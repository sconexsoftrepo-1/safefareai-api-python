"""Daily maintenance job: sync status and send reminders / completion checks.

Every run, for each vehicle that is not completed: 15 and 7 days before the due date a heads-up is sent; on
the last 3, 2 and 1 days the job checks again whether the maintenance is completed and, if not, asks for the
completion (postponed) date. The due date is the postponed date when one exists. A cycle marked completed is
reopened as pending once its own 15-day window begins.


Uses a plain background thread so it works with any FastAPI setup. If your
project already runs APScheduler/Celery beat, schedule ``MaintenanceScheduler.run_once``
there instead and do not call ``start()``.

Concurrency: a non-blocking lock guarantees one run at a time per process.
Run the scheduler in ONE application instance only (VM_SCHEDULER_ENABLED=false
on the others); in-memory dedup is not shared between processes.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from app.repositories.vehicle_maintenance_repository import MaintenanceRepository
from app.services.maintenance_notification_service import MaintenanceNotificationService
from app.utils.date_calculations import COMPLETED, effective_due, effective_status

log = logging.getLogger(__name__)


@dataclass
class RunSummary:
    ran: bool
    run_date: Optional[date] = None
    scanned: int = 0
    status_updates: int = 0
    notifications: dict = field(default_factory=dict)
    errors: int = 0


class MaintenanceScheduler:
    def __init__(
        self,
        repository: MaintenanceRepository,
        notifications: MaintenanceNotificationService,
        today: Callable[[], date],
        now: Callable[[], datetime],
        timezone: str,
        run_at: time = time(8, 0),
    ):
        self._repo = repository
        self._notify = notifications
        self._today = today
        self._now = now
        self._tz = ZoneInfo(timezone)
        self._run_at = run_at
        self._run_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def run_once(self, today: Optional[date] = None) -> RunSummary:
        if not self._run_lock.acquire(blocking=False):
            log.warning("Maintenance scheduler already running; skipped overlapping run")
            return RunSummary(ran=False)
        try:
            today = today or self._today()
            summary = RunSummary(ran=True, run_date=today)
            with self._repo.unit_of_work() as s:
                records = s.all_schedules()
            summary.scanned = len(records)
            def wanted_for(r):
                return effective_status(r.expected_vehicle_maintenance_date, r.postponed_date, r.status, today)

            active = []
            for record in records:
                if effective_due(record.expected_vehicle_maintenance_date, record.postponed_date) is None:
                    continue
                wanted = wanted_for(record)
                if (record.status or "").strip().lower() != wanted:
                    try:
                        with self._repo.unit_of_work() as s:
                            # Re-read under lock: the row may have been postponed/completed meanwhile.
                            fresh = s.find(record.tenant_id, record.vehicle_number, record.device_id, for_update=True)
                            if len(fresh) == 1:
                                f = fresh[0]
                                wanted = wanted_for(f)
                                if (f.status or "").strip().lower() != wanted:
                                    s.update(f.tenant_id, f.vehicle_number, f.device_id,
                                             {"status": wanted, "updated_at": self._now()})
                                    summary.status_updates += 1
                                f.status = wanted
                                record = f
                    except Exception:
                        summary.errors += 1
                        log.exception("Status sync failed for vehicle %s", record.vehicle_number)
                if wanted_for(record) == COMPLETED:
                    continue  # completed and the next cycle's window has not opened yet
                active.append(record)
            summary.notifications = self._notify.process_many(active, today)
            log.info("Maintenance scheduler run %s: %s", today, summary)
            return summary
        finally:
            self._run_lock.release()

    # ------------------------------------------------------------------
    def seconds_until_next_run(self, now: Optional[datetime] = None) -> float:
        now = now or datetime.now(self._tz)
        target = datetime.combine(now.date(), self._run_at, tzinfo=self._tz)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    def _loop(self) -> None:
        while not self._stop.wait(self.seconds_until_next_run()):
            try:
                self.run_once()
            except Exception:
                log.exception("Maintenance scheduler run failed")

    def start(self, run_immediately: bool = False) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        if run_immediately:
            threading.Thread(target=self._safe_run, name="vm-scheduler-startup", daemon=True).start()
        self._thread = threading.Thread(target=self._loop, name="vm-scheduler", daemon=True)
        self._thread.start()
        log.info("Maintenance scheduler started; next run in %.0f s", self.seconds_until_next_run())

    def _safe_run(self) -> None:
        try:
            self.run_once()
        except Exception:
            log.exception("Maintenance scheduler startup run failed")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
