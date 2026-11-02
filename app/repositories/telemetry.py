"""dbo.device_latest_state and dbo.device_positions."""
from datetime import datetime

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db import tables as t
from app.repositories.common import upsert


def upsert_latest_state(db: Session, tenant_id: int, device_id: int, values: dict) -> str:
    return upsert(db, t.device_latest_state, {"device_id": device_id}, values, insert_only={"tenant_id": tenant_id})


def insert_positions(db: Session, tenant_id: int, device_id: int, points: list[dict]) -> int:
    """Insert track points that are not stored yet (PK device_id + device_time). Returns rows inserted."""
    if not points:
        return 0
    times = [p["device_time"] for p in points]
    existing = set(db.execute(select(t.device_positions.c.device_time).where(
        t.device_positions.c.device_id == device_id,
        t.device_positions.c.device_time >= min(times), t.device_positions.c.device_time <= max(times))).scalars())
    seen: set[datetime] = set()
    fresh = []
    for p in points:
        if p["device_time"] in existing or p["device_time"] in seen:
            continue
        seen.add(p["device_time"])
        fresh.append({"tenant_id": tenant_id, "device_id": device_id, **p})
    if fresh:
        db.execute(insert(t.device_positions), fresh)
    return len(fresh)
