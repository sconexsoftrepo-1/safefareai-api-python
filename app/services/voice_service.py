"""Fence voice reminders.

The PDF documents three different voice APIs, which are NOT interchangeable:
  10.6 GET /path/getVoice   - no parameters; the voices usable as fence broadcast reminders (id is the voiceId
                              used by /path/add `issued[].voiceId`).
  9.2  GET /voice/getVoice  - requires the vendor userId; that user's uploaded recordings (with importType/userId).
  9.1  POST /voice/addVoice - multipart upload (userId, name, file .wav); returns data = null (no new id).
Both lists are persisted to dbo.custom_voices keyed by (tenant_id, vendor_voice_id).
"""
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BadRequestError, ConfigurationError, VendorError
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import parse_vendor_time, to_float, to_int
from app.db.session import transaction
from app.repositories import voices as voice_repo
from app.repositories.common import PersistStats, truncate
from app.services.common import expect_list
from app.vendor.api import GpsTrackTechApi


def _vendor_user_id(user: CurrentUser, api: GpsTrackTechApi) -> int:
    vendor_user_id = user.vendor_user_id or api.account.vendor_user_id
    if vendor_user_id is None:
        raise ConfigurationError("No vendor user id is linked to this user or vendor account",
                                 code="VENDOR_USER_MISSING")
    return vendor_user_id


def _persist(db: Session, tenant_id: int, rows: list[dict]) -> tuple[list[dict], PersistStats]:
    stats = PersistStats()
    enriched = []
    for row in rows:
        vendor_id = to_int(row.get("id"))
        size = to_float(row.get("fileSize"))
        if vendor_id is None or not str(row.get("name") or "").strip():
            stats.add("skippedInvalid")
            enriched.append({**row, "localVoiceId": None})
            continue
        values = {"name": truncate(str(row["name"]).strip(), 120), "vendor_path": truncate(row.get("path"), 500),
                  "file_size_mb": round(size, 2) if size is not None and 0 <= size < 1_000_000 else None,
                  "ftp_base_url": truncate(row.get("ftpPath"), 300)}
        if "importType" in row:
            values["import_type"] = to_int(row.get("importType"))
        if "userId" in row:
            values["vendor_user_id"] = to_int(row.get("userId"))
        if row.get("createTime"):
            values["vendor_created_at"] = parse_vendor_time(row.get("createTime"))
        stats.add(voice_repo.upsert_vendor_voice(db, tenant_id, vendor_id, values))
        enriched.append(row)
    ids = voice_repo.voice_ids_by_vendor(db, tenant_id, [to_int(r.get("id")) for r in rows if to_int(r.get("id"))])
    for row in enriched:
        row.setdefault("localVoiceId", ids.get(to_int(row.get("id"))))
        if row.get("ftpPath") and row.get("path"):
            row["fileUrl"] = str(row["ftpPath"]).rstrip("/") + "/" + str(row["path"]).lstrip("/")
    return enriched, stats


def list_voices(db: Session, api: GpsTrackTechApi, user: CurrentUser, source: Literal["fence", "user"]) -> dict:
    response = api.path_voices() if source == "fence" else api.user_voices(_vendor_user_id(user, api))
    rows = expect_list(response)
    if not rows:
        return no_data()
    with transaction(db):
        enriched, stats = _persist(db, user.tenant_id, rows)
    return ok(enriched, meta={"source": "/path/getVoice" if source == "fence" else "/voice/getVoice",
                              "persisted": stats})


def upload_voice(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, name: str,
                 filename: str, content: bytes) -> dict:
    name = (name or "").strip()
    if not 1 <= len(name) <= 120:
        raise BadRequestError("name must be 1-120 characters", code="INVALID_VOICE_NAME")
    if not filename.lower().endswith(".wav"):
        raise BadRequestError("Only .wav files are accepted", code="INVALID_VOICE_FILE")
    if len(content) < 12 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
        raise BadRequestError("The file is not a valid WAV file", code="INVALID_VOICE_FILE")
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.voice_max_upload_mb:
        raise BadRequestError(f"The file exceeds {settings.voice_max_upload_mb} MB", code="VOICE_FILE_TOO_LARGE")
    vendor_user_id = _vendor_user_id(user, api)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")[-100:] or "voice.wav"
    api.add_voice(vendor_user_id, name, safe_filename, content)

    # The vendor returns no id; look the new recording up by name (the newest match wins).
    vendor_rows, warning = [], None
    try:
        vendor_rows = [r for r in expect_list(api.user_voices(vendor_user_id))
                       if str(r.get("name") or "").strip() == name and to_int(r.get("id")) is not None]
    except VendorError as exc:
        warning = f"Uploaded, but the voice list could not be refreshed ({exc.code}); refresh the list later"
    match = max(vendor_rows, key=lambda r: to_int(r.get("id"))) if vendor_rows else None
    vendor_id = to_int(match.get("id")) if match else None
    with transaction(db):
        local_id = voice_repo.voice_ids_by_vendor(db, user.tenant_id, [vendor_id]).get(vendor_id) if vendor_id \
            else None
        if local_id is None:
            vendor_values = {"vendor_voice_id": vendor_id, "vendor_path": truncate(match.get("path"), 500),
                             "ftp_base_url": truncate(match.get("ftpPath"), 300),
                             "import_type": to_int(match.get("importType")),
                             "vendor_created_at": parse_vendor_time(match.get("createTime"))} if match else None
            local_id = voice_repo.insert_uploaded_voice(db, user.tenant_id, name, vendor_user_id, round(size_mb, 2),
                                                        vendor_values)
    return ok({"localVoiceId": local_id, "vendorVoiceId": vendor_id, "name": name,
               "fileSizeMb": round(size_mb, 2), "synced": match is not None},
              message="Voice uploaded", meta={"warning": warning} if warning else None)
