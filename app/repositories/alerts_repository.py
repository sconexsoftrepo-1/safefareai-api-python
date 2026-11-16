"""Stores every maintenance alert against the user it was sent to (normally the vehicle's driver).

Table: ``vehicle_maintenance_alerts`` (see migrations/003_create_alerts_table.sql). Its own table: it does not touch
``vehicle_maintenance``. Reminder alerts are stored at most once per (user, vehicle, kind, due date, day), so
restarting the server or running the job twice cannot create duplicates. This also makes the "already sent" check
survive restarts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional, Protocol

from app.core.vm_database import Database

ALERTS_TABLE = "vehicle_maintenance_alerts"
# Reminder kinds are stored once per day; event kinds (created / postponed / completed) are always stored.
REMINDER_KINDS = frozenset({"reminder_15d", "reminder_7d", "action_3d", "action_2d", "action_1d", "due_today", "overdue"})


@dataclass
class AlertRow:
    vehicle_number: str
    kind: str
    title: str
    message: str
    due_date: Optional[date]
    alert_date: Optional[date]
    created_at: Optional[datetime]
    is_read: bool


class AlertStore(Protocol):
    def add(self, tenant_id, vehicle_number: str, user_id, role: str, kind: str, title: str, message: str,
            due_date: Optional[date], alert_date: date, created_at: datetime) -> bool: ...
    def list_for_user(self, user_id, offset: int, limit: int, vehicle_number: Optional[str] = None) -> tuple[list[AlertRow], int]: ...


def _to_date(v) -> Optional[date]:
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


class SqlServerAlertStore:
    def __init__(self, db: Database, schema: str = "dbo"):
        self._db = db
        self._t = f"[{schema}].[{ALERTS_TABLE}]"

    def add(self, tenant_id, vehicle_number, user_id, role, kind, title, message, due_date, alert_date, created_at) -> bool:
        cols = "(tenant_id, vehicle_number, user_id, role, kind, title, message, due_date, alert_date, created_at, is_read)"
        values = [tenant_id, vehicle_number, str(user_id), role, kind, title, message, due_date, alert_date, created_at]
        if kind in REMINDER_KINDS:
            sql = (f"INSERT INTO {self._t} {cols} SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0 "
                   f"WHERE NOT EXISTS (SELECT 1 FROM {self._t} WHERE tenant_id = ? AND vehicle_number = ? "
                   "AND user_id = ? AND kind = ? AND due_date = ? AND alert_date = ?)")
            values += [tenant_id, vehicle_number, str(user_id), kind, due_date, alert_date]
        else:
            sql = f"INSERT INTO {self._t} {cols} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)"
        with self._db.transaction() as conn:
            cur = conn.cursor()
            cur.execute(sql, *values)
            return cur.rowcount > 0

    def list_for_user(self, user_id, offset, limit, vehicle_number=None):
        """The newest alerts of one user (the driver), newest first; optionally only one vehicle's."""
        where = "WHERE user_id = ?" + (" AND vehicle_number = ?" if vehicle_number else "")
        params = [str(user_id)] + ([vehicle_number] if vehicle_number else [])
        with self._db.transaction() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self._t} {where}", *params)
            total = int(cur.fetchone()[0])
            cur.execute(
                "SELECT vehicle_number, kind, title, message, due_date, alert_date, created_at, is_read "
                f"FROM {self._t} {where} ORDER BY created_at DESC, alert_date DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                *params, offset, limit)
            rows = [AlertRow(str(r[0]).strip(), r[1], r[2], r[3], _to_date(r[4]), _to_date(r[5]), r[6], bool(r[7]))
                    for r in cur.fetchall()]
        return rows, total