"""Alarm pop-up columns of dbo.user_preferences (other preference columns belong to the Java settings APIs)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.db import tables as t
from app.repositories.common import upsert

DEFAULT_CLOSE_SEC = 30
DEFAULT_MAX = 10


def alarm_popup_prefs(db: Session, tenant_id: int, user_id: int) -> dict:
    row = db.execute(select(t.user_preferences.c.alarm_popup_close_sec, t.user_preferences.c.alarm_popup_max)
                     .where(t.user_preferences.c.tenant_id == tenant_id,
                            t.user_preferences.c.user_id == user_id)).first()
    if row is None:
        return {"popupCloseSec": DEFAULT_CLOSE_SEC, "popupMax": DEFAULT_MAX}
    return {"popupCloseSec": row.alarm_popup_close_sec, "popupMax": row.alarm_popup_max}


def save_alarm_popup_prefs(db: Session, tenant_id: int, user_id: int, close_sec: int, max_popups: int) -> str:
    return upsert(db, t.user_preferences, {"tenant_id": tenant_id, "user_id": user_id},
                  {"alarm_popup_close_sec": close_sec, "alarm_popup_max": max_popups, "updated_at": utcnow()})
