from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.responses import ENVELOPE, ERROR_RESPONSES, NO_DATA_MESSAGE
from app.core.security import require_permissions
from app.db import tables as t
from app.repositories import devices as device_repo
from app.schemas.tracking import FenceFromTrackIn, TrackOptions
from app.services import tracking_service

router = APIRouter(tags=["Vehicle detail & Track playback"], responses=ERROR_RESPONSES)


@router.get("/monitor/realtime", **ENVELOPE, summary="Live device states for fleet monitoring")
def realtime(device_ids: list[int] | None = Query(None, alias="deviceIds"),
             user=Depends(require_permissions("device.read")), db: Session = Depends(get_db),
             api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return tracking_service.realtime_states(db, api, user, settings, device_ids)


@router.get("/groups", **ENVELOPE, summary="List the caller's device groups")
def groups(user=Depends(require_permissions("device.read")), db: Session = Depends(get_db)):
    rows = db.execute(select(t.device_groups.c.id, t.device_groups.c.vendor_group_id, t.device_groups.c.name)
                      .where(t.device_groups.c.tenant_id == user.tenant_id,
                             t.device_groups.c.deleted_at.is_(None))
                      .order_by(t.device_groups.c.id)).all()
    items = [{"id": row.id, "vendorGroupId": row.vendor_group_id, "name": row.name} for row in rows]
    return {"success": True, "message": "Success", "data": items, "meta": {"total": len(items)}}


@router.get("/devices", **ENVELOPE, summary="List the caller's devices")
def devices(group_id: int | None = Query(None, alias="groupId"), keyword: str | None = None,
            page: int = Query(1, ge=1), page_size: int = Query(100, alias="pageSize", ge=1, le=100),
            user=Depends(require_permissions("device.read")), db: Session = Depends(get_db)):
    rows = device_repo.tenant_devices(db, user.tenant_id, group_id)
    if keyword and keyword.strip():
        needle = keyword.strip().casefold()
        rows = [d for d in rows if needle in (d.name or "").casefold() or needle in d.terminal_no.casefold()]
    total = len(rows)
    start = (page - 1) * page_size
    items = [{"id": d.id, "vendorVehicleId": d.vendor_vehicle_id, "groupId": d.group_id,
              "name": d.name, "terminalNo": d.terminal_no, "cameraLines": list(d.camera_lines),
              "cameraCount": len(d.camera_lines)} for d in rows[start:start + page_size]]
    return {"success": True, "message": "Success", "data": items, "meta": {"total": total}}


def track_options(filter_parking_minutes: int = Query(0, alias="filterParkingMinutes", ge=0, le=1440),
                  filter_stops: bool = Query(False, alias="filterStops"),
                  position_filter: int = Query(0, alias="positionFilter", ge=0, le=2,
                                                description="0 drop non-located, 1 keep all, 2 drop located"),
                  ) -> TrackOptions:
    return TrackOptions(filter_parking_minutes=filter_parking_minutes, filter_stops=filter_stops,
                        position_filter=position_filter)


@router.get("/devices/{device_id}/sensors", **ENVELOPE,
            summary="Sensor readings (temperature, humidity, fuel, load)",
            description="Vendor 3.1 getRealTimeInfo. Persists dbo.device_latest_state.")
def sensors(device_id: int = Path(gt=0), user=Depends(require_permissions("device.read")),
            db: Session = Depends(get_db), api=Depends(get_vendor_api)):
    return tracking_service.sensor_readings(db, api, user, device_id)


@router.get("/devices/{device_id}/track", **ENVELOPE,
            summary="Historical track, playback points and stops/idling/mileage summary",
            description="Vendor 3.2 getTrackList. `points[].elapsedSec` drives client-side playback at any speed. "
                        "Located points are persisted to dbo.device_positions.")
def track(device_id: int = Path(gt=0), start_time: datetime = Query(alias="startTime"),
          end_time: datetime = Query(alias="endTime"), opts: TrackOptions = Depends(track_options),
          user=Depends(require_permissions("track.read")), db: Session = Depends(get_db),
          api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return tracking_service.query_track(db, api, user, settings, device_id, start_time, end_time, opts)


@router.get("/devices/{device_id}/track/alarm-points", **ENVELOPE,
            summary="Alarm points on the track (AI events with attachments + track alarms)",
            description="Vendor 3.2 getTrackList + 5.1 recentlyAdasList. AI events are persisted to dbo.alarms.")
def track_alarm_points(device_id: int = Path(gt=0), start_time: datetime = Query(alias="startTime"),
                       end_time: datetime = Query(alias="endTime"), opts: TrackOptions = Depends(track_options),
                       user=Depends(require_permissions("track.read", "alarm.read")), db: Session = Depends(get_db),
                       api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return tracking_service.track_alarm_points(db, api, user, settings, device_id, start_time, end_time, opts)


@router.post("/geofences/from-track", **ENVELOPE, status_code=201,
             summary="Turn a queried track into a line (route) fence",
             description="Vendor 3.2 getTrackList then 10.3 /path/add (pathType 1). Persists dbo.geofences, "
                         "geofence_points, geofence_rules, geofence_bindings and geofence_reminders.")
def fence_from_track(body: FenceFromTrackIn, user=Depends(require_permissions("geofence.manage", "track.read")),
                     db: Session = Depends(get_db), api=Depends(get_vendor_api),
                     settings: Settings = Depends(get_settings)):
    result = tracking_service.fence_from_track(db, api, user, settings, body)
    # 201 only when a fence was created; "No Data from Vendor" (empty track) is a plain 200.
    return JSONResponse(jsonable_encoder(result), status_code=201 if result.get("message") != NO_DATA_MESSAGE else 200)
