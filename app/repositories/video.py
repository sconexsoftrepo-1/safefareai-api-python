"""dbo.video_export_jobs and dbo.device_video_files."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import insert_returning_id, upsert

ACTIVE_JOB_STATUSES = ("REQUESTED", "UPLOADING", "READY", "COPYING", "STORED")


def find_active_job(db: Session, tenant_id: int, device_id: int, channel: int, start, end, data_type: int,
                    stream_type: int):
    return db.execute(select(t.video_export_jobs).where(
        t.video_export_jobs.c.tenant_id == tenant_id, t.video_export_jobs.c.device_id == device_id,
        t.video_export_jobs.c.channel == channel, t.video_export_jobs.c.start_time == start,
        t.video_export_jobs.c.end_time == end, t.video_export_jobs.c.data_type == data_type,
        t.video_export_jobs.c.stream_type == stream_type,
        t.video_export_jobs.c.status.in_(ACTIVE_JOB_STATUSES)).order_by(t.video_export_jobs.c.id.desc())).first()


def create_job(db: Session, values: dict) -> int:
    return insert_returning_id(db, t.video_export_jobs, {**values, "created_at": utcnow()})


def get_job(db: Session, tenant_id: int, job_id: int):
    row = db.execute(select(t.video_export_jobs).where(t.video_export_jobs.c.id == job_id,
                                                       t.video_export_jobs.c.tenant_id == tenant_id)).first()
    if row is None:
        raise NotFoundError("Video export job not found", code="VIDEO_JOB_NOT_FOUND")
    return row


def update_job(db: Session, job_id: int, values: dict) -> None:
    db.execute(update(t.video_export_jobs).where(t.video_export_jobs.c.id == job_id).values(**values))


def list_jobs(db: Session, tenant_id: int, device_id: int | None, page: int, page_size: int):
    where = [t.video_export_jobs.c.tenant_id == tenant_id]
    if device_id is not None:
        where.append(t.video_export_jobs.c.device_id == device_id)
    total = db.execute(select(func.count()).select_from(t.video_export_jobs).where(*where)).scalar_one()
    rows = db.execute(select(t.video_export_jobs).where(*where).order_by(t.video_export_jobs.c.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def upsert_video_file(db: Session, tenant_id: int, device_id: int, key: dict, file_size_mb) -> str:
    return upsert(db, t.device_video_files, {"device_id": device_id, **key},
                  {"file_size_mb": file_size_mb, "synced_at": utcnow()}, insert_only={"tenant_id": tenant_id})
