"""One-call wiring of the vehicle maintenance module into an existing FastAPI app.

In your existing main.py:

    from app.vehicle_maintenance_module import setup_vehicle_maintenance, shutdown_vehicle_maintenance

    @asynccontextmanager
    async def lifespan(app):
        # ... your existing startup ...
        setup_vehicle_maintenance(app)          # router + services (+ scheduler if enabled)
        yield
        shutdown_vehicle_maintenance(app)
        # ... your existing shutdown ...

If you build the router list before the app starts, you can instead call
``app.include_router(router)`` yourself and pass ``include_router=False``.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import FastAPI

from app.api.vehicle_maintenance import router
from app.core.vm_config import Settings, get_settings
from app.core.vm_database import Database
from app.integration.alert_sender import AlertStoringSender
from app.integration.directory import MaintenanceDirectory, SqlMaintenanceDirectory
from app.integration.notifier import LoggingNotificationSender, NotificationSender
from app.repositories.alerts_repository import SqlServerAlertStore
from app.repositories.vehicle_maintenance_repository import SqlServerMaintenanceRepository
from app.scheduler.maintenance_scheduler import MaintenanceScheduler
from app.services.maintenance_notification_service import MaintenanceNotificationService
from app.services.vehicle_maintenance_service import VehicleMaintenanceService
from app.utils.date_calculations import now_for_db, today_in

log = logging.getLogger(__name__)


def setup_vehicle_maintenance(
    app: FastAPI,
    settings: Optional[Settings] = None,
    connection_factory: Any = None,          # reuse your existing pyodbc connection factory here
    sender: Optional[NotificationSender] = None,
    directory: Optional[MaintenanceDirectory] = None,
    include_router: bool = True,
    start_scheduler: Optional[bool] = None,
) -> VehicleMaintenanceService:
    s = settings or get_settings()
    db = Database(s, connection_factory)
    repo = SqlServerMaintenanceRepository(db, s.db_schema, s.vehicles_table)
    directory = directory or SqlMaintenanceDirectory(db, s.db_schema, s.vehicles_table)

    def today():
        return today_in(s.app_timezone)

    def now():
        return now_for_db(s.app_timezone, s.db_timestamps_utc)

    # Every alert that is sent is saved in vehicle_maintenance_alerts (and still logged / passed to `sender`).
    alerts = SqlServerAlertStore(db, s.db_schema)
    notifications = MaintenanceNotificationService(
        AlertStoringSender(alerts, today, now, inner=sender or LoggingNotificationSender()),
        directory, s.overdue_reminder_every_days, notify_fleet_owner=s.notify_fleet_owner)

    service = VehicleMaintenanceService(
        repo, directory, notifications, today, now,
        driver_can_postpone=s.driver_can_postpone,
        max_reason_length=s.max_reason_length,
        max_page_size=s.max_page_size,
        window_for_tenant=lambda tenant_id: s.tenant_windows.get(str(tenant_id), s.default_window_days),
        alerts=alerts,
    )
    scheduler = MaintenanceScheduler(repo, notifications, today, now, s.app_timezone, s.scheduler_run_at)
    app.state.vehicle_maintenance_service = service
    app.state.vehicle_maintenance_scheduler = scheduler
    if include_router and not any(getattr(r, "path", "").startswith(router.prefix) for r in app.routes):
        app.include_router(router)
    if start_scheduler if start_scheduler is not None else s.scheduler_enabled:
        scheduler.start(run_immediately=s.scheduler_run_on_startup)
    return service


def shutdown_vehicle_maintenance(app: FastAPI) -> None:
    scheduler = getattr(app.state, "vehicle_maintenance_scheduler", None)
    if scheduler:
        scheduler.stop()