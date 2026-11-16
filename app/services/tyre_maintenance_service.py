import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.tyre_maintenance import calculate_maintenance_status
from app.repositories import tyre_maintenance_repository as repo

logger = logging.getLogger(__name__)

# Maintenance status -> alert level (stored in tyre_maintenance.last_alert_level)
ALERT_LEVELS = {
    "NORMAL": 0,
    "DUE_SOON": 1,      # 75%
    "CRITICAL_85": 2,   # 85%
    "CRITICAL_95": 3,   # 95%
    "OVERDUE": 4,       # 100%
}
OVERDUE_LEVEL = ALERT_LEVELS["OVERDUE"]


def _overdue_reminder_interval() -> timedelta:
    try:
        hours = float(os.getenv("TYRE_OVERDUE_REMINDER_INTERVAL_HOURS", "24"))
    except ValueError:
        hours = 24.0
    return timedelta(hours=hours)


def _to_sql_datetime(value: datetime) -> datetime:
    """Convert timezone-aware datetime to naive UTC for SQL Server DATETIME2."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _get_vehicle_or_raise(tenant_id: int, vehicle_number: str):
    """Find vehicle using tenant ID and vehicle number."""

    if not vehicle_number or not vehicle_number.strip():
        raise ValueError("Vehicle number is required.")

    vehicle = repo.get_vehicle_by_number(
        tenant_id=tenant_id,
        vehicle_number=vehicle_number.strip(),
    )

    if not vehicle:
        raise ValueError(
            f"Vehicle {vehicle_number} not found for this tenant."
        )

    if vehicle["device_id"] is None:
        raise ValueError(
            f"No device is assigned to vehicle {vehicle_number}."
        )

    return vehicle


def get_tyre_maintenance(tenant_id: int, device_id: int):
    """
    Calculate current tyre usage.

    Current tyre distance =
        Total trip distance - Tyre installation baseline
    """

    vehicle = repo.get_vehicle_by_device(tenant_id, device_id)

    if not vehicle:
        raise ValueError("Vehicle not found for this tenant and device.")

    tyre_limit = vehicle["tyre_life_limit_km"]

    if tyre_limit is None or tyre_limit <= 0:
        raise ValueError("Tyre life limit is not configured.")

    maintenance = repo.get_maintenance(tenant_id, device_id)

    if not maintenance:
        raise ValueError(
            "Tyre maintenance record is not initialized. "
            "Please register the current tyre installation date first."
        )

    total_trip_distance = repo.get_total_trip_distance(
        device_id=device_id,
        tenant_id=tenant_id,
    )

    baseline = maintenance["tyre_change_odometer_km"]

    current_distance = max(
        Decimal("0"),
        total_trip_distance - baseline,
    )

    usage_percentage = (
        current_distance / tyre_limit
    ) * Decimal("100")

    remaining_km = max(
        Decimal("0"),
        tyre_limit - current_distance,
    )

    maintenance_status = calculate_maintenance_status(
        current_distance,
        tyre_limit,
    )

    repo.update_maintenance_distance(
        tenant_id,
        device_id,
        current_distance,
        maintenance_status,
    )

    return {
        "tenant_id": tenant_id,
        "device_id": device_id,
        "vehicle_number": vehicle["vehicle_number"],
        "tyre_life_limit_km": tyre_limit,
        "tyre_change_odometer_km": baseline,
        "current_distance_km": current_distance,
        "usage_percentage": usage_percentage.quantize(
            Decimal("0.01")
        ),
        "remaining_km": remaining_km,
        "maintenance_status": maintenance_status,
        "last_tyre_change_date": maintenance["last_tyre_change_date"],
        "last_limit_reminder_at": maintenance["last_limit_reminder_at"],
    }


def get_tyre_maintenance_by_vehicle(
    tenant_id: int,
    vehicle_number: str,
):
    """Get tyre maintenance using vehicle number."""

    vehicle = _get_vehicle_or_raise(
        tenant_id,
        vehicle_number,
    )

    return get_tyre_maintenance(
        tenant_id=tenant_id,
        device_id=vehicle["device_id"],
    )


def register_existing_tyre(
    tenant_id: int,
    device_id: int,
    installation_date: datetime,
):
    """
    Register tyres already installed on a vehicle.

    Historical baseline:
        SUM(distance_km where start_time < installation_date)

    Current tyre distance:
        Total trip distance - historical baseline
    """

    if installation_date is None:
        raise ValueError("Tyre installation date is required.")

    installation_date = _to_sql_datetime(installation_date)

    if installation_date > datetime.now(timezone.utc).replace(tzinfo=None):
        raise ValueError(
            "Tyre installation date cannot be in the future."
        )

    vehicle = repo.get_vehicle_by_device(
        tenant_id,
        device_id,
    )

    if not vehicle:
        raise ValueError(
            "Vehicle not found for this tenant and device."
        )

    tyre_limit = vehicle["tyre_life_limit_km"]

    if tyre_limit is None or tyre_limit <= 0:
        raise ValueError(
            "Configure a valid tyre_life_limit_km in dbo.vehicles first."
        )

    total_distance = repo.get_total_trip_distance(
        device_id=device_id,
        tenant_id=tenant_id,
    )

    historical_baseline = repo.get_historical_trip_distance(
        tenant_id=tenant_id,
        device_id=device_id,
        installation_date=installation_date,
    )

    current_distance = total_distance - historical_baseline

    if current_distance < 0:
        raise ValueError(
            "Calculated tyre distance cannot be negative."
        )

    initial_status = calculate_maintenance_status(
        current_distance,
        tyre_limit,
    )

    repo.register_existing_tyre(
        tenant_id=tenant_id,
        device_id=device_id,
        installation_date=installation_date,
        initial_status=initial_status,
    )

    return get_tyre_maintenance(
        tenant_id,
        device_id,
    )


def register_existing_tyre_by_vehicle(
    tenant_id: int,
    vehicle_number: str,
    installation_date: datetime,
):
    """Register existing tyres using vehicle number."""

    vehicle = _get_vehicle_or_raise(
        tenant_id,
        vehicle_number,
    )

    return register_existing_tyre(
        tenant_id=tenant_id,
        device_id=vehicle["device_id"],
        installation_date=installation_date,
    )


def complete_tyre_replacement(
    tenant_id: int,
    device_id: int,
    replacement_date: datetime | None = None,
):
    """
    Record completed tyre replacement.

    Backend calculates the new baseline from trip history.
    """

    vehicle = repo.get_vehicle_by_device(
        tenant_id,
        device_id,
    )

    if not vehicle:
        raise ValueError(
            "Vehicle not found for this tenant and device."
        )

    maintenance = repo.get_maintenance(
        tenant_id,
        device_id,
    )

    if not maintenance:
        raise ValueError(
            "Tyre maintenance record is not initialized."
        )

    total_distance = repo.get_total_trip_distance(
        device_id=device_id,
        tenant_id=tenant_id,
    )

    if replacement_date is None:
        replacement_date = datetime.now(timezone.utc)

    sql_replacement_date = _to_sql_datetime(
        replacement_date
    )

    repo.complete_tyre_change(
        tenant_id=tenant_id,
        device_id=device_id,
        total_distance=total_distance,
        replacement_date=sql_replacement_date,
    )

    return {
        "message": "Tyre replacement recorded successfully.",
        "tenant_id": tenant_id,
        "device_id": device_id,
        "vehicle_number": vehicle["vehicle_number"],
        "new_tyre_change_odometer_km": total_distance,
        "current_distance_km": Decimal("0"),
        "maintenance_status": "NORMAL",
        "last_tyre_change_date": sql_replacement_date,
    }


def complete_tyre_replacement_by_vehicle(
    tenant_id: int,
    vehicle_number: str,
    replacement_date: datetime | None = None,
):
    """Complete tyre replacement using vehicle number."""

    vehicle = _get_vehicle_or_raise(
        tenant_id,
        vehicle_number,
    )

    return complete_tyre_replacement(
        tenant_id=tenant_id,
        device_id=vehicle["device_id"],
        replacement_date=replacement_date,
    )


def check_and_create_alert(result: dict):
    """
    Create an alert when a vehicle reaches 75 / 85 / 95 / 100 % of its tyre
    life. Each level fires once (tracked in tyre_maintenance.last_alert_level).
    After 100 % a reminder is created every
    TYRE_OVERDUE_REMINDER_INTERVAL_HOURS hours.

    `result` is the dict returned by get_tyre_maintenance().
    Returns the alert message that was created, or None.
    """

    tenant_id = result["tenant_id"]
    device_id = result["device_id"]
    status = result["maintenance_status"]
    level = ALERT_LEVELS.get(status, 0)

    if level == 0:
        return None

    last_level = repo.get_last_alert_level(tenant_id, device_id)
    is_reminder = False

    if level > last_level:
        pass  # new threshold crossed
    elif level == OVERDUE_LEVEL and last_level == OVERDUE_LEVEL:
        last_time = repo.get_last_alert_time(tenant_id, device_id, OVERDUE_LEVEL)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if last_time is not None and now - last_time < _overdue_reminder_interval():
            return None
        is_reminder = True
    else:
        return None

    vehicle_number = result["vehicle_number"]
    usage = result["usage_percentage"]
    distance = result["current_distance_km"]
    limit_km = result["tyre_life_limit_km"]

    if level == OVERDUE_LEVEL:
        message = (
            f"{'Reminder: ' if is_reminder else ''}Tyre life limit reached for "
            f"vehicle {vehicle_number}. Used {distance:.0f} km of "
            f"{limit_km:.0f} km ({usage}%). Replace the tyres now."
        )
    else:
        message = (
            f"Vehicle {vehicle_number} has used {usage}% of its tyre life "
            f"({distance:.0f} of {limit_km:.0f} km). Status: {status}."
        )

    repo.record_alert(
        tenant_id=tenant_id,
        device_id=device_id,
        vehicle_number=vehicle_number,
        alert_level=level,
        maintenance_status=status,
        usage_percentage=usage,
        current_distance_km=distance,
        limit_km=limit_km,
        message=message,
        is_reminder=is_reminder,
    )

    logger.warning("TYRE ALERT | %s", message)
    return message


def get_alerts(
    tenant_id: int,
    limit: int = 50,
    vehicle_number: str | None = None,
):
    return repo.get_alerts(tenant_id, limit, vehicle_number)