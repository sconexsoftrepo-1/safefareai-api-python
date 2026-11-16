"""Bridge to YOUR existing notification infrastructure.

>>> WIRE-UP POINT 3 <<<
Implement ``NotificationSender.send`` by calling your existing email / SMS /
push / in-app service. The default sender only logs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.integration.directory import Recipient

log = logging.getLogger("vehicle_maintenance.notifications")


@dataclass(frozen=True)
class MaintenanceNotification:
    recipient: Recipient
    kind: str          # reminder_15d | reminder_7d | action_3d | action_2d | action_1d | due_today | overdue | created | postponed | completed
    title: str
    message: str
    data: dict = field(default_factory=dict)


class NotificationSender(Protocol):
    def send(self, notification: MaintenanceNotification) -> None: ...


class LoggingNotificationSender:
    def send(self, notification: MaintenanceNotification) -> None:
        log.info("[%s] to %s %s: %s", notification.kind, notification.recipient.role,
                 notification.recipient.user_id, notification.message)


class ExistingServiceSender:
    """Example adapter. Replace ``service.notify`` with your real call."""

    def __init__(self, service: Any):
        self._service = service

    def send(self, notification: MaintenanceNotification) -> None:
        self._service.notify(
            user_id=notification.recipient.user_id,
            title=notification.title,
            body=notification.message,
            payload=notification.data,
        )
