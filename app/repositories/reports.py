"""Report persistence: device_mileage_reports, device_activity_periods, device_media, report_jobs."""
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import insert_returning_id, truncate, upsert


def upsert_mileage(db: Session, tenant_id: int, device_id: int, period_start, period_end, values: dict) -> str:
    return upsert(db, t.device_mileage_reports,
                  {"device_id": device_id, "period_start": period_start, "period_end": period_end},
                  {**values, "synced_at": utcnow()}, insert_only={"tenant_id": tenant_id})


def upsert_activity(db: Session, tenant_id: int, device_id: int, kind: str, start_time, values: dict) -> str:
    return upsert(db, t.device_activity_periods, {"device_id": device_id, "kind": kind, "start_time": start_time},
                  {**values, "synced_at": utcnow()}, insert_only={"tenant_id": tenant_id})


def upsert_media(db: Session, tenant_id: int, device_id: int, file_path: str, values: dict) -> str:
    return upsert(db, t.device_media, {"device_id": device_id, "file_path": file_path},
                  {**values, "synced_at": utcnow()}, insert_only={"tenant_id": tenant_id})


def create_report_job(db: Session, tenant_id: int, user_id: int, report_type: str, params: str, fmt: str) -> int:
    now = utcnow()
    return insert_returning_id(db, t.report_jobs, {
        "tenant_id": tenant_id, "requested_by": user_id, "report_type": report_type, "params": params,
        "format": fmt, "status": "RUNNING", "created_at": now, "started_at": now})


def finish_report_job(db: Session, job_id: int, status: str, size_bytes: int | None = None,
                      error: str | None = None) -> None:
    db.execute(update(t.report_jobs).where(t.report_jobs.c.id == job_id).values(
        status=status, size_bytes=size_bytes, error=truncate(error, 500), completed_at=utcnow()))
