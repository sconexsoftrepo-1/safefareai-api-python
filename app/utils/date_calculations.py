"""Pure date logic for vehicle maintenance. Calendar dates only, no UTC timestamps."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

PENDING = "pending"
COMPLETED = "completed"
OVERDUE = "overdue"
STATUSES = (PENDING, COMPLETED, OVERDUE)

# Reminder offsets in days before the due date (0 = due today).
#   15 and 7  -> early heads-up alerts
#   1         -> "completion check": if the maintenance is still not completed, ask for the
#                date it will be completed (the postponed date)
#   0         -> due today
# After a postponement only the 1-day-before reminder is sent (see maintenance_notification_service).
REMINDER_OFFSETS = (15, 7, 1, 0)
ACTION_OFFSETS = (1,)
POSTPONED_REMINDER_OFFSETS = (1,)
REMINDER_LABELS = {
    15: "15 days before",
    7: "1 week before",
    1: "1 day before - final completion check",
    0: "Maintenance due today",
}
# A cycle that was marked 'completed' stays 'completed' until the next cycle's first reminder day
# (due date - 15 days); from then on the vehicle is 'pending' again.
REOPEN_DAYS_BEFORE = max(REMINDER_OFFSETS)


@dataclass(frozen=True)
class Reminder:
    days_before: int
    label: str
    reminder_date: date


def to_date(value) -> Optional[date]:
    """Normalise DB values (date / datetime / ISO str / None) to date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def validate_window(window: int) -> int:
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("maintenance_time_window must be a positive whole number of days")
    return window


def calculate_expected_date(previous_date: date, window: int) -> date:
    """expected = previous actual maintenance date + window days."""
    return previous_date + timedelta(days=validate_window(window))


def next_expected_date(actual_done_date: date, window: int) -> date:
    """The next cycle starts on the actual done date: previous = done_date, expected = done_date + window."""
    return calculate_expected_date(actual_done_date, window)


def days_until(expected: date, today: date) -> int:
    return (expected - today).days


def compute_status(expected: Optional[date], today: date, stored_status: Optional[str] = None) -> str:
    """pending: today <= expected; overdue: today > expected; completed only if stored as completed."""
    if (stored_status or "").strip().lower() == COMPLETED:
        return COMPLETED
    if expected is None:
        return PENDING
    return OVERDUE if today > expected else PENDING


def effective_due(expected: Optional[date], postponed: Optional[date]) -> Optional[date]:
    """The date everything (reminders, overdue) is measured against.
    The postponed date, when one has been given, otherwise the expected date.
    ``expected_vehicle_maintenance_date`` itself is never overwritten by a postponement."""
    return postponed or expected


def effective_status(expected: Optional[date], postponed: Optional[date],
                     stored_status: Optional[str], today: date) -> str:
    """completed / pending / overdue for ``today``.

    A stored 'completed' holds until the next cycle's reminder window opens
    (``REOPEN_DAYS_BEFORE`` days before the new due date); after that it is pending/overdue again.
    """
    due = effective_due(expected, postponed)
    if (stored_status or "").strip().lower() == COMPLETED:
        if due is None or today < due - timedelta(days=REOPEN_DAYS_BEFORE):
            return COMPLETED
    return compute_status(due, today)


def reminder_schedule(expected: date) -> list[Reminder]:
    return [Reminder(o, REMINDER_LABELS[o], expected - timedelta(days=o)) for o in REMINDER_OFFSETS]


def reminder_for_day(expected: Optional[date], today: date) -> Optional[Reminder]:
    if expected is None:
        return None
    remaining = days_until(expected, today)
    if remaining in REMINDER_OFFSETS:
        return Reminder(remaining, REMINDER_LABELS[remaining], today)
    return None


def is_overdue_reminder_day(expected: date, today: date, every_days: int) -> bool:
    """Overdue reminder on day 1 overdue, then every ``every_days`` days."""
    overdue_by = (today - expected).days
    return overdue_by >= 1 and (overdue_by - 1) % max(1, every_days) == 0


def today_in(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def now_for_db(tz_name: str, utc: bool) -> datetime:
    """Naive timestamp for created_at/updated_at (DATETIME/DATETIME2 columns)."""
    tz = ZoneInfo("UTC") if utc else ZoneInfo(tz_name)
    return datetime.now(tz).replace(tzinfo=None, microsecond=0)