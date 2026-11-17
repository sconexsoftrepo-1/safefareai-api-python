"""Viewing links for migrated alarm images / videos.

    GET /api/alarm-media/urls?ids=1,2,3[&expires_in=900]

alarm_media.s3_key holds the plain S3 URL of a PRIVATE bucket, which a browser cannot open (AccessDenied). This
read-only endpoint turns the stored s3_key of the given alarm_media ids into temporary signed links that open the image /
video directly (<img src>, <video src>). The bucket stays private, nothing is written, and only files inside the
alarm media folder (alerts/) can be signed.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.alarm_media_service import InvalidMediaRecord, key_from_s3_url

logger = logging.getLogger(__name__)

alarm_media_router = APIRouter(prefix="/api/alarm-media", tags=["Alarm media"])

MAX_IDS = 50


def get_alarm_media_repository():
    """Dependency (overridden in tests)."""
    from app.config.alarm_media_config import load_alarm_media_config
    from app.database.alarm_media_repository import AlarmMediaRepository
    return AlarmMediaRepository(load_alarm_media_config().table)


def get_media_storage():
    """Dependency (overridden in tests)."""
    from app.services.alarm_media_service import S3MediaStorage
    return S3MediaStorage()


def _prefix() -> str:
    from app.config.alarm_media_config import load_alarm_media_config
    return load_alarm_media_config().s3_prefix


@alarm_media_router.get("/urls")
def get_alarm_media_urls(
    ids: str = Query(..., description="alarm_media ids, comma separated, e.g. 12,13,14 (max 50)"),
    expires_in: int = Query(900, ge=60, le=3600, description="seconds the link stays valid (default 900 = 15 minutes)"),
    repo=Depends(get_alarm_media_repository),
    storage=Depends(get_media_storage),
):
    """Temporary viewing links for migrated alarm media. A record that is not migrated yet gets url = null."""
    try:
        wanted: List[int] = list(dict.fromkeys(int(x) for x in ids.split(",") if x.strip()))
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be numbers separated by commas")
    if not wanted or len(wanted) > MAX_IDS or any(i <= 0 for i in wanted):
        raise HTTPException(status_code=400, detail=f"give 1 to {MAX_IDS} positive ids")

    try:
        rows = {r["id"]: r for r in repo.fetch_by_ids(wanted)}
    except Exception:
        logger.exception("Failed to read alarm_media.")
        raise HTTPException(status_code=500, detail="Unable to retrieve alarm media")

    prefix = _prefix()
    items = []
    for record_id in wanted:
        row: Optional[dict] = rows.get(record_id)
        item = {"id": record_id, "media_type": row.get("media_type") if row else None, "url": None}
        if row is None:
            item["reason"] = "not found"
        elif not row.get("s3_key"):
            item["reason"] = "not migrated to S3 yet"
        else:
            try:
                item["url"] = storage.presigned_url(key_from_s3_url(row["s3_key"], prefix), expires_in)
            except InvalidMediaRecord:
                item["reason"] = "s3_key is not an alarm media file"
            except Exception:
                logger.exception("Could not create a link for alarm_media id=%s", record_id)
                item["reason"] = "could not create the link"
        items.append(item)
    return {"success": True, "expires_in": expires_in, "items": items}


routers = [alarm_media_router]