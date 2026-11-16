"""Business rules for vehicle maintenance (single current-cycle row per vehicle)."""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from app.integration.auth_adapter import CurrentUser, Role
from app.integration.directory import MaintenanceDirectory
from app.repositories.vehicle_maintenance_repository import (
    AccessScope,
    ListFilters,
    MaintenanceRecord,
    MaintenanceRepository,
    MaintenanceSession,
)
from app.schemas.vehicle_maintenance import (
    CompleteRequest,
    CreateMaintenanceRequest,
    PostponeRequest,
)
from app.services.errors import MaintenanceError
from app.services.maintenance_notification_service import MaintenanceNotificationService
from app.utils.date_calculations import (
    COMPLETED,
    calculate_expected_date,
    compute_status,
    days_until,
    effective_due,
    effective_status,
    STATUSES,
)

log = logging.getLogger(__name__)

MANAGERS = (Role.ADMIN, Role.FLEET_OWNER)
EVERYONE = (Role.ADMIN, Role.FLEET_OWNER, Role.DRIVER)
CREATORS = (Role.FLEET_OWNER,)                       # only Fleet Owners create schedules
DRIVER_ONLY = (Role.DRIVER,)                         # only the Driver completes or postpones; Fleet Owner/Admin only view
LATEST_ALERTS = 3                                    # the UI shows only the driver's latest 3 alerts
DEFAULT_WINDOW_DAYS = 30                             # used only if no organization default is configured


class VehicleMaintenanceService:
    def __init__(
        self,
        repository: MaintenanceRepository,
        directory: MaintenanceDirectory,
        notifications: MaintenanceNotificationService,
        today: Callable[[], date],
        now: Callable[[], datetime],
        driver_can_postpone: bool = True,
        max_reason_length: int = 500,
        max_page_size: int = 100,
        window_for_tenant: Optional[Callable[[Any], int]] = None,
        alerts: Any = None,
    ):
        self._repo = repository
        self._directory = directory
        self._notify = notifications
        self._today = today
        self._now = now
        self._driver_can_postpone = driver_can_postpone
        self._max_reason = max_reason_length
        self._max_page = max_page_size
        self._alerts = alerts
        self._window_for_tenant = window_for_tenant or (lambda tenant_id: DEFAULT_WINDOW_DAYS)

    # =====================================================================
    # Access control helpers
    # =====================================================================
    @staticmethod
    def _require_role(user: CurrentUser, allowed: tuple, action: str) -> None:
        if user.role not in allowed:
            raise MaintenanceError(403, f"You are not allowed to {action}")

    @staticmethod
    def _own_tenant(user: CurrentUser) -> Any:
        """Tenant always comes from the logged-in user, never from the request."""
        if user.tenant_id is None:
            raise MaintenanceError(403, "No tenant is associated with this account")
        return user.tenant_id

    @staticmethod
    def _tenant_for_vehicle(session: MaintenanceSession, user: CurrentUser, vehicle_number: str) -> Any:
        """Fleet Owner / Driver: their own tenant. Admin: their own tenant if they have one,
        otherwise the (single) authorised tenant that has a schedule for this vehicle."""
        if user.role != Role.ADMIN or user.tenant_id is not None:
            return VehicleMaintenanceService._own_tenant(user)
        allowed = list(user.authorized_tenant_ids) if user.authorized_tenant_ids is not None else None
        tenants = session.tenants_for_vehicle(vehicle_number, allowed)
        if not tenants:
            raise MaintenanceError(404, "Maintenance schedule not found")
        if len(tenants) > 1:
            raise MaintenanceError(409, "This vehicle number exists in more than one tenant; "
                                        "log in with a tenant-specific admin account")
        return tenants[0]

    def _driver_vehicles(self, user: CurrentUser, tenant_id) -> set[str]:
        return {v.strip().upper() for v in self._directory.driver_vehicle_numbers(tenant_id, user.user_id)}

    def _check_vehicle_access(self, user: CurrentUser, tenant_id, vehicle_number: str) -> None:
        if user.role == Role.DRIVER and vehicle_number.strip().upper() not in self._driver_vehicles(user, tenant_id):
            raise MaintenanceError(403, "You can only access vehicles assigned to you")

    def _scope(self, user: CurrentUser) -> AccessScope:
        if user.role == Role.ADMIN:
            if user.tenant_id is not None and user.authorized_tenant_ids is None:
                return AccessScope(tenant_ids=[user.tenant_id])
            tenants = list(user.authorized_tenant_ids) if user.authorized_tenant_ids is not None else None
            return AccessScope(tenant_ids=tenants)
        tenant = self._own_tenant(user)
        if user.role == Role.DRIVER:
            vehicles = sorted(self._directory.driver_vehicle_numbers(tenant, user.user_id))
            return AccessScope(tenant_ids=[tenant], vehicle_numbers=vehicles)
        return AccessScope(tenant_ids=[tenant])

    # =====================================================================
    # Record helpers
    # =====================================================================
    def _reason(self, reason: Optional[str]) -> Optional[str]:
        if reason is not None and len(reason) > self._max_reason:
            raise MaintenanceError(400, f"reason must be at most {self._max_reason} characters")
        return reason

    @staticmethod
    def _load(session: MaintenanceSession, tenant_id, vehicle_number: str,
              for_update: bool = False) -> MaintenanceRecord:
        """A schedule is identified by tenant_id (from login) + vehicle_number (from the URL)."""
        rows = session.find(tenant_id, vehicle_number, for_update=for_update)
        if not rows:
            raise MaintenanceError(404, "Maintenance schedule not found")
        if len(rows) > 1:
            raise MaintenanceError(
                409, "More than one maintenance row exists for this vehicle in your tenant, so it cannot be "
                     "identified uniquely. Remove the extra rows and retry.",
                {"device_ids": sorted({str(r.device_id) for r in rows})})
        return rows[0]

    def _write(self, session: MaintenanceSession, record: MaintenanceRecord, fields: dict) -> MaintenanceRecord:
        fields = {**fields, "updated_at": self._now()}
        count = session.update(record.tenant_id, record.vehicle_number, record.device_id, fields)
        if count != 1:  # raising inside the unit of work rolls the transaction back
            raise MaintenanceError(409, "The schedule could not be updated uniquely; no changes were saved")
        return replace(record, **fields)

    def view(self, record: MaintenanceRecord, effective_status_value: Optional[str] = None,
             drivers: Optional[dict] = None) -> dict:
        today = self._today()
        if drivers is None:
            drivers = self._drivers_for([record])
        driver = drivers.get((record.tenant_id, record.vehicle_number.strip().upper())) or {}
        expected = record.expected_vehicle_maintenance_date
        due = effective_due(expected, record.postponed_date)
        return {
            "tenant_id": record.tenant_id,
            "vehicle_number": record.vehicle_number,
            "device_id": record.device_id,
            "driver_id": driver.get("driver_id"),
            "driver_name": driver.get("driver_name"),     # from users.display_name; never stored here
            "previous_vehicle_maintenance_date": _iso(record.previous_vehicle_maintenance_date),
            "maintenance_time_window": record.maintenance_time_window,
            "expected_vehicle_maintenance_date": _iso(expected),
            "postponed_date": _iso(record.postponed_date),      # null until the driver postpones
            "postponed_reason": record.postponed_reason,
            "postponed_by": record.postponed_by,
            "postponed_at": _iso(record.postponed_at),
            "due_date": _iso(due),                      # postponed date if any, else expected date
            "done_date": _iso(record.done_date),
            "status": effective_status_value or effective_status(expected, record.postponed_date, record.status, today),
            "reason": record.reason,
            "created_at": _iso(record.created_at),
            "updated_at": _iso(record.updated_at),
            "days_until_due": days_until(due, today) if due else None,
            "reminder_schedule": self._notify.reminder_dates(due),
        }

    def _after_commit(self, record: MaintenanceRecord, event: str, old_due: Optional[date] = None,
                      changed_by: Optional[str] = None) -> None:
        try:
            self._notify.on_schedule_changed(record, event, self._today(), old_due, changed_by)
        except Exception:  # notification problems must never undo a committed change
            log.exception("Post-commit notification failed for %s", record.vehicle_number)

    # =====================================================================
    # API 1: create
    # =====================================================================
    def create(self, user: CurrentUser, body: CreateMaintenanceRequest) -> dict:
        self._require_role(user, CREATORS, "create maintenance schedules (Fleet Owner only)")
        tenant = self._own_tenant(user)
        vehicle = body.vehicle_number.strip()
        prev = body.previous_vehicle_maintenance_date
        # The window is not sent: it is the default (30 days, or the organization's configured value).
        window = self._window_for_tenant(tenant)
        expected = calculate_expected_date(prev, window)        # previous + window
        today = self._today()
        now = self._now()
        record = MaintenanceRecord(
            tenant_id=tenant,
            vehicle_number=vehicle,
            device_id=None,                      # resolved from vehicle_number inside the transaction
            previous_vehicle_maintenance_date=prev,
            maintenance_time_window=window,
            expected_vehicle_maintenance_date=expected,
            done_date=None,
            status=compute_status(expected, today),
            reason=self._reason(body.reason),
            created_at=now,
            updated_at=now,
        )
        with self._repo.unit_of_work() as s:
            devices = s.devices_for_vehicle(tenant, vehicle)
            if not devices:
                raise MaintenanceError(404, "Vehicle not found in your organization")
            if not self._directory.driver_recipients(tenant, vehicle):
                raise MaintenanceError(
                    409, "No driver is assigned to this vehicle (vehicles.driver_id is empty), so the alerts "
                         "would have nobody to reach. Set vehicles.driver_id first")
            distinct = sorted({d for d in devices if d is not None}, key=str)
            if len(distinct) > 1:
                raise MaintenanceError(
                    409, "This vehicle has more than one device registered, so the device cannot be chosen "
                         "automatically", {"device_ids": [str(d) for d in distinct]})
            record = replace(record, device_id=distinct[0] if distinct else None)
            # HOLDLOCK range lock: a concurrent create for the same vehicle waits here.
            if s.find(tenant, vehicle, for_update=True):
                raise MaintenanceError(409, "A maintenance schedule already exists for this vehicle")
            s.insert(record)
        self._after_commit(record, "created")
        return self.view(record)

    # =====================================================================
    # Driver identity: the driver enters their own driver_id (= users.id = vehicles.driver_id)
    # =====================================================================
    def _driver_tenant(self, driver_id, vehicle_number: str) -> Any:
        """The tenant of this vehicle, but only if ``driver_id`` is the driver assigned to it in vehicles.driver_id."""
        tenants = self._directory.tenants_of_driver_vehicle(driver_id, vehicle_number)
        if not tenants:
            raise MaintenanceError(403, "This vehicle is not assigned to that driver_id")
        if len(tenants) > 1:
            raise MaintenanceError(409, "This vehicle number exists in more than one tenant, so it cannot be "
                                        "identified from the driver_id alone")
        return tenants[0]

    @staticmethod
    def _driver_label(driver_id) -> str:
        return f"Driver {driver_id}"

    def _drivers_for(self, records: list) -> dict:
        """{(tenant_id, VEHICLE): {driver_id, driver_name}} from vehicles.driver_id -> users.display_name."""
        by_tenant: dict = {}
        for r in records:
            by_tenant.setdefault(r.tenant_id, set()).add(r.vehicle_number)
        out = {}
        for tenant, numbers in by_tenant.items():
            found = self._directory.vehicle_drivers(tenant, sorted(numbers))
            for number, info in found.items():
                out[(tenant, number.strip().upper())] = info
        return out

    def _manager(self, user: Optional[CurrentUser], action: str) -> CurrentUser:
        if user is None:
            raise MaintenanceError(401, "Authentication required")
        self._require_role(user, MANAGERS, f"{action}")
        return user

    # =====================================================================
    # Alerts stored for the driver (vehicle_maintenance_alerts)
    # =====================================================================
    def list_alerts(self, user: Optional[CurrentUser], vehicle_number: str) -> dict:
        """Latest ``LATEST_ALERTS`` (3) alerts of a vehicle, for its driver. Used the same way by the fleet owner
        and the driver: only the vehicle_number is sent; the driver comes from vehicles.driver_id."""
        if self._alerts is None:
            raise MaintenanceError(500, "Alerts storage is not configured")
        vehicle_number = vehicle_number.strip()
        if user is None or (user.role == Role.ADMIN and user.authorized_tenant_ids is None):
            allowed = None
        elif user.role == Role.ADMIN:
            allowed = list(user.authorized_tenant_ids)
        else:
            allowed = [self._own_tenant(user)]
        with self._repo.unit_of_work() as s:
            tenants = s.tenants_for_vehicle(vehicle_number, allowed)
        if not tenants:
            raise MaintenanceError(404, "Maintenance schedule not found")
        if len(tenants) > 1:
            raise MaintenanceError(409, "This vehicle number exists in more than one tenant")
        info = self._directory.vehicle_drivers(tenants[0], [vehicle_number])
        match = next((v for k, v in info.items() if k.strip().upper() == vehicle_number.upper()), None)
        if not match or match.get("driver_id") is None:
            raise MaintenanceError(404, "No driver is assigned to this vehicle")
        rows, total = self._alerts.list_for_user(match["driver_id"], 0, LATEST_ALERTS, vehicle_number)
        return {
            "vehicle_number": vehicle_number,
            "driver_id": match["driver_id"],
            "driver_name": match.get("driver_name"),
            "items": [self._alert_view(r) for r in rows],
            "total_alerts": total,          # how many exist in all; only the latest 3 are returned
        }

    @staticmethod
    def _alert_view(r) -> dict:
        return {"vehicle_number": r.vehicle_number, "kind": r.kind, "title": r.title, "message": r.message,
                "due_date": _iso(r.due_date), "alert_date": _iso(r.alert_date), "created_at": _iso(r.created_at)}

    # =====================================================================
    # API 2 / 3 / 8: reads
    # =====================================================================
    def list(self, user: Optional[CurrentUser], filters: ListFilters, page: int, page_size: int) -> dict:
        user = self._manager(user, "list all maintenance schedules (Fleet Owner / Admin only)")
        if filters.status and filters.status not in STATUSES:
            raise MaintenanceError(400, f"status must be one of {', '.join(STATUSES)}")
        if filters.expected_date_from and filters.expected_date_to and filters.expected_date_from > filters.expected_date_to:
            raise MaintenanceError(400, "expected_date_from must be on or before expected_date_to")
        page = max(1, page)
        page_size = min(max(1, page_size), self._max_page)
        scope = self._scope(user)
        with self._repo.unit_of_work() as s:
            rows, total = s.search(scope, filters, self._today(), (page - 1) * page_size, page_size)
        drivers = self._drivers_for([r for r, _ in rows])
        return {
            "items": [self.view(r, status, drivers) for r, status in rows],
            "pagination": {"page": page, "page_size": page_size, "total": total,
                           "total_pages": (total + page_size - 1) // page_size},
        }

    def get(self, user: Optional[CurrentUser], vehicle_number: str, driver_id: Optional[int] = None) -> dict:
        """Fleet Owner / Admin: by login. Driver: enters their own driver_id (only their own vehicle)."""
        vehicle_number = vehicle_number.strip()
        if driver_id is not None:
            tenant = self._driver_tenant(driver_id, vehicle_number)
        else:
            user = self._manager(user, "view this schedule without a driver_id (Fleet Owner / Admin only)")
            with self._repo.unit_of_work() as s:
                tenant = self._tenant_for_vehicle(s, user, vehicle_number)
        with self._repo.unit_of_work() as s:
            record = self._load(s, tenant, vehicle_number)
        return self.view(record)

    # =====================================================================
    # API 5: postpone  (stores the new date separately; the expected date is kept)
    # =====================================================================
    def postpone(self, vehicle_number: str, body: PostponeRequest) -> dict:
        """Driver only: the driver enters their own driver_id, which must be the vehicle's driver."""
        if not self._driver_can_postpone:
            raise MaintenanceError(403, "Drivers are not permitted to postpone maintenance")
        vehicle_number = vehicle_number.strip()
        tenant = self._driver_tenant(body.driver_id, vehicle_number)
        new_date = body.postponed_date
        reason = self._reason(body.reason)
        today = self._today()
        if new_date < today:
            raise MaintenanceError(400, "postponed_date cannot be in the past")
        with self._repo.unit_of_work() as s:
            current = self._load(s, tenant, vehicle_number, for_update=True)
            expected = current.expected_vehicle_maintenance_date
            if effective_status(expected, current.postponed_date, current.status, today) == COMPLETED:
                raise MaintenanceError(409, "The current maintenance is already completed; there is nothing to postpone")
            if expected is not None and new_date <= expected:
                raise MaintenanceError(
                    400, f"postponed_date must be after the expected maintenance date ({expected.isoformat()})")
            if new_date == current.postponed_date:
                return self.view(current)                      # nothing changed, so no alert
            old_due = effective_due(expected, current.postponed_date)
            # The postponement is stored in the same row; the expected date itself is kept.
            updated = self._write(s, current, {
                "postponed_date": new_date,
                "postponed_reason": reason,
                "postponed_by": str(body.driver_id),
                "postponed_at": self._now(),
                "status": compute_status(new_date, today),
            })
        self._after_commit(updated, "postponed", old_due, self._driver_label(body.driver_id))
        return self.view(updated)

    # =====================================================================
    # API 6: complete
    # =====================================================================
    def complete(self, vehicle_number: str, body: CompleteRequest) -> dict:
        """Driver only (enters their own driver_id). previous = done_date; next expected = done_date + window."""
        vehicle_number = vehicle_number.strip()
        done = body.done_date
        today = self._today()
        if done > today:
            raise MaintenanceError(400, "done_date cannot be in the future")
        tenant = self._driver_tenant(body.driver_id, vehicle_number)
        with self._repo.unit_of_work() as s:
            # UPDLOCK serialises concurrent completions of the same vehicle.
            current = self._load(s, tenant, vehicle_number, for_update=True)
            prev = current.previous_vehicle_maintenance_date
            if current.done_date is not None and done == current.done_date:
                raise MaintenanceError(409, "This completion has already been recorded for this date")
            if prev is not None and done < prev:
                raise MaintenanceError(400, "done_date cannot be earlier than the previous maintenance date")
            window = current.maintenance_time_window
            if not window:
                raise MaintenanceError(400, "No maintenance interval is configured for this vehicle")
            new_previous = done                                           # previous date = the done date
            next_expected = calculate_expected_date(new_previous, window)  # done_date + window
            fields = {
                "previous_vehicle_maintenance_date": new_previous,
                "expected_vehicle_maintenance_date": next_expected,
                "done_date": done,
                "status": COMPLETED,       # stays 'completed' until the next cycle's reminders begin
                "postponed_date": None,    # a new cycle starts with no postponement
                "postponed_reason": None,
                "postponed_by": None,
                "postponed_at": None,
            }
            if body.reason is not None:
                fields["reason"] = self._reason(body.reason)
            updated = self._write(s, current, fields)
        self._after_commit(updated, "completed", effective_due(
            current.expected_vehicle_maintenance_date, current.postponed_date), self._driver_label(body.driver_id))
        result = self.view(updated)
        result["completed_cycle"] = {
            "done_date": done.isoformat(),
            "was_expected_on": _iso(current.expected_vehicle_maintenance_date),
            "was_postponed_to": _iso(current.postponed_date),
        }
        return result


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None