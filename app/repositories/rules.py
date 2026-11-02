"""dbo.alarm_rules / alarm_rule_types (alarm linkage rules)."""
from sqlalchemy import delete, insert, select, true, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db import tables as t
from app.repositories.common import insert_returning_id


def rule_type_ids(db: Session, rule_ids: list[int]) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {rid: [] for rid in rule_ids}
    if not rule_ids:
        return result
    for row in db.execute(select(t.alarm_rule_types).where(t.alarm_rule_types.c.rule_id.in_(rule_ids))
                          .order_by(t.alarm_rule_types.c.alarm_type_id)).all():
        result[row.rule_id].append(row.alarm_type_id)
    return result


def list_rules(db: Session, tenant_id: int, enabled_only: bool = False):
    query = select(t.alarm_rules).where(t.alarm_rules.c.tenant_id == tenant_id)
    if enabled_only:
        query = query.where(t.alarm_rules.c.enabled == true())
    return db.execute(query.order_by(t.alarm_rules.c.priority, t.alarm_rules.c.id)).all()


def get_rule(db: Session, tenant_id: int, rule_id: int):
    row = db.execute(select(t.alarm_rules).where(t.alarm_rules.c.tenant_id == tenant_id,
                                                 t.alarm_rules.c.id == rule_id)).first()
    if row is None:
        raise NotFoundError("Alarm rule not found", code="ALARM_RULE_NOT_FOUND")
    return row


def name_taken(db: Session, tenant_id: int, name: str, exclude_id: int | None = None) -> bool:
    query = select(t.alarm_rules.c.id).where(t.alarm_rules.c.tenant_id == tenant_id, t.alarm_rules.c.name == name)
    if exclude_id is not None:
        query = query.where(t.alarm_rules.c.id != exclude_id)
    return db.execute(query).first() is not None


def create_rule(db: Session, values: dict, type_ids: list[int]) -> int:
    rule_id = insert_returning_id(db, t.alarm_rules, values)
    set_rule_types(db, rule_id, type_ids)
    return rule_id


def update_rule(db: Session, tenant_id: int, rule_id: int, values: dict, type_ids: list[int] | None) -> None:
    db.execute(update(t.alarm_rules).where(t.alarm_rules.c.id == rule_id, t.alarm_rules.c.tenant_id == tenant_id)
               .values(**values))
    if type_ids is not None:
        set_rule_types(db, rule_id, type_ids)


def set_rule_types(db: Session, rule_id: int, type_ids: list[int]) -> None:
    db.execute(delete(t.alarm_rule_types).where(t.alarm_rule_types.c.rule_id == rule_id))
    if type_ids:
        db.execute(insert(t.alarm_rule_types), [{"rule_id": rule_id, "alarm_type_id": tid} for tid in type_ids])


def delete_rule(db: Session, tenant_id: int, rule_id: int) -> None:
    db.execute(delete(t.alarm_rule_types).where(t.alarm_rule_types.c.rule_id == rule_id))
    db.execute(delete(t.alarm_rules).where(t.alarm_rules.c.id == rule_id, t.alarm_rules.c.tenant_id == tenant_id))
