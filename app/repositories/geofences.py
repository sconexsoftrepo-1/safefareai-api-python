"""dbo.geofences and child tables (points, rules, bindings, reminders)."""
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db import tables as t
from app.repositories.common import insert_returning_id


def name_exists(db: Session, tenant_id: int, name: str) -> bool:
    return db.execute(select(t.geofences.c.id).where(t.geofences.c.tenant_id == tenant_id,
                                                     t.geofences.c.name == name,
                                                     t.geofences.c.deleted_at.is_(None))).first() is not None


def create_geofence(db: Session, values: dict, points: list[tuple[float, float]], rules: list[dict],
                    bindings: list[dict], reminders: list[dict]) -> int:
    geofence_id = insert_returning_id(db, t.geofences, values)
    db.execute(insert(t.geofence_points),
               [{"geofence_id": geofence_id, "seq": i, "lon": lon, "lat": lat} for i, (lon, lat) in enumerate(points)])
    if rules:
        db.execute(insert(t.geofence_rules), [{"geofence_id": geofence_id, **r} for r in rules])
    if bindings:
        db.execute(insert(t.geofence_bindings), [{"geofence_id": geofence_id, **b} for b in bindings])
    if reminders:
        db.execute(insert(t.geofence_reminders), [{"geofence_id": geofence_id, **r} for r in reminders])
    return geofence_id
