"""dbo.alarm_types / alarms / alarm_media / alarm_actions access."""
from datetime import datetime

from sqlalchemy import and_, func, insert, or_, select, true, update
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import PersistStats, insert_returning_id, upsert

OPEN_STATUSES = ("NEW", "ACKNOWLEDGED", "IN_PROGRESS")


# --- alarm types (reference data synced from vendor 5.7) ---------------------------------------------------
def alarm_types(db: Session, categories: list[int] | None = None, active_only: bool = True):
    query = select(t.alarm_types).order_by(t.alarm_types.c.category, t.alarm_types.c.id)
    if categories:
        query = query.where(t.alarm_types.c.category.in_(categories))
    if active_only:
        query = query.where(t.alarm_types.c.is_active == true())
    return db.execute(query).all()


def alarm_type_map(db: Session) -> dict:
    return {r.id: r for r in db.execute(select(t.alarm_types)).all()}


def upsert_alarm_types(db: Session, items: list[dict]) -> PersistStats:
    """Vendor fields (label/code/category) are refreshed; locally managed severity/is_active are preserved."""
    stats = PersistStats()
    now = utcnow()
    for item in items:
        values = {"code": item["code"], "label": item["label"], "category": item["category"], "updated_at": now}
        stats.add(upsert(db, t.alarm_types, {"id": item["id"]}, values))
    return stats


# --- alarms ----------------------------------------------------------------------------------------------
def find_alarm(db: Session, tenant_id: int, vendor_alarm_id: str, alarm_time: datetime):
    return db.execute(select(t.alarms.c.id, t.alarms.c.alarm_time, t.alarms.c.media_status,
                             t.alarms.c.handling_status, t.alarms.c.rule_id, t.alarms.c.ended_at,
                             t.alarms.c.duration_seconds)
                      .where(t.alarms.c.tenant_id == tenant_id, t.alarms.c.vendor_alarm_id == vendor_alarm_id,
                             t.alarms.c.alarm_time == alarm_time)
                      .with_hint(t.alarms, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")).first()


def insert_alarm(db: Session, values: dict) -> int:
    return insert_returning_id(db, t.alarms, values)


def update_alarm(db: Session, alarm_id: int, alarm_time: datetime, values: dict) -> None:
    db.execute(update(t.alarms).where(t.alarms.c.id == alarm_id, t.alarms.c.alarm_time == alarm_time)
               .values(**values))


def add_media_if_absent(db: Session, tenant_id: int, alarm_id: int, alarm_time: datetime, media_type: str,
                        url: str) -> bool:
    exists = db.execute(select(t.alarm_media.c.id).where(
        t.alarm_media.c.alarm_id == alarm_id, t.alarm_media.c.alarm_time == alarm_time,
        t.alarm_media.c.media_type == media_type, t.alarm_media.c.vendor_url == url)).first()
    if exists:
        return False
    db.execute(insert(t.alarm_media).values(tenant_id=tenant_id, alarm_id=alarm_id, alarm_time=alarm_time,
                                            media_type=media_type, vendor_url=url, status="PENDING"))
    return True


def get_alarm(db: Session, tenant_id: int, alarm_id: int, for_update: bool = False):
    query = select(t.alarms).where(t.alarms.c.tenant_id == tenant_id, t.alarms.c.id == alarm_id)
    if for_update:
        query = query.with_hint(t.alarms, "WITH (UPDLOCK, ROWLOCK)", dialect_name="mssql")
    return db.execute(query).first()


def active_user_exists(db: Session, tenant_id: int, user_id: int) -> bool:
    return db.execute(select(t.users.c.id).where(t.users.c.tenant_id == tenant_id, t.users.c.id == user_id,
                                                 t.users.c.status == "ACTIVE", t.users.c.deleted_at.is_(None))
                      ).first() is not None


def alarm_media(db: Session, alarm_id: int, alarm_time: datetime):
    return db.execute(select(t.alarm_media.c.id, t.alarm_media.c.media_type, t.alarm_media.c.channel,
                             t.alarm_media.c.vendor_url, t.alarm_media.c.status)
                      .where(t.alarm_media.c.alarm_id == alarm_id, t.alarm_media.c.alarm_time == alarm_time)
                      .order_by(t.alarm_media.c.id)).all()


def _not_hidden():
    hidden_rules = select(t.alarm_rules.c.id).where(t.alarm_rules.c.handling_mode == "HIDE")
    return or_(t.alarms.c.rule_id.is_(None), t.alarms.c.rule_id.not_in(hidden_rules))


def list_alarms(db: Session, tenant_id: int, *, start: datetime | None, end: datetime | None,
                statuses: list[str] | None, device_ids: list[int] | None, type_ids: list[int] | None,
                include_hidden: bool, page: int, page_size: int):
    conditions = [t.alarms.c.tenant_id == tenant_id]
    if start:
        conditions.append(t.alarms.c.alarm_time >= start)
    if end:
        conditions.append(t.alarms.c.alarm_time <= end)
    if statuses:
        conditions.append(t.alarms.c.handling_status.in_(statuses))
    if device_ids:
        conditions.append(t.alarms.c.device_id.in_(device_ids))
    if type_ids:
        conditions.append(t.alarms.c.alarm_type_id.in_(type_ids))
    if not include_hidden:
        conditions.append(_not_hidden())
    where = and_(*conditions)
    total = db.execute(select(func.count()).select_from(t.alarms).where(where)).scalar_one()
    rows = db.execute(
        select(t.alarms.c.id, t.alarms.c.alarm_time, t.alarms.c.device_id, t.alarms.c.alarm_type_id,
               t.alarms.c.vendor_alarm_id, t.alarms.c.severity, t.alarms.c.speed_kmh, t.alarms.c.lat,
               t.alarms.c.lon, t.alarms.c.duration_seconds, t.alarms.c.media_status, t.alarms.c.handling_status,
               t.alarms.c.handling_outcome, t.alarms.c.handled_by, t.alarms.c.handled_at, t.alarms.c.rule_id,
               t.alarm_types.c.label.label("alarm_type_label"), t.alarm_types.c.category.label("alarm_category"))
        .join(t.alarm_types, t.alarm_types.c.id == t.alarms.c.alarm_type_id, isouter=True)
        .where(where).order_by(t.alarms.c.alarm_time.desc(), t.alarms.c.id.desc())
        .offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def popup_candidates(db: Session, tenant_id: int, since: datetime, limit: int):
    return db.execute(
        select(t.alarms.c.id, t.alarms.c.alarm_time, t.alarms.c.device_id, t.alarms.c.alarm_type_id,
               t.alarms.c.severity, t.alarms.c.lat, t.alarms.c.lon, t.alarms.c.rule_id,
               t.alarm_types.c.label.label("alarm_type_label"),
               t.alarm_rules.c.popup_enabled, t.alarm_rules.c.sound_enabled, t.alarm_rules.c.handling_mode)
        .join(t.alarm_types, t.alarm_types.c.id == t.alarms.c.alarm_type_id, isouter=True)
        .join(t.alarm_rules, t.alarm_rules.c.id == t.alarms.c.rule_id, isouter=True)
        .where(t.alarms.c.tenant_id == tenant_id, t.alarms.c.handling_status == "NEW",
               t.alarms.c.alarm_time >= since, _not_hidden(),
               or_(t.alarm_rules.c.id.is_(None), t.alarm_rules.c.popup_enabled == true()))
        .order_by(t.alarms.c.severity, t.alarms.c.alarm_time.desc()).limit(limit)).all()


def open_alarm_count(db: Session, tenant_id: int) -> int:
    return db.execute(select(func.count()).select_from(t.alarms).where(
        t.alarms.c.tenant_id == tenant_id, t.alarms.c.handling_status.in_(OPEN_STATUSES), _not_hidden())).scalar_one()


# --- actions ---------------------------------------------------------------------------------------------
def alarm_actions(db: Session, alarm_id: int, alarm_time: datetime):
    return db.execute(select(t.alarm_actions).where(t.alarm_actions.c.alarm_id == alarm_id,
                                                    t.alarm_actions.c.alarm_time == alarm_time)
                      .order_by(t.alarm_actions.c.created_at, t.alarm_actions.c.id)).all()


def completed_steps(db: Session, alarm_id: int, alarm_time: datetime) -> list[int]:
    return list(db.execute(select(t.alarm_actions.c.step_no).where(
        t.alarm_actions.c.alarm_id == alarm_id, t.alarm_actions.c.alarm_time == alarm_time,
        t.alarm_actions.c.action_type == "HIGH_PRIORITY_STEP", t.alarm_actions.c.step_no.is_not(None))
        .order_by(t.alarm_actions.c.step_no)).scalars())


def insert_action(db: Session, values: dict) -> int:
    return insert_returning_id(db, t.alarm_actions, values)
