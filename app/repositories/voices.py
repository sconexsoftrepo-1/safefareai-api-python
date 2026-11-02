"""dbo.custom_voices."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import insert_returning_id, upsert


def upsert_vendor_voice(db: Session, tenant_id: int, vendor_voice_id: int, values: dict) -> str:
    """Upsert on (tenant_id, vendor_voice_id). A locally uploaded row that has no vendor id yet and the same name
    is linked instead of creating a duplicate."""
    linked = db.execute(select(t.custom_voices.c.id).where(
        t.custom_voices.c.tenant_id == tenant_id, t.custom_voices.c.vendor_voice_id == vendor_voice_id)).first()
    if linked is None:
        pending = db.execute(select(t.custom_voices.c.id).where(
            t.custom_voices.c.tenant_id == tenant_id, t.custom_voices.c.vendor_voice_id.is_(None),
            t.custom_voices.c.name == values.get("name"), t.custom_voices.c.deleted_at.is_(None))
            .order_by(t.custom_voices.c.id)).first()
        if pending is not None:
            db.execute(update(t.custom_voices).where(t.custom_voices.c.id == pending.id)
                       .values(vendor_voice_id=vendor_voice_id, **values, synced_at=utcnow()))
            return "updated"
    return upsert(db, t.custom_voices, {"tenant_id": tenant_id, "vendor_voice_id": vendor_voice_id},
                  {**values, "synced_at": utcnow()}, insert_only={"source": "VENDOR", "created_at": utcnow()})


def insert_uploaded_voice(db: Session, tenant_id: int, name: str, vendor_user_id: int | None,
                          file_size_mb: float, vendor_values: dict | None = None) -> int:
    """Record an upload. `vendor_values` (vendor_voice_id, vendor_path, ...) is set when the vendor id is known."""
    now = utcnow()
    return insert_returning_id(db, t.custom_voices, {
        "tenant_id": tenant_id, "name": name, "source": "UPLOAD", "vendor_user_id": vendor_user_id,
        "file_size_mb": file_size_mb, "created_at": now, **(vendor_values or {}),
        **({"synced_at": now} if vendor_values else {})})


def voice_ids_by_vendor(db: Session, tenant_id: int, vendor_ids: list[int]) -> dict[int, int]:
    if not vendor_ids:
        return {}
    rows = db.execute(select(t.custom_voices.c.id, t.custom_voices.c.vendor_voice_id).where(
        t.custom_voices.c.tenant_id == tenant_id, t.custom_voices.c.vendor_voice_id.in_(vendor_ids))).all()
    return {r.vendor_voice_id: r.id for r in rows}


def get_voice_vendor_id(db: Session, tenant_id: int, voice_id: int) -> int:
    row = db.execute(select(t.custom_voices.c.vendor_voice_id).where(
        t.custom_voices.c.tenant_id == tenant_id, t.custom_voices.c.id == voice_id,
        t.custom_voices.c.deleted_at.is_(None))).first()
    if row is None:
        raise NotFoundError("Custom voice not found", code="VOICE_NOT_FOUND", details={"voiceId": voice_id})
    if row.vendor_voice_id is None:
        raise ConflictError("Custom voice is not yet registered with the vendor; refresh the voice list first",
                            code="VOICE_NOT_SYNCED", details={"voiceId": voice_id})
    return row.vendor_voice_id
