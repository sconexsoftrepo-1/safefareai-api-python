"""Home & AI-event dashboards and the safety rating. All metrics are computed from documented vendor data
(5.1, 5.5, 5.6, 5.8); the vendor itself does not return aggregated statistics."""
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import day_range, parse_vendor_time, to_float, to_int, validate_range
from app.db.session import transaction
from app.repositories import alarms as alarm_repo
from app.repositories import devices as device_repo
from app.repositories.common import PersistStats
from app.repositories.devices import by_terminal
from app.schemas.reports import DashboardQuery, SafetyQuery
from app.services import alarm_service, report_service
from app.services.common import fetch_all_devices, resolve_scope
from app.vendor.api import GpsTrackTechApi


def _merge(*stats: PersistStats) -> PersistStats:
    merged = PersistStats()
    for s in stats:
        for k, v in s.items():
            merged.add(k, v)
    return merged


def alarm_trend(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, q: DashboardQuery) -> dict:
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings, enforce_query_limit=False)
    ai, ai_trunc, ai_stats = alarm_service.collect_ai_events(db, api, user.tenant_id, settings, devices, start, end)
    routine, r_trunc, r_stats = alarm_service.collect_routine_alarms(db, api, user.tenant_id, settings, devices,
                                                                     start, end)
    if not ai and not routine:
        return no_data()
    days = {d.date(): {"aiEvents": 0, "alarms": 0} for d, _ in day_range(start, end)}
    for rows, key, time_field in ((ai, "aiEvents", "alarmTime"), (routine, "alarms", "startTime")):
        for row in rows:
            ts = parse_vendor_time(row.get(time_field))
            if ts is not None and ts.date() in days and not row.get("hidden"):
                days[ts.date()][key] += 1
    series = [{"date": d.isoformat(), **v} for d, v in sorted(days.items())]
    return ok({"days": series, "totals": {"aiEvents": sum(s["aiEvents"] for s in series),
                                          "alarms": sum(s["alarms"] for s in series)}},
              meta={"truncated": ai_trunc or r_trunc, "persisted": _merge(ai_stats, r_stats)})


def _usage(db, api, user, settings, devices, start, end):
    """Mileage + driving time per device for the range (persisted to the report tables)."""
    mileage, m_trunc = fetch_all_devices(lambda t, p, s: api.mileage_report(t, start, end, p, s), devices, settings)
    driving, d_trunc = fetch_all_devices(lambda t, p, s: api.driving_report(t, start, end, p, s), devices, settings)
    index = by_terminal(devices)
    stats = PersistStats()
    with transaction(db):
        if mileage:
            stats = _merge(stats, report_service.persist_mileage(db, user.tenant_id, mileage, index))
        if driving:
            stats = _merge(stats, report_service.persist_activity(db, user.tenant_id, "DRIVING", driving, index))
    usage: dict[str, dict] = defaultdict(lambda: {"distanceKm": 0.0, "drivingSeconds": 0, "deviceName": None})
    for row in mileage:
        entry = usage[str(row.get("deviceId"))]
        entry["distanceKm"] += to_float(row.get("drvingMileage", row.get("drivingMileage"))) or 0.0
        entry["deviceName"] = entry["deviceName"] or row.get("deviceName")
    for row in driving:
        entry = usage[str(row.get("deviceId"))]
        entry["drivingSeconds"] += row.get("durationSeconds") or 0
        entry["deviceName"] = entry["deviceName"] or row.get("deviceName")
    return usage, bool(mileage or driving), m_trunc or d_trunc, stats


def top_rankings(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, q: DashboardQuery) -> dict:
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings, enforce_query_limit=False)
    usage, has_data, truncated, stats = _usage(db, api, user, settings, devices, start, end)
    if not has_data:
        return no_data()
    index = by_terminal(devices)
    items = [{"deviceId": index[t].id if t in index else None, "terminalNo": t,
              "deviceName": (index[t].name if t in index else None) or u["deviceName"],
              "distanceKm": round(u["distanceKm"], 3), "drivingSeconds": u["drivingSeconds"]}
             for t, u in usage.items()]
    return ok({"byMileage": sorted(items, key=lambda i: i["distanceKm"], reverse=True)[:q.top_n],
               "byDrivingTime": sorted(items, key=lambda i: i["drivingSeconds"], reverse=True)[:q.top_n]},
              meta={"truncated": truncated, "persisted": stats})


def ai_dashboard(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, q: DashboardQuery) -> dict:
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings, enforce_query_limit=False)
    rows, truncated, stats = alarm_service.collect_ai_events(db, api, user.tenant_id, settings, devices, start, end)
    rows = [r for r in rows if not r.get("hidden")]
    if not rows:
        return no_data()
    names = {d.id: d.name for d in devices}
    by_type = Counter((to_int(r.get("alarmType")), r.get("alarmName")) for r in rows)
    hourly = [0] * 24
    by_device: Counter = Counter()
    cells: Counter = Counter()
    for r in rows:
        ts = parse_vendor_time(r.get("alarmTime"))
        if ts is not None:
            hourly[ts.hour] += 1
        by_device[r.get("localDeviceId") or r.get("deviceId")] += 1
        lat, lon = to_float(r.get("lat")), to_float(r.get("lon"))
        if lat and lon:
            cells[(round(lat, 2), round(lon, 2))] += 1
    return ok({
        "total": len(rows),
        "byType": [{"alarmType": k[0], "alarmName": k[1], "count": c} for k, c in by_type.most_common()],
        "hourly": [{"hour": h, "count": c} for h, c in enumerate(hourly)],
        "topVehicles": [{"deviceId": k if isinstance(k, int) else None, "deviceName": names.get(k, k), "count": c}
                        for k, c in by_device.most_common(q.top_n)],
        "mapCells": [{"lat": k[0], "lon": k[1], "count": c} for k, c in cells.most_common(500)],
    }, meta={"timezone": "UTC", "truncated": truncated, "persisted": stats})


def _grade(score: float | None) -> str | None:
    if score is None:
        return None
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "E"


def _score(penalty: float, distance_km: float, settings: Settings) -> float | None:
    if distance_km < settings.safety_min_distance_km:
        return None
    return round(max(0.0, 100.0 - penalty / (distance_km / 100.0)), 2)


def safety_rating(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, q: SafetyQuery) -> dict:
    """ASSUMPTION (needs product sign-off): score = 100 - severity-weighted AI events per 100 km, floored at 0.
    Weights come from settings (SAFETY_WEIGHT_*); devices under SAFETY_MIN_DISTANCE_KM get no score."""
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings, enforce_query_limit=False)
    events, a_trunc, a_stats = alarm_service.collect_ai_events(db, api, user.tenant_id, settings, devices, start, end)
    usage, has_usage, u_trunc, u_stats = _usage(db, api, user, settings, devices, start, end)
    if not events and not has_usage:
        return no_data()
    types = alarm_repo.alarm_type_map(db)
    per_device = {d.id: {"deviceId": d.id, "deviceName": d.name, "groupId": d.group_id,
                         "distanceKm": round(usage.get(d.terminal_no, {}).get("distanceKm", 0.0), 3),
                         "drivingSeconds": usage.get(d.terminal_no, {}).get("drivingSeconds", 0),
                         "events": 0, "severeEvents": 0, "penalty": 0.0} for d in devices}
    for e in events:
        entry = per_device.get(e.get("localDeviceId"))
        if entry is None or e.get("hidden"):
            continue
        type_row = types.get(to_int(e.get("alarmType")))
        severity = type_row.default_severity if type_row else 3
        entry["events"] += 1
        entry["severeEvents"] += 1 if severity == 1 else 0
        entry["penalty"] += settings.severity_weight(severity)
    for entry in per_device.values():
        entry["score"] = _score(entry["penalty"], entry["distanceKm"], settings)
        entry["grade"] = _grade(entry["score"])
    items = sorted(per_device.values(), key=lambda e: (e["score"] is None, e["score"] if e["score"] is not None
                                                       else 0))
    if q.level == "fleet":
        groups = device_repo.group_names(db, user.tenant_id)
        fleets: dict[int, dict] = {}
        for entry in per_device.values():
            fleet = fleets.setdefault(entry["groupId"], {"groupId": entry["groupId"],
                                                         "groupName": groups.get(entry["groupId"]), "vehicles": 0,
                                                         "distanceKm": 0.0, "drivingSeconds": 0, "events": 0,
                                                         "severeEvents": 0, "penalty": 0.0})
            fleet["vehicles"] += 1
            for key in ("distanceKm", "drivingSeconds", "events", "severeEvents", "penalty"):
                fleet[key] += entry[key]
        for fleet in fleets.values():
            fleet["distanceKm"] = round(fleet["distanceKm"], 3)
            fleet["score"] = _score(fleet["penalty"], fleet["distanceKm"], settings)
            fleet["grade"] = _grade(fleet["score"])
        items = sorted(fleets.values(), key=lambda f: (f["score"] is None, f["score"] or 0))
    return ok({"level": q.level, "items": items,
               "method": {"formula": "100 - weightedEvents / (distanceKm / 100), floor 0",
                          "weights": {str(s): settings.severity_weight(s) for s in (1, 2, 3, 4)},
                          "minDistanceKm": settings.safety_min_distance_km}},
              meta={"truncated": a_trunc or u_trunc, "persisted": _merge(a_stats, u_stats)})
