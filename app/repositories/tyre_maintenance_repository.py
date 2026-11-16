from datetime import datetime
from decimal import Decimal

from app.core.database import get_db_connection


# Tables used (columns confirmed from your database):
#   dbo.vehicles                 id, tenant_id, device_id, vehicle_number,
#                                tyre_life_limit_km
#   dbo.trips                    tenant_id, device_id, start_time, distance_km
#   dbo.vehicle_tyre_maintenance tenant_id, device_id, last_tyre_change_date,
#                                tyre_change_odometer_km, current_distance_km,
#                                last_limit_reminder_at, maintenance_status,
#                                created_at, updated_at
#   dbo.tyre_alerts              created by create_tyre_alerts_table.sql
#
# Current tyre distance = total trip distance - tyre_change_odometer_km
VEHICLES_TABLE = "dbo.vehicles"
TRIPS_TABLE = "dbo.trips"
MAINTENANCE_TABLE = "dbo.vehicle_tyre_maintenance"
ALERTS_TABLE = "dbo.tyre_alerts"


def _dec(value) -> Decimal:
    """Safely convert a DB value (None/float/Decimal) to Decimal."""
    return Decimal(str(value)) if value is not None else Decimal("0")


# ---------------------------------------------------------------- vehicles

def get_vehicle_by_number(tenant_id: int, vehicle_number: str):
    """Find a vehicle using tenant_id + vehicle_number."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP 2
                id, tenant_id, device_id, vehicle_number, tyre_life_limit_km
            FROM {VEHICLES_TABLE}
            WHERE tenant_id = ?
              AND vehicle_number = ?
            """,
            tenant_id,
            vehicle_number.strip(),
        )
        rows = cursor.fetchall()

        if not rows:
            return None
        if len(rows) > 1:
            raise ValueError("Duplicate vehicle number found for this tenant.")

        row = rows[0]
        return {
            "vehicle_id": row[0],
            "tenant_id": row[1],
            "device_id": row[2],
            "vehicle_number": row[3],
            "tyre_life_limit_km": _dec(row[4]),
        }
    finally:
        conn.close()


def get_vehicle_by_device(tenant_id: int, device_id: int):
    """Find a vehicle using tenant_id + device_id."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP 1
                id, tenant_id, device_id, vehicle_number, tyre_life_limit_km
            FROM {VEHICLES_TABLE}
            WHERE tenant_id = ?
              AND device_id = ?
            """,
            tenant_id,
            device_id,
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "vehicle_id": row[0],
            "tenant_id": row[1],
            "device_id": row[2],
            "vehicle_number": row[3],
            "tyre_life_limit_km": _dec(row[4]),
        }
    finally:
        conn.close()


# ------------------------------------------------------------------- trips

def get_total_trip_distance(device_id: int, tenant_id: int) -> Decimal:
    """Total distance travelled by the device across all trips."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(distance_km), 0)
            FROM {TRIPS_TABLE}
            WHERE tenant_id = ?
              AND device_id = ?
            """,
            tenant_id,
            device_id,
        )
        return _dec(cursor.fetchone()[0])
    finally:
        conn.close()


def get_historical_trip_distance(
    tenant_id: int,
    device_id: int,
    installation_date: datetime,
) -> Decimal:
    """Distance travelled before the tyres were installed."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(distance_km), 0)
            FROM {TRIPS_TABLE}
            WHERE tenant_id = ?
              AND device_id = ?
              AND start_time < ?
            """,
            tenant_id,
            device_id,
            installation_date,
        )
        return _dec(cursor.fetchone()[0])
    finally:
        conn.close()


# ------------------------------------------------------------- maintenance

def get_all_maintenance_keys(tenant_id: int | None = None):
    """
    Return [(tenant_id, device_id), ...] for all initialized vehicles.
    The scheduler calls it without arguments (all tenants); the API passes
    a tenant_id to get only that organization's vehicles.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if tenant_id is None:
            cursor.execute(
                f"SELECT tenant_id, device_id FROM {MAINTENANCE_TABLE}"
            )
        else:
            cursor.execute(
                f"""
                SELECT tenant_id, device_id
                FROM {MAINTENANCE_TABLE}
                WHERE tenant_id = ?
                """,
                tenant_id,
            )
        return [(row[0], row[1]) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_maintenance(tenant_id: int, device_id: int):
    """Get the tyre maintenance record, or None if not initialized."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP 1
                tyre_change_odometer_km,
                current_distance_km,
                maintenance_status,
                last_tyre_change_date,
                last_limit_reminder_at
            FROM {MAINTENANCE_TABLE}
            WHERE tenant_id = ?
              AND device_id = ?
            """,
            tenant_id,
            device_id,
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "tyre_change_odometer_km": _dec(row[0]),
            "current_distance_km": _dec(row[1]),
            "maintenance_status": row[2],
            "last_tyre_change_date": row[3],
            "last_limit_reminder_at": row[4],
        }
    finally:
        conn.close()


def update_maintenance_distance(
    tenant_id: int,
    device_id: int,
    current_distance: Decimal,
    maintenance_status: str,
):
    """Store the latest calculated distance and status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE {MAINTENANCE_TABLE}
            SET current_distance_km = ?,
                maintenance_status = ?,
                updated_at = SYSUTCDATETIME()
            WHERE tenant_id = ?
              AND device_id = ?
            """,
            current_distance,
            maintenance_status,
            tenant_id,
            device_id,
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------- register / replace tyres

def register_existing_tyre(
    tenant_id: int,
    device_id: int,
    installation_date: datetime,
    initial_status: str,
):
    """
    Create the maintenance record for tyres already fitted.
    Baseline (tyre_change_odometer_km) = trip distance before the
    installation date.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT 1 FROM {MAINTENANCE_TABLE}
            WHERE tenant_id = ? AND device_id = ?
            """,
            tenant_id,
            device_id,
        )
        if cursor.fetchone():
            raise ValueError(
                "Tyre maintenance is already registered for this vehicle."
            )

        cursor.execute(
            f"""
            INSERT INTO {MAINTENANCE_TABLE} (
                tenant_id, device_id, last_tyre_change_date,
                tyre_change_odometer_km, current_distance_km,
                maintenance_status, created_at, updated_at
            )
            SELECT
                ?, ?, ?,
                COALESCE(SUM(distance_km), 0), 0,
                ?, SYSUTCDATETIME(), SYSUTCDATETIME()
            FROM {TRIPS_TABLE}
            WHERE tenant_id = ?
              AND device_id = ?
              AND start_time < ?
            """,
            tenant_id,
            device_id,
            installation_date,
            initial_status,
            tenant_id,
            device_id,
            installation_date,
        )
        conn.commit()
    finally:
        conn.close()


def complete_tyre_change(
    tenant_id: int,
    device_id: int,
    total_distance: Decimal,
    replacement_date: datetime,
):
    """Reset the baseline after a tyre replacement."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE {MAINTENANCE_TABLE}
            SET tyre_change_odometer_km = ?,
                current_distance_km = 0,
                maintenance_status = 'NORMAL',
                last_tyre_change_date = ?,
                last_limit_reminder_at = NULL,
                updated_at = SYSUTCDATETIME()
            WHERE tenant_id = ?
              AND device_id = ?
            """,
            total_distance,
            replacement_date,
            tenant_id,
            device_id,
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ alerts
#
# Each alert is stored with cycle_start = the maintenance record's
# last_tyre_change_date at that moment. Alerts from an earlier tyre cycle
# never count for the current tyres, even if the replacement is back-dated.

_ALERT_COLUMNS = (
    "id", "tenant_id", "device_id", "vehicle_number", "alert_level",
    "maintenance_status", "usage_percentage", "current_distance_km",
    "limit_km", "message", "is_reminder", "created_at",
)


def get_last_alert_level(tenant_id: int, device_id: int) -> int:
    """Highest alert level already sent for the vehicle's CURRENT tyres."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT COALESCE(MAX(a.alert_level), 0)
            FROM {ALERTS_TABLE} a
            JOIN {MAINTENANCE_TABLE} m
              ON m.tenant_id = a.tenant_id
             AND m.device_id = a.device_id
            WHERE a.tenant_id = ?
              AND a.device_id = ?
              AND a.cycle_start = m.last_tyre_change_date
            """,
            tenant_id,
            device_id,
        )
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    finally:
        conn.close()


def get_last_alert_time(tenant_id: int, device_id: int, alert_level: int):
    """Time (naive UTC) of the newest alert at this level, or None."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT MAX(a.created_at)
            FROM {ALERTS_TABLE} a
            JOIN {MAINTENANCE_TABLE} m
              ON m.tenant_id = a.tenant_id
             AND m.device_id = a.device_id
            WHERE a.tenant_id = ?
              AND a.device_id = ?
              AND a.alert_level = ?
              AND a.cycle_start = m.last_tyre_change_date
            """,
            tenant_id,
            device_id,
            alert_level,
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def record_alert(
    tenant_id: int,
    device_id: int,
    vehicle_number: str,
    alert_level: int,
    maintenance_status: str,
    usage_percentage: Decimal,
    current_distance_km: Decimal,
    limit_km: Decimal,
    message: str,
    is_reminder: bool = False,
):
    """Insert the alert and stamp last_limit_reminder_at, in one transaction."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {ALERTS_TABLE} (
                tenant_id, device_id, vehicle_number, alert_level,
                maintenance_status, usage_percentage, current_distance_km,
                limit_km, message, is_reminder, cycle_start
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, m.last_tyre_change_date
            FROM {MAINTENANCE_TABLE} m
            WHERE m.tenant_id = ? AND m.device_id = ?
            """,
            tenant_id,
            device_id,
            vehicle_number,
            alert_level,
            maintenance_status,
            usage_percentage,
            current_distance_km,
            limit_km,
            message,
            1 if is_reminder else 0,
            tenant_id,
            device_id,
        )
        cursor.execute(
            f"""
            UPDATE {MAINTENANCE_TABLE}
            SET last_limit_reminder_at = SYSUTCDATETIME(),
                updated_at = SYSUTCDATETIME()
            WHERE tenant_id = ? AND device_id = ?
            """,
            tenant_id,
            device_id,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_alerts(
    tenant_id: int,
    limit: int = 50,
    vehicle_number: str | None = None,
):
    """
    Newest alerts first for one tenant (organization).
    If vehicle_number is given, only that vehicle's alerts are returned.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = f"""
            SELECT TOP (?) {", ".join(_ALERT_COLUMNS)}
            FROM {ALERTS_TABLE}
            WHERE tenant_id = ?
        """
        params = [limit, tenant_id]
        if vehicle_number and vehicle_number.strip():
            sql += " AND vehicle_number = ?"
            params.append(vehicle_number.strip())
        sql += " ORDER BY id DESC"
        cursor.execute(sql, *params)
        return [dict(zip(_ALERT_COLUMNS, row)) for row in cursor.fetchall()]
    finally:
        conn.close()