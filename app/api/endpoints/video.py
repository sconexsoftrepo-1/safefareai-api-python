from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.schemas.video import LiveSessionIn, RecordQueryIn, RecordUploadIn
from app.services import command_service, video_service

router = APIRouter(prefix="/video", tags=["Live video & Playback"], responses=ERROR_RESPONSES)
any_video = require_permissions("video.live", "video.playback", any_of=True)


@router.get("/sdk-token", **ENVELOPE, summary="Temporary audio/video SDK token (5 minutes)",
            description="Vendor 4.7 getAvSdkTempTk. The permanent secret key is never returned. Not persisted.")
def sdk_token(user=Depends(any_video), api=Depends(get_vendor_api)):
    return video_service.temp_token(api)


@router.get("/embed-config", **ENVELOPE, summary="Vendor iframe demo pages + temporary token",
            description="Vendor 4.2/4.3 are browser-only iframe pages (not JSON APIs); this returns their URLs "
                        "with a fresh 4.7 temporary token.")
def embed_config(user=Depends(any_video), api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return video_service.embed_config(api, settings)


@router.post("/devices/{device_id}/live-session", **ENVELOPE,
             summary="Prepare live video (wake device if ACC is off, issue temp token)",
             description="Vendor 3.1 (ACC state) -> 8.3 wakenDevice when needed -> 4.7 temp token.")
def live_session(body: LiveSessionIn, device_id: int = Path(gt=0), user=Depends(require_permissions("video.live")),
                 db: Session = Depends(get_db), api=Depends(get_vendor_api),
                 settings: Settings = Depends(get_settings)):
    return video_service.live_session(db, api, user, settings, device_id, body.auto_wake)


@router.post("/devices/{device_id}/wake", **ENVELOPE, summary="Wake the device for live video",
             description="Vendor 8.3 wakenDevice. Recorded in dbo.commands / command_targets. Never auto-retried.")
def wake(device_id: int = Path(gt=0), user=Depends(require_permissions("video.live")),
         db: Session = Depends(get_db), api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return command_service.wake(db, api, user, settings, [device_id])


@router.get("/devices/{device_id}/calendar", **ENVELOPE,
            summary="Recording calendar (days with recordings)", description="Vendor 4.6 monthlyCalendar.")
def calendar(device_id: int = Path(gt=0), year_month: str = Query(alias="yearMonth", examples=["2025-10"]),
             user=Depends(require_permissions("video.playback")), db: Session = Depends(get_db),
             api=Depends(get_vendor_api)):
    return video_service.calendar(db, api, user, device_id, year_month)


@router.post("/devices/{device_id}/recordings/query", **ENVELOPE,
             summary="Recording segments per channel", description="Vendor 4.1 devRecordQuery. "
                                                                   "Persists dbo.device_video_files.")
def recordings(body: RecordQueryIn, device_id: int = Path(gt=0), user=Depends(require_permissions("video.playback")),
               db: Session = Depends(get_db), api=Depends(get_vendor_api),
               settings: Settings = Depends(get_settings)):
    return video_service.recordings(db, api, user, settings, device_id, body)


@router.post("/devices/{device_id}/recordings/export", **ENVELOPE, status_code=202,
             summary="Request a recording clip upload (download)",
             description="Vendor 4.4 devFtpUpload. Creates dbo.video_export_jobs; identical active requests are "
                         "reused instead of re-sending the device command.")
def export_recording(body: RecordUploadIn, device_id: int = Path(gt=0),
                     user=Depends(require_permissions("video.playback")), db: Session = Depends(get_db),
                     api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return video_service.request_upload(db, api, user, settings, device_id, body)


@router.get("/exports", **ENVELOPE, summary="Download center: recording export jobs")
def list_exports(device_id: int | None = Query(None, alias="deviceId", gt=0), page: int = Query(1, ge=1),
                 page_size: int = Query(50, alias="pageSize", ge=1, le=500),
                 user=Depends(require_permissions("video.playback")), db: Session = Depends(get_db)):
    return video_service.list_jobs(db, user, device_id, page, page_size)


@router.get("/exports/{job_id}", **ENVELOPE, summary="Poll a recording export",
            description="Vendor 4.5 getUploadResult while the job is REQUESTED/UPLOADING; updates the job.")
def poll_export(job_id: int = Path(gt=0), user=Depends(require_permissions("video.playback")),
                db: Session = Depends(get_db), api=Depends(get_vendor_api)):
    return video_service.poll_upload(db, api, user, job_id)
