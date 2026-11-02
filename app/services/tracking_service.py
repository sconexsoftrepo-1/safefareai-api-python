"""Vehicle detail & track playback: sensor readings (3.1), track (3.2), alarm points (3.2 + 5.1), route fence (10.3)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (BadRequestError, ConfigurationError, ConflictError, DatabaseError,
                                 VendorBadRequestError, VendorInvalidResponseError)
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import parse_vendor_time, to_float, to_int, utcnow, valid_lat_lon, validate_range
from app.db.session import transaction
from app.repositories import devices as device_repo
from app.repositories import geofences as fence_repo
from app.repositories import telemetry as telemetry_repo
from app.repositories import voices as voice_repo
from app.repositories.common import to_json, truncate
from app.repositories.devices import DeviceRef
from app.schemas.tracking import FenceFromTrackIn, TrackOptions
from app.services import alarm_service
from app.services.common import device_view, expect_object
from app.vendor.api import GpsTrackTechApi

FENCE_COLORS = {0: "#1e90ff", 1: "#00BCD4", 2: "#43CF7C", 3: "#F44336", 4: "#FF9800", 5: "#FFEB3B"}
LOAD_STATUS = {0: "EMPTY", 1: "HALF", 2: "FULL"}
POINT_TYPES = {1: "IDLING", 2: "PARKING"}


def acc_on(value) -> bool | None:
    state = to_int(value)
    return {0: True, 1: False}.get(state)  # vendor: 0 on, 1 off


def _battery(value) -> int | None:
    pct = to_int(value)
    return pct if pct is not None and 0 <= pct <= 100 else None


def _channels(value) -> list[float | None]:
    if value is None or str(value).strip() == "":
        return []
    return [to_float(part) for part in str(value).split(",")]


# --- 3.1 sensor readings -----------------------------------------------------------------------------------
def build_sensors(row: dict) -> dict:
    load_status = to_int(row.get("loadStatus"))
    return {
        "temperature": {"raw": row.get("temperature"), "channels": _channels(row.get("temperature"))},
        "humidity": {"raw": row.get("humidity"), "channels": _channels(row.get("humidity"))},
        "fuel": {k: to_float(row.get(k)) for k in ("firstOilScale", "firstOilMete", "secondOilScale",
                                                   "secondOilMete")},
        "load": {"loadStatus": load_status, "loadStatusText": LOAD_STATUS.get(load_status),
                 "loadValue": to_float(row.get("loadValue")), "wholeWeigh": to_float(row.get("wholeWeigh")),
                 "loadWeigh": to_float(row.get("loadWeigh"))},
    }


def latest_state_values(row: dict, sensors: dict) -> dict:
    located = to_int(row.get("posState")) not in (None, 0)
    lat, lon = valid_lat_lon(row.get("lat"), row.get("lon")) if located else (None, None)
    status = to_int(row.get("vehicleState"))
    network = to_int(row.get("netModel"))
    direction = to_int(row.get("direct"))
    now = utcnow()
    return {
        "device_time": parse_vendor_time(row.get("devTime")), "received_at": now, "lat": lat, "lon": lon,
        "speed_kmh": to_float(row.get("speed")),
        "direction_deg": direction if direction is not None and 0 <= direction <= 360 else None,
        "altitude_m": to_float(row.get("high")), "mileage_km": to_float(row.get("mileage")),
        "status_code": status if status is not None and 0 <= status <= 5 else 3,
        "acc_on": acc_on(row.get("accState")), "position_mode": to_int(row.get("posState")),
        "battery_pct": _battery(row.get("power")), "gsm_signal": to_int(row.get("gsmSin")),
        "network_type": network if network in (1, 2, 3) else None, "sensors": to_json(sensors),
        "active_alarm": truncate(row.get("alarm"), 200), "video_capable": to_int(row.get("videoType")) == 1,
        "updated_at": now,
    }


def fetch_realtime_row(api: GpsTrackTechApi, device: DeviceRef) -> dict | None:
    data = expect_object(api.real_time_info([device.terminal_no]))
    items = (data or {}).get("list")
    if items is None:
        return None
    if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
        raise VendorInvalidResponseError("The vendor returned vehicle data in an unexpected format")
    return next((i for i in items if str(i.get("terminalNo")) == device.terminal_no), None)


def sensor_readings(db: Session, api: GpsTrackTechApi, user: CurrentUser, device_id: int) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    row = fetch_realtime_row(api, device)
    if row is None:
        return no_data()
    sensors = build_sensors(row)
    with transaction(db):
        outcome = telemetry_repo.upsert_latest_state(db, user.tenant_id, device.id, latest_state_values(row, sensors))
    return ok({"device": device_view(device), "deviceTime": row.get("devTime"),
               "vehicleState": to_int(row.get("vehicleState")), "accOn": acc_on(row.get("accState")),
               "sensors": sensors}, meta={"persisted": {outcome: 1}})


def realtime_states(db: Session, api: GpsTrackTechApi, user: CurrentUser,
                    settings: Settings, device_ids: list[int] | None = None) -> dict:
    """Fetch the tenant's live device states in vendor-sized batches for Live Monitoring."""
    devices = (device_repo.get_devices(db, user.tenant_id, device_ids) if device_ids
               else device_repo.tenant_devices(db, user.tenant_id))
    states = []
    received_devices = set()
    with transaction(db):
        for offset in range(0, len(devices), settings.gpstracktech_max_devices_per_query):
            batch = devices[offset:offset + settings.gpstracktech_max_devices_per_query]
            response = expect_object(api.real_time_info([d.terminal_no for d in batch]))
            rows = (response or {}).get("list", [])
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise VendorInvalidResponseError("The vendor returned vehicle data in an unexpected format")
            by_terminal = {str(row.get("terminalNo")): row for row in rows if row.get("terminalNo") is not None}
            for device in batch:
                row = by_terminal.get(device.terminal_no)
                if row is None:
                    continue
                sensors = build_sensors(row)
                values = latest_state_values(row, sensors)
                telemetry_repo.upsert_latest_state(db, user.tenant_id, device.id, values)
                received_devices.add(device.id)
                states.append({
                    "deviceId": device.id,
                    "vendorVehicleId": device.vendor_vehicle_id,
                    "name": device.name,
                    "terminalNo": device.terminal_no,
                    "statusCode": values["status_code"],
                    "deviceTime": values["device_time"].isoformat() if values["device_time"] else None,
                    "lat": values["lat"], "lon": values["lon"],
                    "speedKmh": values["speed_kmh"], "directionDeg": values["direction_deg"],
                    "altitudeM": values["altitude_m"], "mileageKm": values["mileage_km"],
                    "positionMode": values["position_mode"], "batteryPct": values["battery_pct"],
                    "gsmSignal": values["gsm_signal"], "networkType": values["network_type"],
                    "activeAlarm": values["active_alarm"], "videoCapable": values["video_capable"],
                    "sensors": sensors, "receivedAt": values["received_at"].isoformat(),
                })
    return ok({"onlineCount": len(received_devices), "offlineCount": max(0, len(devices) - len(received_devices)),
               "devices": states}, meta={"source": "VENDOR", "stale": False})


# --- 3.2 track -------------------------------------------------------------------------------------------
def fetch_track(api: GpsTrackTechApi, device: DeviceRef, start: datetime, end: datetime,
                opts: TrackOptions) -> tuple[dict, list[dict]]:
    terminal = (device.terminal_no or "").strip()

    def mapping_error():
        return ConfigurationError(
            f"GPS vendor could not resolve device {device.id} (terminal '{terminal or 'missing'}'). "
            "Check its vendor vehicle ID, terminal number and access under the configured vendor account.",
            code="VENDOR_DEVICE_MAPPING_INVALID",
            details={"deviceId": device.id, "terminalNo": terminal,
                     "vendorVehicleId": device.vendor_vehicle_id},
        )

    def request_track(value):
        return expect_object(api.track_list(value, start, end, filter_time=opts.filter_parking_minutes,
                                           stop_status=0 if opts.filter_stops else 1,
                                           pos_status=opts.position_filter))

    if not terminal:
        raise mapping_error()
    try:
        data = request_track(terminal)
    except VendorBadRequestError as exc:
        message = str((exc.details or {}).get("vendorMessage") or exc.message).strip().casefold()
        if message != "device cannot be empty":
            raise
        if not device.vendor_vehicle_id:
            raise mapping_error() from exc
        # Use only the explicitly mapped vendor vehicle ID. Guessing by name or
        # choosing another device could return a different vehicle's route.
        try:
            vehicle = expect_object(api.vehicle_info(device.vendor_vehicle_id))
        except VendorBadRequestError as lookup_exc:
            raise mapping_error() from lookup_exc
        if not vehicle:
            raise mapping_error() from exc
        if to_int(vehicle.get("vehicleId")) != device.vendor_vehicle_id:
            raise VendorInvalidResponseError("Vendor vehicle lookup returned a different or missing vehicle ID")
        verified_terminal = str(vehicle.get("terminalNo") or "").strip()
        if not verified_terminal or verified_terminal == terminal:
            raise mapping_error() from exc
        try:
            data = request_track(verified_terminal)
        except VendorBadRequestError as retry_exc:
            message = str((retry_exc.details or {}).get("vendorMessage") or retry_exc.message).strip().casefold()
            if message == "device cannot be empty":
                raise mapping_error() from retry_exc
            raise
    if data is None:
        return {}, []
    points = data.get("trackList")
    if points is None:
        return data, []
    if not isinstance(points, list) or any(not isinstance(p, dict) for p in points):
        raise VendorInvalidResponseError("The vendor returned track data in an unexpected format")
    return data, points


def normalize_points(points: list[dict]) -> list[dict]:
    result, first = [], None
    for p in points:
        time = parse_vendor_time(p.get("devTime"))
        if time is not None and first is None:
            first = time
        lat, lon = valid_lat_lon(p.get("lat"), p.get("lon"))
        point_type = to_int(p.get("pointType"))
        result.append({
            "time": time.isoformat() if time else p.get("devTime"),
            "elapsedSec": int((time - first).total_seconds()) if time and first else None,
            "lat": lat, "lon": lon, "speedKmh": to_float(p.get("speed")), "direction": to_int(p.get("direct")),
            "mileageKm": to_float(p.get("mileage")), "accOn": acc_on(p.get("accState")),
            "located": to_int(p.get("positionState")) == 1, "runState": to_int(p.get("runState")),
            "stopType": POINT_TYPES.get(point_type), "stopSeconds": to_int(p.get("timeSecond")) if point_type else None,
            "alarm": p.get("typeAlarm") or None, "alarmLevel": to_int(p.get("alarmLevelInt")) or None,
            "sensorState": p.get("sensorState"), "temperature": p.get("temperature"),
            "power": _battery(p.get("power")), "backfill": to_int(p.get("returnPass")) == 1,
        })
    return result


def summarize(data: dict, points: list[dict]) -> dict:
    stops = [{"type": p["stopType"], "time": p["time"], "durationSec": p["stopSeconds"], "lat": p["lat"],
              "lon": p["lon"]} for p in points if p["stopType"]]
    moving = [p["speedKmh"] for p in points if p["speedKmh"] and p["runState"] == 1]
    return {
        "distanceKm": to_float(data.get("relativeMileage")),
        "drivingSeconds": to_int(data.get("runTime")),
        "firstTime": data.get("firstTime"), "lastTime": data.get("lastTime"),
        "pointCount": to_int(data.get("trackTotal")) or len(points),
        "stopCount": sum(1 for s in stops if s["type"] == "PARKING"),
        "idleCount": sum(1 for s in stops if s["type"] == "IDLING"),
        "parkingSeconds": sum(s["durationSec"] or 0 for s in stops if s["type"] == "PARKING"),
        "idlingSeconds": sum(s["durationSec"] or 0 for s in stops if s["type"] == "IDLING"),
        "maxSpeedKmh": max((p["speedKmh"] or 0 for p in points), default=None),
        "avgMovingSpeedKmh": round(sum(moving) / len(moving), 1) if moving else None,
        "stops": stops,
    }


def position_rows(raw_points: list[dict]) -> list[dict]:
    rows = []
    for p in raw_points:
        time = parse_vendor_time(p.get("devTime"))
        lat, lon = valid_lat_lon(p.get("lat"), p.get("lon"))
        if time is None or lat is None or to_int(p.get("positionState")) != 1:
            continue
        direction = to_int(p.get("direct"))
        rows.append({
            "device_time": time, "lat": lat, "lon": lon, "speed_kmh": to_float(p.get("speed")),
            "direction_deg": direction if direction is not None and 0 <= direction <= 360 else None,
            "mileage_km": to_float(p.get("mileage")), "acc_on": acc_on(p.get("accState")),
            "run_state": to_int(p.get("runState")), "position_state": 1, "battery_pct": _battery(p.get("power")),
            "is_backfill": to_int(p.get("returnPass")) == 1,
            "extra": to_json({k: p.get(k) for k in ("oil", "oilScale", "swOilMete", "swOilScale", "sensorState",
                                                    "loadStatus", "sensorSpeed", "temperature", "typeAlarm",
                                                    "alarmLevelInt", "pointType", "timeSecond")}),
        })
    return rows


def query_track(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, device_id: int,
                start: datetime, end: datetime, opts: TrackOptions) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    start, end = validate_range(start, end, settings.track_max_range_days)
    data, raw_points = fetch_track(api, device, start, end, opts)
    if not raw_points:
        return no_data()
    points = normalize_points(raw_points)
    with transaction(db):
        inserted = telemetry_repo.insert_positions(db, user.tenant_id, device.id, position_rows(raw_points))
    return ok({"device": device_view(device), "baseInfo": data.get("baseInfo"), "summary": summarize(data, points),
               "points": points},
              meta={"persisted": {"inserted": inserted, "unchanged": len(raw_points) - inserted}})


def track_alarm_points(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, device_id: int,
                       start: datetime, end: datetime, opts: TrackOptions) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    start, end = validate_range(start, end, settings.track_max_range_days)
    _, raw_points = fetch_track(api, device, start, end, opts)
    track_alarms = [p for p in normalize_points(raw_points) if p["alarm"]]
    events, truncated, stats = alarm_service.collect_ai_events(db, api, user.tenant_id, settings, [device], start,
                                                               end)
    if not track_alarms and not events:
        return no_data()
    ai_points = [{"localAlarmId": e.get("localAlarmId"), "alarmId": e.get("alarmId"),
                  "alarmType": e.get("alarmType"), "alarmName": e.get("alarmName"), "alarmTime": e.get("alarmTime"),
                  "lat": to_float(e.get("lat")), "lon": to_float(e.get("lon")), "speed": to_float(e.get("speed")),
                  "videoUrl": e.get("aviPath") or None, "imageUrl": e.get("imagePath") or None,
                  "handlingStatus": e.get("handlingStatus")} for e in events if not e.get("hidden")]
    return ok({"device": device_view(device), "aiEvents": ai_points, "trackAlarms": track_alarms},
              meta={"aiEventsTruncated": truncated, "persisted": stats})


# --- 10.3 track to route fence -----------------------------------------------------------------------------
def _downsample(coords: list[tuple[float, float]], max_points: int) -> list[tuple[float, float]]:
    deduped = [c for i, c in enumerate(coords) if i == 0 or c != coords[i - 1]]
    if len(deduped) <= max_points:
        return deduped
    step = (len(deduped) - 1) / (max_points - 1)
    return [deduped[round(i * step)] for i in range(max_points)]


def fence_from_track(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings,
                     req: FenceFromTrackIn) -> dict:
    device = device_repo.get_device(db, user.tenant_id, req.device_id)
    start, end = validate_range(req.start_time, req.end_time, settings.track_max_range_days)
    name = req.name.strip()
    if fence_repo.name_exists(db, user.tenant_id, name):
        raise ConflictError("A geofence with this name already exists", code="GEOFENCE_NAME_EXISTS")

    # Validate bindings and voices before touching the vendor.
    vendor_select_ids: list[int] = []
    if req.bind_type == "DEVICE":
        targets = device_repo.get_devices(db, user.tenant_id, req.bind_ids)
        unsynced = [d.id for d in targets if d.vendor_vehicle_id is None]
        if unsynced:
            raise ConflictError("Devices have no vendor vehicle id yet; sync devices first",
                                code="DEVICE_NOT_SYNCED", details={"deviceIds": unsynced})
        vendor_select_ids = [d.vendor_vehicle_id for d in targets]
    elif req.bind_type == "GROUP":
        groups = [device_repo.get_group(db, user.tenant_id, gid) for gid in req.bind_ids]
        unsynced = [g.id for g in groups if g.vendor_group_id is None]
        if unsynced:
            raise ConflictError("Groups have no vendor group id yet; sync groups first",
                                code="GROUP_NOT_SYNCED", details={"groupIds": unsynced})
        vendor_select_ids = [g.vendor_group_id for g in groups]
    issued = []
    for r in req.reminders:
        entry = {"ruleType": r.rule_type, "displayUsage": r.display_usage, "playCount": r.play_count}
        if r.display_usage == 8:
            entry["text"] = r.text.strip()
        else:
            entry["voiceId"] = voice_repo.get_voice_vendor_id(db, user.tenant_id, r.voice_id)
        issued.append(entry)

    _, raw_points = fetch_track(api, device, start, end, req)
    if not raw_points:
        return no_data()
    coords = []
    for p in raw_points:
        lat, lon = valid_lat_lon(p.get("lat"), p.get("lon"))
        if lat is not None and to_int(p.get("positionState")) == 1:
            coords.append((lon, lat))
    coords = _downsample(coords, min(req.max_points, settings.fence_max_points))
    if len(coords) < 2:
        raise BadRequestError("The track has fewer than 2 located points; a line fence needs at least 2",
                              code="TRACK_TOO_SHORT")

    rule_csv = ",".join(str(r) for r in sorted(req.rule_types))
    body = {"pathName": name, "pathType": 1, "ruleType": rule_csv, "color": str(req.color),
            "areaType": req.area_type, "pointList": [{"oriLat": lat, "oriLon": lon} for lon, lat in coords]}
    if 1 in req.rule_types:
        body["maxSpeed"] = req.max_speed_kmh
    if 2 in req.rule_types:
        body["param"] = req.offset_meters
    if 5 in req.rule_types:
        body["threshold"] = req.completion_pct
    if req.bind_type:
        body["selectType"] = 1 if req.bind_type == "DEVICE" else 0
        body["selectIds"] = ",".join(str(i) for i in vendor_select_ids)
    if issued:
        body["issued"] = issued
    api.add_path(body)  # vendor returns data=null on success; a non-200 code raises

    now = utcnow()
    rules = [{"rule_type": rt, "max_speed_kmh": req.max_speed_kmh if rt == 1 else None,
              "offset_meters": req.offset_meters if rt == 2 else None,
              "completion_pct": req.completion_pct if rt == 5 else None} for rt in sorted(req.rule_types)]
    bindings = [{"target_type": req.bind_type, "target_id": i} for i in req.bind_ids] if req.bind_type else []
    reminders = [{"rule_type": r.rule_type, "display_usage": r.display_usage,
                  "tts_text": r.text.strip() if r.display_usage == 8 else None, "play_count": r.play_count,
                  "voice_id": r.voice_id if r.display_usage == 32 else None} for r in req.reminders]
    try:
        with transaction(db):
            geofence_id = fence_repo.create_geofence(db, {
                "tenant_id": user.tenant_id, "name": name, "shape_type": "LINE", "color": FENCE_COLORS[req.color],
                "area_type": req.area_type, "enabled": True, "created_by": user.user_id, "created_at": now,
                "updated_at": now, "rule_types": rule_csv,
                "rule_param": req.offset_meters if 2 in req.rule_types else None,
                "max_speed": req.max_speed_kmh if 1 in req.rule_types else None,
                "threshold": req.completion_pct if 5 in req.rule_types else None,
                "select_type": body.get("selectType"), "select_ids": body.get("selectIds"),
                "issued": to_json(issued) if issued else None, "vendor_user_id": api.account.vendor_user_id,
            }, coords, rules, bindings, reminders)
    except DatabaseError as exc:
        raise DatabaseError("The route fence was created at the vendor but could not be saved locally; "
                            "it will appear after the next geofence sync", code="FENCE_NOT_SAVED_LOCALLY") from exc
    return ok({"geofenceId": geofence_id, "vendorPathId": None, "name": name, "shapeType": "LINE",
               "ruleTypes": sorted(req.rule_types), "pointCount": len(coords), "sourcePointCount": len(raw_points)},
              message="Route fence created",
              meta={"note": "The vendor's /path/add response does not include the new path id; "
                            "vendor_path_id is filled by the geofence sync (/path/list)."})
