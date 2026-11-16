"""Saves every maintenance notification into ``vehicle_maintenance_alerts``.

The notification service calls ``send()`` once per recipient (normally the vehicle's driver). This sender
writes that notification to the alerts table (so the app can show it) and then passes it on to the
normal sender (by default: the log line).

Reminder alerts are stored at most once per (user, vehicle, kind, due date, day) - see
``alerts_repository.REMINDER_KINDS`` - so a restart or a second run cannot create duplicates.
If the database write fails the exception is raised, the notification service logs it and
retries on the next run.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable, Optional

from app.integration.notifier import MaintenanceNotification, NotificationSender

log = logging.getLogger(__name__)


def _to_date(value) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


class AlertStoringSender:
    def __init__(self, store, today: Callable[[], date], now: Callable[[], datetime],
                 inner: Optional[NotificationSender] = None):
        self._store = store
        self._today = today
        self._now = now
        self._inner = inner

    def send(self, notification: MaintenanceNotification) -> None:
        data = notification.data or {}
        stored = self._store.add(
            data.get("tenant_id"),
            data.get("vehicle_number"),
            notification.recipient.user_id,
            notification.recipient.role,
            notification.kind,
            notification.title,
            notification.message,
            _to_date(data.get("due_date")),
            self._today(),
            self._now(),
        )
        log.info("Alert %s for vehicle %s -> user %s: %s", notification.kind, data.get("vehicle_number"),
                 notification.recipient.user_id, "stored" if stored else "already stored today, skipped")
        if self._inner is not None:
            self._inner.send(notification)