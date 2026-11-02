"""Reports hub: mileage (5.6), driving time (5.5), parking (5.2), multimedia (5.3), alarm report (5.8).

Persistence (live schema, Flyway V5):
  mileage    -> dbo.device_mileage_reports   unique (device_id, period_start, period_end)
  driving    -> dbo.device_activity_periods  kind DRIVING, unique (device_id, kind, start_time)
  parking    -> dbo.device_activity_periods  kind PARKING
  multimedia -> dbo.device_media             unique (device_id, file_path)
  alarms     -> dbo.alarms (via AlarmIngestor)
"""
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import (
    day_range,
    parse_duration_seconds,
    parse_vendor_date,
    parse_vendor_time,
    to_float,
    to_int,
    valid_lat_lon,
    validate_range,
)
from app.db.session import transaction
from app.repositories import reports as report_repo
from app.repositories.common import PersistStats, truncate
from app.repositories.devices import DeviceRef, by_terminal
from app.schemas.common import ScopedRangeQuery
from app.schemas.reports import AlarmReportQuery, DailyMileageQuery, MultimediaQuery
from app.services import alarm_service
from app.services.alarm_ingest import AlarmIngestor
from app.services.common import expect_list, fetch_all_devices, resolve_scope
from app.vendor.api import GpsTrackTechApi


# --- row persistence (shared with dashboard / safety / export) ---------------------------------------------
def persist_mileage(db: Session, tenant_id: int, rows: list[dict], devices: dict[str, DeviceRef]) -> PersistStats:
    stats = PersistStats()
    for row in rows:
        device = devices.get(str(row.get("deviceId") or ""))
        row["localDeviceId"] = device.id if device else None
        start, end = parse_vendor_date(row.get("startTime")), parse_vendor_date(row.get("endTime"))
        if device is None or start is None or end is None:
            stats.add("skipped")
            continue
        distance = to_float(row.get("drvingMileage", row.get("drivingMileage")))  # vendor spells "drvingMileage"
        stats.add(report_repo.upsert_mileage(db, tenant_id, device.id, start, end, {
            "distance_km": distance, "start_mileage_km": to_float(row.get("startMileage")),
            "end_mileage_km": to_float(row.get("endMileage")), "plate_color": truncate(row.get("plateColor"), 30)}))
    return stats


def persist_activity(db: Session, tenant_id: int, kind: str, rows: list[dict],
                     devices: dict[str, DeviceRef]) -> PersistStats:
    stats = PersistStats()
    for row in rows:
        device = devices.get(str(row.get("deviceId") or ""))
        row["localDeviceId"] = device.id if device else None
        start = parse_vendor_time(row.get("startTime"))
        # The parking response example uses "drivingTime" while its field table lists "parkingTime".
        duration_text = row.get("parkingTime", row.get("drivingTime")) if kind == "PARKING" else row.get("drivingTime")
        row["durationSeconds"] = parse_duration_seconds(duration_text)
        if device is None or start is None:
            stats.add("skipped")
            continue
        stats.add(report_repo.upsert_activity(db, tenant_id, device.id, kind, start, {
            "end_time": parse_vendor_time(row.get("endTime")), "duration_seconds": row["durationSeconds"],
            "duration_text": truncate(duration_text, 40), "device_type": truncate(row.get("deviceType"), 60)}))
    return stats


def persist_media(db: Session, tenant_id: int, rows: list[dict], devices: dict[str, DeviceRef]) -> PersistStats:
    stats = PersistStats()
    for row in rows:
        device = devices.get(str(row.get("deviceId") or ""))
        row["localDeviceId"] = device.id if device else None
        path = truncate(row.get("filePath"), 500)
        media_type = to_int(row.get("mediaType"))
        if device is None or not path or media_type not in (0, 1):
            stats.add("skipped")
            continue
        lat, lon = valid_lat_lon(row.get("lat"), row.get("lon"))
        stats.add(report_repo.upsert_media(db, tenant_id, device.id, path, {
            "channel": to_int(row.get("channel")), "media_type": media_type,
            "trigger_type": to_int(row.get("multiType")), "operator_user": truncate(row.get("operatorUser"), 100),
            "captured_at": parse_vendor_time(row.get("operatorTime")), "lat": lat, "lon": lon,
            "start_time": parse_vendor_time(row.get("startTime")), "end_time": parse_vendor_time(row.get("endTime")),
            "preview_url": truncate(row.get("previewPath"), 1000)}))
    return stats


# --- paged report endpoints ----------------------------------------------------------------------------------
def _paged(db: Session, user: CurrentUser, settings: Settings, q: ScopedRangeQuery,
           call: Callable[[list[str], datetime, datetime, int, int], object],
           persist: Callable[[list[dict], dict[str, DeviceRef]], PersistStats]) -> dict:
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings)
    response = call([d.terminal_no for d in devices], start, end, q.page, q.page_size)
    rows = expect_list(response)
    if not rows:
        return no_data()
    with transaction(db):
        stats = persist(rows, by_terminal(devices))
    return ok(rows, meta={"total": response.total, "page": q.page, "pageSize": q.page_size, "persisted": stats})


def mileage(db, api: GpsTrackTechApi, user, settings, q: ScopedRangeQuery) -> dict:
    return _paged(db, user, settings, q, api.mileage_report,
                  lambda rows, devs: persist_mileage(db, user.tenant_id, rows, devs))


def driving(db, api: GpsTrackTechApi, user, settings, q: ScopedRangeQuery) -> dict:
    return _paged(db, user, settings, q, api.driving_report,
                  lambda rows, devs: persist_activity(db, user.tenant_id, "DRIVING", rows, devs))


def parking(db, api: GpsTrackTechApi, user, settings, q: ScopedRangeQuery) -> dict:
    return _paged(db, user, settings, q, api.parking_report,
                  lambda rows, devs: persist_activity(db, user.tenant_id, "PARKING", rows, devs))


def multimedia(db, api: GpsTrackTechApi, user, settings, q: MultimediaQuery) -> dict:
    return _paged(db, user, settings, q,
                  lambda terms, s, e, p, size: api.multimedia(terms, s, e, q.media_type, p, size),
                  lambda rows, devs: persist_media(db, user.tenant_id, rows, devs))


def alarm_report(db, api: GpsTrackTechApi, user, settings, q: AlarmReportQuery) -> dict:
    type_ids = q.alarm_type_ids or alarm_service.ensure_type_ids(db, api, alarm_service.ROUTINE_CATEGORIES)
    ingestor = AlarmIngestor(db, user.tenant_id)

    def persist(rows, devs):
        rows[:] = ingestor.ingest_routine(rows, devs, type_ids)
        return ingestor.stats

    return _paged(db, user, settings, q,
                  lambda terms, s, e, p, size: api.routine_alarms(terms, type_ids, s, e, p, size), persist)


def mileage_daily(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings,
                  q: DailyMileageQuery) -> dict:
    """Distance per device per UTC day: one vendor query per day (the vendor aggregates over the whole range)."""
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings, enforce_query_limit=False)
    index = by_terminal(devices)
    result, stats, truncated = [], PersistStats(), False
    for day_start, day_end in day_range(start, end):
        rows, was_truncated = fetch_all_devices(
            lambda terms, page, size, s=day_start, e=day_end: api.mileage_report(terms, s, e, page, size),
            devices, settings)
        truncated = truncated or was_truncated
        if rows:
            with transaction(db):
                for outcome, count in persist_mileage(db, user.tenant_id, rows, index).items():
                    stats.add(outcome, count)
        for row in rows:
            result.append({"date": day_start.date().isoformat(), "deviceId": row.get("localDeviceId"),
                           "terminalNo": row.get("deviceId"), "deviceName": row.get("deviceName"),
                           "distanceKm": to_float(row.get("drvingMileage", row.get("drivingMileage"))),
                           "startMileageKm": to_float(row.get("startMileage")),
                           "endMileageKm": to_float(row.get("endMileage"))})
    if not result:
        return no_data()
    return ok(result, meta={"days": len(day_range(start, end)), "truncated": truncated, "persisted": stats})
