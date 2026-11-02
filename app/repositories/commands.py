"""dbo.commands / command_targets audit trail and dbo.device_passthrough_messages."""
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import insert_returning_id, upsert


def create_command(db: Session, tenant_id: int, user_id: int, command_type: str, vendor_endpoint: str,
                   payload: str, target_count: int) -> int:
    return insert_returning_id(db, t.commands, {
        "tenant_id": tenant_id, "requested_by": user_id, "command_type": command_type,
        "vendor_endpoint": vendor_endpoint, "payload": payload, "target_count": target_count, "status": "PENDING",
        "created_at": utcnow()})


def add_targets(db: Session, rows: list[dict]) -> None:
    if rows:
        db.execute(insert(t.command_targets), rows)


def finish_command(db: Session, command_id: int, status: str) -> None:
    values = {"status": status}
    if status in ("FAILED", "SUCCESS"):
        values["completed_at"] = utcnow()
    db.execute(update(t.commands).where(t.commands.c.id == command_id).values(**values))


def get_command(db: Session, tenant_id: int, command_id: int):
    row = db.execute(select(t.commands).where(t.commands.c.id == command_id,
                                              t.commands.c.tenant_id == tenant_id)).first()
    if row is None:
        raise NotFoundError("Command not found", code="COMMAND_NOT_FOUND")
    targets = db.execute(select(t.command_targets).where(t.command_targets.c.command_id == command_id)
                         .order_by(t.command_targets.c.id)).all()
    return row, targets


def upsert_passthrough(db: Session, tenant_id: int, device_id: int, vendor_message_id: str, values: dict) -> str:
    return upsert(db, t.device_passthrough_messages,
                  {"tenant_id": tenant_id, "device_id": device_id, "vendor_message_id": vendor_message_id},
                  {**values, "synced_at": utcnow()})
