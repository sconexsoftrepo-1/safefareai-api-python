"""FastAPI routes for vehicle maintenance.

All responses use {"success", "message", "data"}. Error formatting is scoped to
this router (custom route class), so existing APIs are not affected.
"""
from __future__ import annotations

import inspect
import logging
from datetime import date
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.integration.auth_adapter import CurrentUser, Role, get_current_user
from app.repositories.vehicle_maintenance_repository import ListFilters
from app.schemas.vehicle_maintenance import (
    CompleteRequest,
    CreateMaintenanceRequest,
    PostponeRequest,
    _strict_date,
)
from app.services.errors import MaintenanceError
from app.services.vehicle_maintenance_service import VehicleMaintenanceService

log = logging.getLogger(__name__)


def envelope(success: bool, message: str, data: Any = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": success, "message": message, "data": data})


def _validation_details(exc: RequestValidationError) -> list:
    out = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p != "body"]
        msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        if err.get("type") == "extra_forbidden":
            msg = "Field is not allowed"
        out.append({"field": ".".join(loc), "message": msg})
    return out


class MaintenanceRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as exc:
                return envelope(False, "Invalid request", {"errors": _validation_details(exc)}, 400)
            except MaintenanceError as exc:
                return envelope(False, exc.message, exc.data, exc.status_code)
            except HTTPException as exc:  # e.g. raised by your existing auth dependency
                return envelope(False, str(exc.detail), None, exc.status_code)
            except Exception:
                log.exception("Unhandled error in vehicle maintenance API")
                return envelope(False, "Internal server error", None, 500)

        return handler


router = APIRouter(prefix="/api/vehicle-maintenance", tags=["Vehicle Maintenance"], route_class=MaintenanceRoute)


def get_vehicle_maintenance_service(request: Request) -> VehicleMaintenanceService:
    service = getattr(request.app.state, "vehicle_maintenance_service", None)
    if service is None:
        raise MaintenanceError(500, "Vehicle maintenance module is not initialised")
    return service


def _opt_date(value: Optional[str], name: str) -> Optional[date]:
    if value in (None, ""):
        return None
    try:
        return _strict_date(value)
    except ValueError as exc:
        raise MaintenanceError(400, f"{name}: {exc}")


def optional_user(request: Request) -> Optional[CurrentUser]:
    """The logged-in Fleet Owner / Admin if there is one; drivers do not log in, they type their driver_id."""
    fn = request.app.dependency_overrides.get(get_current_user, get_current_user)
    try:
        return fn(request) if inspect.signature(fn).parameters else fn()
    except (MaintenanceError, HTTPException):
        return None


Service = Depends(get_vehicle_maintenance_service)
User = Depends(get_current_user)
MaybeUser = Depends(optional_user)


@router.post("", status_code=201)
def create_schedule(body: CreateMaintenanceRequest, user: CurrentUser = User,
                    svc: VehicleMaintenanceService = Service):
    """Fleet Owner only. tenant_id is taken from the logged-in user."""
    data = svc.create(user, body)
    return envelope(True, "Maintenance schedule created successfully", data, 201)


@router.post("/run-reminders")
def run_reminders(request: Request, user: CurrentUser = User):
    """Fleet Owner / Admin: run the daily reminder job NOW (the same job that runs every day at VM_SCHEDULER_RUN_AT).

    Every due alert is saved in vehicle_maintenance_alerts for the vehicle's driver. Running it again the same day
    does not create duplicates. The response says how many schedules were checked and which alerts were sent."""
    if user.role not in (Role.ADMIN, Role.FLEET_OWNER):
        raise MaintenanceError(403, "Only a Fleet Owner or Admin can run the reminders")
    scheduler = getattr(request.app.state, "vehicle_maintenance_scheduler", None)
    if scheduler is None:
        raise MaintenanceError(500, "Vehicle maintenance module is not initialised")
    summary = scheduler.run_once()
    data = {
        "ran": summary.ran,
        "run_date": summary.run_date.isoformat() if summary.run_date else None,
        "schedules_checked": summary.scanned,
        "status_updates": summary.status_updates,
        "alerts_sent": summary.notifications,      # e.g. {"overdue": 1, "due_today": 1}
        "errors": summary.errors,
    }
    if not summary.ran:
        message = "A run is already in progress; try again in a moment"
    elif not summary.scanned:
        message = "No maintenance schedules found (dbo.vehicle_maintenance_postponements is empty)"
    elif not summary.notifications:
        message = ("Schedules checked, but no new alert was sent. Either nothing is due today, the alert was "
                   "already sent today, or the vehicle has no active driver (vehicles.driver_id). See the server log.")
    else:
        message = "Reminders generated and saved to vehicle_maintenance_alerts"
    return envelope(True, message, data)


@router.get("/alerts")
def list_alerts(
    vehicle_number: str = Query(..., min_length=1, description="The vehicle number"),
    user: Optional[CurrentUser] = MaybeUser,
    svc: VehicleMaintenanceService = Service,
):
    """Fleet Owner and Driver alike: send the vehicle_number and get that vehicle's LATEST 3 alerts."""
    return envelope(True, "Alerts retrieved successfully", svc.list_alerts(user, vehicle_number))


@router.get("")
def list_schedules(
    vehicle_number: Optional[str] = None,
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    expected_date_from: Optional[str] = None,
    expected_date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    user: Optional[CurrentUser] = MaybeUser,
    svc: VehicleMaintenanceService = Service,
):
    """Fleet Owner / Admin only (drivers cannot list all schedules)."""
    filters = ListFilters(
        vehicle_number=vehicle_number.strip() if vehicle_number else None,
        device_id=device_id,
        status=status.strip().lower() if status else None,
        expected_date_from=_opt_date(expected_date_from, "expected_date_from"),
        expected_date_to=_opt_date(expected_date_to, "expected_date_to"),
    )
    data = svc.list(user, filters, page, page_size)
    return envelope(True, "Maintenance schedules retrieved successfully", data)


@router.get("/{vehicle_number}")
def get_schedule(vehicle_number: str,
                 driver_id: Optional[int] = Query(None, gt=0, description="Driver: your own driver id"),
                 user: Optional[CurrentUser] = MaybeUser, svc: VehicleMaintenanceService = Service):
    """Fleet Owner / Admin: any vehicle in their scope. Driver: send your driver_id to see your own vehicle."""
    data = svc.get(user, vehicle_number, driver_id)
    return envelope(True, "Maintenance schedule retrieved successfully", data)


@router.patch("/{vehicle_number}/postpone")
def postpone(vehicle_number: str, body: PostponeRequest, svc: VehicleMaintenanceService = Service):
    """Driver only. Body: driver_id (your own id), postponed_date, reason (required). The expected date is kept."""
    data = svc.postpone(vehicle_number, body)
    return envelope(True, "Maintenance postponed successfully", data)


@router.post("/{vehicle_number}/complete")
def complete(vehicle_number: str, body: CompleteRequest, svc: VehicleMaintenanceService = Service):
    """Driver only. Body: driver_id (your own id), done_date (+ optional reason).
    previous = done_date, next expected = done_date + window."""
    data = svc.complete(vehicle_number, body)
    return envelope(True, "Maintenance completed; next maintenance cycle scheduled", data)