"""Live video & playback: SDK temp token (4.7), wake (8.3), calendar (4.6), recordings (4.1),
FTP clip export (4.4) + polling (4.5), and the browser-only iframe demo pages (4.2 / 4.3)."""
import re

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BadRequestError, DatabaseError, VendorInvalidResponseError
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import parse_vendor_time, to_float, to_int, utcnow, validate_range
from app.db.session import transaction
from app.repositories import devices as device_repo
from app.repositories import telemetry as telemetry_repo
from app.repositories import video as video_repo
from app.repositories.common import PersistStats, truncate
from app.schemas.video import RecordQueryIn, RecordUploadIn
from app.services import command_service, tracking_service
from app.services.common import device_view, expect_object
from app.vendor.api import GpsTrackTechApi

TEMP_TOKEN_TTL_SECONDS = 300  # documented: "expired for five minutes"
_YEAR_MONTH = re.compile(r"^(\d{2}|\d{4})-(0[1-9]|1[0-2])$")
UPLOAD_STATUS = {0: "READY", 1: "FAILED", 2: "UPLOADING", 3: "FAILED"}
UPLOAD_ERRORS = {1: "Vendor reported that the upload failed",
                 3: "Vendor found no distribution record for this upload"}


def temp_token(api: GpsTrackTechApi) -> dict:
    data = expect_object(api.av_sdk_temp_token())
    token = (data or {}).get("tempTk")
    if not token:
        raise VendorInvalidResponseError("The vendor did not return a temporary video token")
    # Not persisted: the token is a short-lived credential.
    return ok({"tempToken": token, "createTime": data.get("createTime"), "expiresInSeconds": TEMP_TOKEN_TTL_SECONDS})


def embed_config(api: GpsTrackTechApi, settings: Settings) -> dict:
    token = temp_token(api)["data"]
    base = settings.gpstracktech_video_demo_base_url.rstrip("/")
    return ok({"demoUrl": f"{base}/#/videoapi/demo", "docUrl": f"{base}/#/videoapi/demo/doc",
               "usageGuideUrl": f"{base}/#/videoapi/demo/doc?type=0", **token},
              meta={"note": "Vendor 4.2/4.3 are browser-side iframe pages, not JSON APIs. Use tempToken as the "
                            "SDK user token; the PDF does not document URL parameters for passing it to the iframe."})


def live_session(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, device_id: int,
                 auto_wake: bool) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    row = tracking_service.fetch_realtime_row(api, device)
    acc_on = tracking_service.acc_on(row.get("accState")) if row else None
    wake_result = None
    if row is not None:
        with transaction(db):
            sensors = tracking_service.build_sensors(row)
            telemetry_repo.upsert_latest_state(db, user.tenant_id, device.id,
                                               tracking_service.latest_state_values(row, sensors))
    if auto_wake and acc_on is False:
        wake_result = command_service.wake(db, api, user, settings, [device.id])["data"]
    token = temp_token(api)["data"]
    channels = list(device.camera_lines) or (list(range(1, to_int(row.get("cameraNum")) + 1))
                                             if row and to_int(row.get("cameraNum")) else [])
    return ok({"device": device_view(device), "channels": channels, "accOn": acc_on,
               "videoCapable": to_int(row.get("videoType")) == 1 if row else None,
               "vehicleState": to_int(row.get("vehicleState")) if row else None,
               "wakeCommand": wake_result, **token})


def calendar(db: Session, api: GpsTrackTechApi, user: CurrentUser, device_id: int, year_month: str) -> dict:
    if not _YEAR_MONTH.match(year_month):
        raise BadRequestError("yearMonth must be yyyy-MM or yy-MM", code="INVALID_YEAR_MONTH")
    device = device_repo.get_device(db, user.tenant_id, device_id)
    data = api.monthly_calendar(device.terminal_no, year_month).data
    if data is None or (isinstance(data, str) and not data.strip()):
        return no_data()
    if not isinstance(data, str):
        raise VendorInvalidResponseError("The vendor returned the recording calendar in an unexpected format")
    days = sorted({d for d in (to_int(p) for p in data.split(",")) if d is not None and 1 <= d <= 31})
    if not days:
        raise VendorInvalidResponseError("The vendor returned the recording calendar in an unexpected format")
    # Not persisted: no table stores per-month recording calendars.
    return ok({"device": device_view(device), "yearMonth": year_month, "daysWithRecordings": days})


def recordings(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, device_id: int,
               q: RecordQueryIn) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    data = expect_object(api.record_query(device.terminal_no, start, end, q.channel))
    files = (data or {}).get("listFile")
    if not files:
        return no_data()
    if not isinstance(files, list) or any(not isinstance(f, dict) for f in files):
        raise VendorInvalidResponseError("The vendor returned recordings in an unexpected format")
    stats = PersistStats()
    segments = []
    with transaction(db):
        for f in files:
            # The PDF spells the size field 'fileSzie' (table) and 'fireSize' (example); accept both and 'fileSize'.
            size = to_float(f.get("fileSzie", f.get("fireSize", f.get("fileSize"))))
            channel, data_type, stream = to_int(f.get("channel")), to_int(f.get("datatype")), to_int(f.get("codetype"))
            begin, finish = parse_vendor_time(f.get("begintime")), parse_vendor_time(f.get("endtime"))
            segment = {"channel": channel, "beginTime": begin.isoformat() if begin else f.get("begintime"),
                       "endTime": finish.isoformat() if finish else f.get("endtime"), "dataType": data_type,
                       "streamType": stream, "fileSizeMb": size}
            segments.append(segment)
            if None in (channel, begin, finish, data_type, stream):
                stats.add("skippedInvalid")
                continue
            stats.add(video_repo.upsert_video_file(db, user.tenant_id, device.id, {
                "channel": channel, "begin_time": begin, "end_time": finish, "data_type": data_type,
                "stream_type": stream}, size))
    return ok({"device": device_view(device), "segments": segments}, meta={"persisted": stats})


def _job_view(job) -> dict:
    return {"jobId": job.id, "deviceId": job.device_id, "channel": job.channel, "startTime": job.start_time,
            "endTime": job.end_time, "dataType": job.data_type, "streamType": job.stream_type, "status": job.status,
            "vendorStatus": job.vendor_status, "downloadUrl": job.vendor_url, "error": job.error,
            "createdAt": job.created_at, "readyAt": job.ready_at, "checkedAt": job.checked_at}


def request_upload(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, device_id: int,
                   q: RecordUploadIn) -> dict:
    device = device_repo.get_device(db, user.tenant_id, device_id)
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    existing = video_repo.find_active_job(db, user.tenant_id, device.id, q.channel, start, end, q.data_type,
                                          q.stream_type)
    if existing is not None:
        return ok(_job_view(existing), message="An export for this clip already exists; poll its status")
    data = expect_object(api.ftp_upload(device.terminal_no, start, end, q.channel, q.data_type, q.stream_type))
    uuid = (data or {}).get("uuid")
    if not uuid:
        raise VendorInvalidResponseError("The vendor did not return an upload id")
    try:
        with transaction(db):
            job_id = video_repo.create_job(db, {
                "tenant_id": user.tenant_id, "device_id": device.id, "requested_by": user.user_id,
                "channel": q.channel, "start_time": start, "end_time": end, "data_type": q.data_type,
                "stream_type": q.stream_type, "vendor_uuid": truncate(uuid, 64), "status": "REQUESTED"})
    except DatabaseError as exc:
        exc.details = {**(exc.details or {}), "vendorUuid": uuid}
        raise
    return ok(_job_view(video_repo.get_job(db, user.tenant_id, job_id)), message="Upload requested")


def poll_upload(db: Session, api: GpsTrackTechApi, user: CurrentUser, job_id: int) -> dict:
    job = video_repo.get_job(db, user.tenant_id, job_id)
    if job.status not in ("REQUESTED", "UPLOADING") or not job.vendor_uuid:
        return ok(_job_view(job))
    data = expect_object(api.upload_result(job.vendor_uuid))
    vendor_status = to_int((data or {}).get("status"))
    if vendor_status not in UPLOAD_STATUS:
        raise VendorInvalidResponseError("The vendor returned an unknown upload status")
    now = utcnow()
    values = {"vendor_status": vendor_status, "checked_at": now, "status": UPLOAD_STATUS[vendor_status]}
    if vendor_status == 0:
        url = (data or {}).get("url")
        if not url:
            raise VendorInvalidResponseError("The vendor reported success without a download URL")
        values.update(vendor_url=truncate(url, 1000), ready_at=now)
    elif vendor_status in UPLOAD_ERRORS:
        values["error"] = UPLOAD_ERRORS[vendor_status]
    with transaction(db):
        video_repo.update_job(db, job.id, values)
    return ok(_job_view(video_repo.get_job(db, user.tenant_id, job.id)))


def list_jobs(db: Session, user: CurrentUser, device_id: int | None, page: int, page_size: int) -> dict:
    if device_id is not None:
        device_repo.get_device(db, user.tenant_id, device_id)
    rows, total = video_repo.list_jobs(db, user.tenant_id, device_id, page, page_size)
    return ok([_job_view(r) for r in rows], meta={"total": total, "page": page, "pageSize": page_size})
