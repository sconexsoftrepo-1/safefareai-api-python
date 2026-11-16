"""Bridge to YOUR existing driver-assignment and user data (read-only).

>>> WIRE-UP POINT 2 <<<
The three SQL statements below are the only guesses about tables outside
``vehicle_maintenance`` / ``vehicles``. Replace them with your real
relationships (or replace this class with calls into your existing services).
They are SELECT-only; nothing here creates or alters tables.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from app.core.vm_database import Database

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recipient:
    user_id: Any
    role: str  # "fleet_owner" | "driver"
    email: Optional[str] = None
    phone: Optional[str] = None
    device_token: Optional[str] = None


class MaintenanceDirectory(Protocol):
    def driver_vehicle_numbers(self, tenant_id, driver_user_id) -> set[str]: ...
    def fleet_owner_recipients(self, tenant_id) -> list[Recipient]: ...
    def driver_recipients(self, tenant_id, vehicle_number: str) -> list[Recipient]: ...
    def vehicle_drivers(self, tenant_id, vehicle_numbers: list) -> dict: ...
    def tenants_of_driver_vehicle(self, driver_id, vehicle_number: str) -> list: ...


# The driver of a vehicle is vehicles.driver_id (a users.id). All of these are read-only SELECTs.
DRIVER_VEHICLES_SQL = (
    "SELECT vehicle_number FROM [{schema}].[{vehicles}] WHERE tenant_id = ? AND driver_id = ?"
)
# Fleet owners of a tenant = the users other users report to (users.parent_user_id). Columns: user_id, email, phone.
FLEET_OWNERS_SQL = (
    "SELECT o.id, o.email, o.phone FROM [{schema}].[users] o "
    "WHERE o.tenant_id = ? AND o.status = 'ACTIVE' "
    "AND EXISTS (SELECT 1 FROM [{schema}].[users] d WHERE d.parent_user_id = o.id)"
)
# The driver assigned to a vehicle (vehicles.driver_id -> users.id). Columns: user_id, email, phone.
VEHICLE_DRIVERS_SQL = (
    "SELECT u.id, u.email, u.phone FROM [{schema}].[{vehicles}] v "
    "JOIN [{schema}].[users] u ON u.id = v.driver_id AND u.tenant_id = v.tenant_id "
    "WHERE v.tenant_id = ? AND LTRIM(RTRIM(v.vehicle_number)) = ? AND u.status = 'ACTIVE'"
)
# vehicle -> driver id + driver NAME, taken from users.display_name (the name is never stored anywhere else).
# {marks} is replaced by one ? per vehicle number.
VEHICLE_DRIVER_NAMES_SQL = (
    "SELECT LTRIM(RTRIM(v.vehicle_number)), v.driver_id, u.display_name FROM [{schema}].[{vehicles}] v "
    "LEFT JOIN [{schema}].[users] u ON u.id = v.driver_id AND u.tenant_id = v.tenant_id "
    "WHERE v.tenant_id = ? AND LTRIM(RTRIM(v.vehicle_number)) IN ({marks})"
)
# Which tenant(s) does this vehicle belong to, for this driver id? Used to check a driver's own id.
DRIVER_VEHICLE_TENANTS_SQL = (
    "SELECT DISTINCT v.tenant_id FROM [{schema}].[{vehicles}] v "
    "WHERE v.driver_id = ? AND LTRIM(RTRIM(v.vehicle_number)) = ?"
)


class SqlMaintenanceDirectory:
    def __init__(self, db: Database, schema: str = "dbo", vehicles_table: str = "vehicles"):
        self._db = db
        self._fmt = {"schema": schema, "vehicles": vehicles_table}

    def _query(self, sql: str, *params, **fmt) -> list:
        with self._db.transaction() as conn:
            cur = conn.cursor()
            cur.execute(sql.format(**self._fmt, **fmt), *params)
            return cur.fetchall()

    def driver_vehicle_numbers(self, tenant_id, driver_user_id) -> set[str]:
        rows = self._query(DRIVER_VEHICLES_SQL, tenant_id, driver_user_id)
        return {str(r[0]).strip() for r in rows if r[0] is not None}

    def fleet_owner_recipients(self, tenant_id) -> list[Recipient]:
        return [Recipient(r[0], "fleet_owner", r[1], r[2]) for r in self._query(FLEET_OWNERS_SQL, tenant_id)]

    def driver_recipients(self, tenant_id, vehicle_number) -> list[Recipient]:
        rows = self._query(VEHICLE_DRIVERS_SQL, tenant_id, vehicle_number)
        return [Recipient(r[0], "driver", r[1], r[2]) for r in rows]

    def vehicle_drivers(self, tenant_id, vehicle_numbers) -> dict:
        """{vehicle_number: {"driver_id": ..., "driver_name": ...}} (name from users.display_name)."""
        numbers = sorted({str(v).strip() for v in vehicle_numbers})
        if not numbers:
            return {}
        rows = self._query(VEHICLE_DRIVER_NAMES_SQL, tenant_id, *numbers, marks=", ".join("?" for _ in numbers))
        return {str(r[0]).strip(): {"driver_id": r[1], "driver_name": r[2]} for r in rows}

    def tenants_of_driver_vehicle(self, driver_id, vehicle_number) -> list:
        return [r[0] for r in self._query(DRIVER_VEHICLE_TENANTS_SQL, driver_id, vehicle_number)]