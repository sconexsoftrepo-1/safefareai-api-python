from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.exceptions import BadRequestError
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.services import voice_service

router = APIRouter(prefix="/voices", tags=["Fence voice reminders"], responses=ERROR_RESPONSES)


@router.get("", **ENVELOPE, summary="List custom voices",
            description="source=fence: vendor 10.6 /path/getVoice (voices usable in fence reminders). "
                        "source=user: vendor 9.2 /voice/getVoice for the linked vendor user. "
                        "Both upsert dbo.custom_voices.")
def list_voices(source: Literal["fence", "user"] = Query("fence"),
                user=Depends(require_permissions("geofence.manage", "command.send", any_of=True)),
                db: Session = Depends(get_db), api=Depends(get_vendor_api)):
    return voice_service.list_voices(db, api, user, source)


@router.post("", **ENVELOPE, status_code=201, summary="Upload a custom voice (.wav)",
             description="Vendor 9.1 /voice/addVoice (multipart). Records dbo.custom_voices.")
async def upload_voice(name: str = Form(..., max_length=120), file: UploadFile = File(...),
                       user=Depends(require_permissions("geofence.manage")), db: Session = Depends(get_db),
                       api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    limit = int(settings.voice_max_upload_mb * 1024 * 1024)
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise BadRequestError(f"The file exceeds {settings.voice_max_upload_mb} MB", code="VOICE_FILE_TOO_LARGE")
    return await run_in_threadpool(voice_service.upload_voice, db, api, user, settings, name,
                                   file.filename or "voice.wav", content)
