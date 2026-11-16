"""Maintenance reminders, computed entirely in Python from the CURRENT expected date.

The reminders themselves are computed, not queued; each one that is sent is also saved by the sender
(app/integration/alert_sender.py -> vehicle_maintenance_alerts). Every alert goes to the driver assigned to the vehicle
(vehicles.driver_id). Overdue notices and postponements also go to the fleet owner (created / completed only if
notify_fleet_owner is switched on). Reminders: 15 / 7 / 1 days before and on the due day; after a postponement only
the 1-day-before reminder, then overdue. Reminders are not queued: each day the scheduler
recomputes them from the current due date (the postponed date if there is one, else the expected date),
so an old date can never fire after a postponement or completion.

Duplicate prevention is in-memory only (per process). It does NOT survive a
restart and is NOT shared between multiple application instances, so delivery
is neither guaranteed nor exactly-once. Run the scheduler in one instance.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, timedelta
from typing import Callable, Iterable, Optional

from app.integration.directory import MaintenanceDirectory, Recipient
from app.integration.notifier import MaintenanceNotification, NotificationSender
from app.repositories.vehicle_maintenance_repository import MaintenanceRecord
from app.utils.date_calculations import (
    ACTION_OFFSETS,
    COMPLETED,
    POSTPONED_REMINDER_OFFSETS,
    effective_due,
    effective_status,
    is_overdue_reminder_day,
    reminder_for_day,
    reminder_schedule,
)

log = logging.getLogger(__name__)

KIND_BY_OFFSET = {
    15: "reminder_15d",   # early heads-up
    7: "reminder_7d",     # 1 week before
    1: "action_1d",       # final check
    0: "due_today",
}


class InMemoryDedupStore:
    """Thread-safe 'already sent' set. Entries older than ``retain_days`` are pruned."""

    def __init__(self, retain_days: int = 60):
        self._lock = threading.Lock()
        self._sent: dict[tuple, date] = {}
        self._retain = retain_days

    def claim(self, key: tuple, today: date) -> bool:
        with self._lock:
            if key in self._sent:
                return False
            self._sent[key] = today
            return True

    def release(self, key: tuple) -> None:
        with self._lock:
            self._sent.pop(key, None)

    def forget(self, predicate: Callable[[tuple], bool]) -> int:
        with self._lock:
            doomed = [k for k in self._sent if predicate(k)]
            for k in doomed:
                del self._sent[k]
            return len(doomed)

    def prune(self, today: date) -> None:
        cutoff = today - timedelta(days=self._retain)
        self.forget(lambda k: self._sent.get(k, today) < cutoff)

    def __len__(self) -> int:
        return len(self._sent)


def _vehicle_id(record: MaintenanceRecord) -> tuple:
    return (str(record.tenant_id), record.vehicle_number, str(record.device_id))


class MaintenanceNotificationService:
    def __init__(
        self,
        sender: NotificationSender,
        directory: MaintenanceDirectory,
        overdue_every_days: int = 1,
        dedup: Optional[InMemoryDedupStore] = None,
        notify_fleet_owner: bool = False,
    ):
        self._sender = sender
        self._directory = directory
        self._overdue_every = overdue_every_days
        self._notify_owner = notify_fleet_owner      # default: alerts go to the vehicle's driver only
        self._dedup = dedup or InMemoryDedupStore()

    @property
    def dedup(self) -> InMemoryDedupStore:
        return self._dedup

    # ---- pure calculations -------------------------------------------------
    @staticmethod
    def reminder_dates(expected: Optional[date]) -> list[dict]:
        """Reminder dates for a due date (pass the postponed date when there is one)."""
        if expected is None:
            return []
        return [
            {"type": KIND_BY_OFFSET[r.days_before], "days_before": r.days_before,
             "label": r.label, "date": r.reminder_date.isoformat()}
            for r in reminder_schedule(expected)
        ]

    def due_notification(self, record: MaintenanceRecord, today: date) -> Optional[tuple[str, tuple, str]]:
        """What (if anything) is due today for this record: (kind, dedup_key, message).

        Measured against the postponed date when there is one. Nothing is sent for a cycle that is
        completed, so the reminders only ever fire while the maintenance is still open."""
        due = effective_due(record.expected_vehicle_maintenance_date, record.postponed_date)
        if due is None or effective_status(record.expected_vehicle_maintenance_date, record.postponed_date,
                                           record.status, today) == COMPLETED:
            return None
        vid = _vehicle_id(record)
        v = record.vehicle_number
        postponed_note = (f" (postponed from {record.expected_vehicle_maintenance_date:%d %b %Y})"
                          if record.postponed_date and record.expected_vehicle_maintenance_date else "")
        reminder = reminder_for_day(due, today)
        if reminder is not None and record.postponed_date and reminder.days_before not in POSTPONED_REMINDER_OFFSETS:
            reminder = None          # after a postponement only the 1-day-before reminder is sent
        if reminder is not None:
            n = reminder.days_before
            kind = KIND_BY_OFFSET[n]
            unit = "day" if n == 1 else "days"
            if n == 0:
                msg = (f"Maintenance for vehicle {v} is due today ({due:%d %b %Y}){postponed_note} and is not "
                       f"completed. Please complete it now, or postpone the date and give a reason.")
            elif n in ACTION_OFFSETS:
                msg = (f"Maintenance for vehicle {v} is due in {n} {unit} on {due:%d %b %Y}{postponed_note} "
                       f"and is not completed yet. Please complete it.")
            elif n == 7:
                msg = f"Maintenance for vehicle {v} is due in 1 week on {due:%d %b %Y}{postponed_note}."
            else:
                msg = f"Maintenance for vehicle {v} is due in {n} {unit} on {due:%d %b %Y}{postponed_note}."
            return kind, ("reminder", *vid, due.isoformat(), n), msg
        if is_overdue_reminder_day(due, today, self._overdue_every):
            late = (today - due).days
            unit = "day" if late == 1 else "days"
            msg = (f"Maintenance for vehicle {v} is overdue by {late} {unit} (was due {due:%d %b %Y}). "
                   f"Please complete it, or postpone the date and give a reason.")
            return "overdue", ("overdue", *vid, due.isoformat(), today.isoformat()), msg
        return None

    # ---- sending ---------------------------------------------------------
    def _recipients(self, record: MaintenanceRecord, include_owner: bool = True) -> list[Recipient]:
        out: list[Recipient] = []
        fetchers = [lambda: self._directory.driver_recipients(record.tenant_id, record.vehicle_number)]
        if include_owner:
            fetchers.insert(0, lambda: self._directory.fleet_owner_recipients(record.tenant_id))
        for fetch in fetchers:
            try:
                out.extend(fetch())
            except Exception:
                log.exception("Could not resolve recipients for vehicle %s", record.vehicle_number)
        seen, unique = set(), []
        for r in out:
            if (r.role, r.user_id) not in seen:
                seen.add((r.role, r.user_id))
                unique.append(r)
        return unique

    def _send_all(self, record: MaintenanceRecord, kind: str, title: str, message: str,
                  extra: Optional[dict] = None, include_owner: Optional[bool] = None) -> int:
        data = {
            "tenant_id": record.tenant_id,
            "vehicle_number": record.vehicle_number,
            "device_id": record.device_id,
            "expected_vehicle_maintenance_date": (
                record.expected_vehicle_maintenance_date.isoformat()
                if record.expected_vehicle_maintenance_date else None),
            "postponed_date": record.postponed_date.isoformat() if record.postponed_date else None,
            "due_date": (effective_due(record.expected_vehicle_maintenance_date, record.postponed_date).isoformat()
                         if effective_due(record.expected_vehicle_maintenance_date, record.postponed_date) else None),
        }
        if extra:
            data.update(extra)
        sent = 0
        if include_owner is None:
            include_owner = self._notify_owner
        for recipient in self._recipients(record, include_owner):
            try:
                self._sender.send(MaintenanceNotification(recipient, kind, title, message, data))
                sent += 1
            except Exception:
                log.exception("Notification %s to %s failed", kind, recipient.user_id)
        return sent

    def process(self, record: MaintenanceRecord, today: date) -> Optional[str]:
        """Send today's reminder/overdue notice for one record, at most once per key. Returns kind sent."""
        due = self.due_notification(record, today)
        if due is None:
            return None
        kind, key, message = due
        if not self._dedup.claim(key, today):
            return None
        # Reminders (15 / 7 / 1 days before, due day) go to the driver. An overdue notice goes to the driver AND
        # the fleet owner: the maintenance was not done (and not postponed, or not done by the postponed date).
        to_owner = kind == "overdue"
        title = "Vehicle maintenance overdue" if to_owner else "Vehicle maintenance reminder"
        if self._send_all(record, kind, title, message, include_owner=to_owner) == 0:
            self._dedup.release(key)  # nothing delivered; allow a later retry the same day
            log.warning("Alert '%s' for vehicle %s was due but nobody received it: no ACTIVE driver is assigned "
                        "(vehicles.driver_id -> users.id, same tenant), or saving the alert failed.",
                        kind, record.vehicle_number)
            return None
        return kind

    # ---- lifecycle hooks called by the maintenance service ---------------
    def cancel_reminders(self, record: MaintenanceRecord, keep_due: Optional[date]) -> int:
        """Drop in-memory state for every due date except ``keep_due``.
        (Reminders are always recomputed from the stored dates, so old ones cannot fire anyway.)"""
        vid = _vehicle_id(record)
        keep = keep_due.isoformat() if keep_due else None
        return self._dedup.forget(lambda k: tuple(k[1:4]) == vid and k[4] != keep)

    def on_schedule_changed(self, record: MaintenanceRecord, event: str, today: date,
                            old_due: Optional[date] = None, changed_by: Optional[str] = None) -> None:
        """Called after a committed create / postpone / completion.

        ``postponed`` / ``completed`` go to the vehicle's driver (and the fleet owner only if enabled) and name
        who made the change."""
        due = effective_due(record.expected_vehicle_maintenance_date, record.postponed_date)
        self.cancel_reminders(record, keep_due=due)
        v = record.vehicle_number
        if due is not None:
            when = f"{due:%d %b %Y}"
            if event == "postponed":
                text = (f"Maintenance for vehicle {v}"
                        + (f" (due {old_due:%d %b %Y})" if old_due else "")
                        + f" has been postponed to {when}"
                        + (f" by {changed_by}" if changed_by else "") + "."
                        + (f" Reason: {record.postponed_reason}" if record.postponed_reason else ""))
            elif event == "completed":
                text = (f"Maintenance for vehicle {v} marked as completed"
                        + (f" on {record.done_date:%d %b %Y}" if record.done_date else "")
                        + f". Next maintenance due {when}.")
            elif event == "created":
                text = f"Maintenance scheduled for vehicle {v} on {when}."
            else:
                text = None
            if text:
                title = "Vehicle maintenance postponed" if event == "postponed" else "Vehicle maintenance update"
                # A postponement is sent to the driver AND the fleet owner; created / completed follow notify_fleet_owner.
                self._send_all(record, event, title, text, {"changed_by": changed_by} if changed_by else None,
                               include_owner=True if event == "postponed" else None)
        # If today is itself a reminder day for the NEW date, send it now
        # (the daily run may already have happened today).
        self.process(record, today)

    def process_many(self, records: Iterable[MaintenanceRecord], today: date) -> dict:
        counts: dict[str, int] = {}
        for record in records:
            try:
                kind = self.process(record, today)
            except Exception:
                log.exception("Reminder processing failed for %s", record.vehicle_number)
                continue
            if kind:
                counts[kind] = counts.get(kind, 0) + 1
        self._dedup.prune(today)
        return counts