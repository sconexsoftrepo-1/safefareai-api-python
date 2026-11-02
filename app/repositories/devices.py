"""Tenant-scoped device lookups. A vendor vehicle id is never assumed to equal the internal device id."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db import tables as t
from app.repositories.common import from_json


@dataclass(frozen=True)
class DeviceRef:
    id: int
    tenant_id: int
    group_id: int
    terminal_no: str
    name: str
    vendor_vehicle_id: int | None
    camera_lines: tuple[int, ...]


_COLUMNS = (t.devices.c.id, t.devices.c.tenant_id, t.devices.c.group_id, t.devices.c.terminal_no, t.devices.c.name,
            t.devices.c.vendor_vehicle_id, t.devices.c.camera_lines)


def _to_ref(row) -> DeviceRef:
    lines = from_json(row.camera_lines, [])
    lines = tuple(int(x) for x in lines if isinstance(x, int | float) or str(x).isdigit()) \
        if isinstance(lines, list) else ()
    return DeviceRef(id=row.id, tenant_id=row.tenant_id, group_id=row.group_id, terminal_no=row.terminal_no,
                     name=row.name, vendor_vehicle_id=row.vendor_vehicle_id, camera_lines=lines)


def _active(tenant_id: int):
    return select(*_COLUMNS).where(t.devices.c.tenant_id == tenant_id, t.devices.c.deleted_at.is_(None))


def get_devices(db: Session, tenant_id: int, device_ids: list[int]) -> list[DeviceRef]:
    wanted = list(dict.fromkeys(device_ids))
    rows = db.execute(_active(tenant_id).where(t.devices.c.id.in_(wanted))).all()
    found = {r.id: _to_ref(r) for r in rows}
    missing = [i for i in wanted if i not in found]
    if missing:
        # Same response for "other tenant" and "does not exist" so tenants cannot probe ids.
        raise NotFoundError("Device not found", code="DEVICE_NOT_FOUND", details={"deviceIds": missing})
    return [found[i] for i in wanted]


def get_device(db: Session, tenant_id: int, device_id: int) -> DeviceRef:
    return get_devices(db, tenant_id, [device_id])[0]


def tenant_devices(db: Session, tenant_id: int, group_id: int | None = None) -> list[DeviceRef]:
    query = _active(tenant_id).order_by(t.devices.c.id)
    if group_id is not None:
        query = query.where(t.devices.c.group_id == group_id)
    return [_to_ref(r) for r in db.execute(query).all()]


def get_group(db: Session, tenant_id: int, group_id: int):
    row = db.execute(select(t.device_groups.c.id, t.device_groups.c.vendor_group_id, t.device_groups.c.name)
                     .where(t.device_groups.c.id == group_id, t.device_groups.c.tenant_id == tenant_id,
                            t.device_groups.c.deleted_at.is_(None))).first()
    if row is None:
        raise NotFoundError("Group not found", code="GROUP_NOT_FOUND", details={"groupId": group_id})
    return row


def group_names(db: Session, tenant_id: int) -> dict[int, str]:
    rows = db.execute(select(t.device_groups.c.id, t.device_groups.c.name)
                      .where(t.device_groups.c.tenant_id == tenant_id)).all()
    return {r.id: r.name for r in rows}


def by_terminal(devices: list[DeviceRef]) -> dict[str, DeviceRef]:
    return {d.terminal_no: d for d in devices}
