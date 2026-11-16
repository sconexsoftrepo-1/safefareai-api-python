"""Data access for the single schedule table ``vehicle_maintenance_postponements``.

One row per vehicle holds the whole schedule: previous date, window, expected date, done date, status, reason and,
in the same row, the postponement (postponed_date, postponed_reason, postponed_by, postponed_at). The postponed
columns are NULL until the driver postpones and are cleared again when the maintenance is completed.
The old ``vehicle_maintenance`` table is not used.

* The table is set up once with ``migrations/001_create_schedule_table.sql`` (run by you in SSMS).
* Only SELECT / INSERT / UPDATE; a read-only SELECT on the vehicles table. The application never changes the database structure.
* Every value is a ``?`` parameter. The only interpolated names are the schema and vehicles-table identifiers
  (validated in config) and column names from the fixed whitelist below.
* Row identity: (tenant_id, vehicle_number, device_id); updates verify exactly one row changed and roll back otherwise.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterator, Optional, Protocol, Sequence

from app.core.vm_database import Database
from app.utils.date_calculations import REOPEN_DAYS_BEFORE, to_date

TABLE = "vehicle_maintenance_postponements"

COLUMNS = (
    "tenant_id",
    "vehicle_number",
    "device_id",
    "previous_vehicle_maintenance_date",
    "maintenance_time_window",
    "expected_vehicle_maintenance_date",
    "done_date",
    "status",
    "reason",
    "created_at",
    "updated_at",
    "postponed_date",     # NULL until the driver postpones
    "postponed_reason",
    "postponed_by",
    "postponed_at",
)
ROW_COLUMNS = COLUMNS
UPDATABLE_COLUMNS = frozenset(set(COLUMNS) - {"tenant_id", "vehicle_number", "device_id", "created_at"})


@dataclass
class MaintenanceRecord:
    tenant_id: Any
    vehicle_number: str
    device_id: Any
    previous_vehicle_maintenance_date: Optional[date]
    maintenance_time_window: Optional[int]
    expected_vehicle_maintenance_date: Optional[date]
    done_date: Optional[date] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    postponed_date: Optional[date] = None
    postponed_by: Optional[str] = None
    postponed_at: Optional[datetime] = None
    postponed_reason: Optional[str] = None

    @classmethod
    def from_row(cls, row: Sequence[Any]) -> "MaintenanceRecord":
        values = dict(zip(ROW_COLUMNS, row))
        for key in ("previous_vehicle_maintenance_date", "expected_vehicle_maintenance_date", "done_date",
                    "postponed_date"):
            values[key] = to_date(values[key])
        if values["maintenance_time_window"] is not None:
            values["maintenance_time_window"] = int(values["maintenance_time_window"])
        if values.get("postponed_by") is not None:
            values["postponed_by"] = str(values["postponed_by"])
        if isinstance(values["vehicle_number"], str):
            values["vehicle_number"] = values["vehicle_number"].strip()
        return cls(**values)

    def key(self) -> tuple:
        return (self.tenant_id, self.vehicle_number, self.device_id)


@dataclass
class AccessScope:
    """Which rows a caller may see. tenant_ids=None means every tenant (unrestricted admin).
    vehicle_numbers=None means no vehicle restriction (fleet owner / admin)."""
    tenant_ids: Optional[list] = None
    vehicle_numbers: Optional[list] = None


@dataclass
class ListFilters:
    vehicle_number: Optional[str] = None
    device_id: Optional[int] = None
    status: Optional[str] = None
    expected_date_from: Optional[date] = None
    expected_date_to: Optional[date] = None


class MaintenanceSession(Protocol):
    def devices_for_vehicle(self, tenant_id, vehicle_number: str) -> list: ...
    def find(self, tenant_id, vehicle_number: str, device_id=None, for_update: bool = False) -> list[MaintenanceRecord]: ...
    def insert(self, record: MaintenanceRecord) -> None: ...
    def update(self, tenant_id, vehicle_number: str, device_id, fields: dict) -> int: ...
    def search(self, scope: AccessScope, filters: ListFilters, today: date, offset: int, limit: int) -> tuple[list[tuple[MaintenanceRecord, str]], int]: ...
    def all_schedules(self) -> list[MaintenanceRecord]: ...
    def tenants_for_vehicle(self, vehicle_number: str, tenant_ids: Optional[list]) -> list: ...


class MaintenanceRepository(Protocol):
    def unit_of_work(self) -> Iterator[MaintenanceSession]: ...


# ---------------------------------------------------------------------------
# SQL Server implementation
# ---------------------------------------------------------------------------

# Everything is measured against the postponed date when there is one (see date_calculations.effective_status).
_DUE_SQL = "COALESCE(vm.postponed_date, vm.expected_vehicle_maintenance_date)"
_EFFECTIVE_STATUS_SQL = (
    "CASE WHEN LOWER(LTRIM(RTRIM(ISNULL(vm.status, '')))) = 'completed' "
    f"AND ({_DUE_SQL} IS NULL OR p.today < DATEADD(day, -{int(REOPEN_DAYS_BEFORE)}, {_DUE_SQL})) THEN 'completed' "
    f"WHEN {_DUE_SQL} < p.today THEN 'overdue' "
    "ELSE 'pending' END"
)


def _in_clause(column: str, values: list, params: list) -> str:
    params.extend(values)
    return f"{column} IN ({', '.join('?' for _ in values)})"


class SqlServerMaintenanceSession:
    def __init__(self, conn, schema: str, vehicles_table: str):
        self._conn = conn
        self._table = f"[{schema}].[{TABLE}]"
        self._vehicles = f"[{schema}].[{vehicles_table}]"
        self._cols = ", ".join(f"vm.{c}" for c in COLUMNS)

    def _cursor(self):
        return self._conn.cursor()

    # -- reads ------------------------------------------------------------
    def devices_for_vehicle(self, tenant_id, vehicle_number) -> list:
        """device_id values registered for this vehicle in this tenant ([] = vehicle not found).
        A vehicle normally has one device; the service rejects more than one as ambiguous."""
        sql = (
            f"SELECT DISTINCT device_id FROM {self._vehicles} "
            "WHERE tenant_id = ? AND LTRIM(RTRIM(vehicle_number)) = ?"
        )
        cur = self._cursor()
        cur.execute(sql, tenant_id, vehicle_number)
        return [r[0] for r in cur.fetchall()]

    def find(self, tenant_id, vehicle_number, device_id=None, for_update=False):
        hint = " WITH (UPDLOCK, HOLDLOCK)" if for_update else ""
        sql = f"SELECT {self._cols} FROM {self._table} AS vm{hint} WHERE vm.tenant_id = ? AND vm.vehicle_number = ?"
        params: list = [tenant_id, vehicle_number]
        if device_id is not None:
            sql += " AND vm.device_id = ?"
            params.append(device_id)
        cur = self._cursor()
        cur.execute(sql, *params)
        return [MaintenanceRecord.from_row(r) for r in cur.fetchall()]

    def _scope_where(self, scope: AccessScope, params: list) -> list[str]:
        where: list[str] = []
        if scope.tenant_ids is not None:
            where.append(_in_clause("vm.tenant_id", list(scope.tenant_ids), params) if scope.tenant_ids else "1 = 0")
        if scope.vehicle_numbers is not None:
            where.append(_in_clause("vm.vehicle_number", list(scope.vehicle_numbers), params) if scope.vehicle_numbers else "1 = 0")
        return where

    def search(self, scope, filters, today, offset, limit):
        params: list = [today]
        where = self._scope_where(scope, params)
        if filters.vehicle_number:
            where.append("vm.vehicle_number = ?")
            params.append(filters.vehicle_number)
        if filters.device_id is not None:
            where.append("vm.device_id = ?")
            params.append(filters.device_id)
        if filters.expected_date_from:
            where.append(f"{_DUE_SQL} >= ?")
            params.append(filters.expected_date_from)
        if filters.expected_date_to:
            where.append(f"{_DUE_SQL} <= ?")
            params.append(filters.expected_date_to)
        inner_where = (" WHERE " + " AND ".join(where)) if where else ""
        base = (
            f"SELECT {self._cols}, {_EFFECTIVE_STATUS_SQL} AS effective_status "
            f"FROM {self._table} AS vm CROSS JOIN (SELECT CAST(? AS DATE) AS today) AS p{inner_where}"
        )
        outer_params = list(params)
        status_where = ""
        if filters.status:
            status_where = " WHERE x.effective_status = ?"
            outer_params.append(filters.status)

        cur = self._cursor()
        cur.execute(f"SELECT COUNT(*) FROM ({base}) AS x{status_where}", *outer_params)
        total = int(cur.fetchone()[0])

        page_sql = (
            f"SELECT x.* FROM ({base}) AS x{status_where} "
            "ORDER BY COALESCE(x.postponed_date, x.expected_vehicle_maintenance_date) ASC, "
            "x.vehicle_number ASC, x.device_id ASC "
            "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        )
        cur.execute(page_sql, *outer_params, offset, limit)
        rows = [(MaintenanceRecord.from_row(r[: len(ROW_COLUMNS)]), r[len(ROW_COLUMNS)]) for r in cur.fetchall()]
        return rows, total

    def tenants_for_vehicle(self, vehicle_number, tenant_ids):
        """Admin lookup: which tenants have a schedule for this vehicle number."""
        params: list = [vehicle_number]
        sql = f"SELECT DISTINCT vm.tenant_id FROM {self._table} AS vm WHERE vm.vehicle_number = ?"
        if tenant_ids is not None:
            sql += " AND " + (_in_clause("vm.tenant_id", list(tenant_ids), params) if tenant_ids else "1 = 0")
        cur = self._cursor()
        cur.execute(sql, *params)
        return [r[0] for r in cur.fetchall()]

    def all_schedules(self):
        cur = self._cursor()
        cur.execute(f"SELECT {self._cols} FROM {self._table} AS vm")
        return [MaintenanceRecord.from_row(r) for r in cur.fetchall()]

    # -- writes -----------------------------------------------------------
    def insert(self, record: MaintenanceRecord) -> None:
        placeholders = ", ".join("?" for _ in COLUMNS)
        sql = f"INSERT INTO {self._table} ({', '.join(COLUMNS)}) VALUES ({placeholders})"
        cur = self._cursor()
        cur.execute(sql, *[getattr(record, c) for c in COLUMNS])

    def update(self, tenant_id, vehicle_number, device_id, fields: dict) -> int:
        unknown = set(fields) - UPDATABLE_COLUMNS
        if unknown or not fields:
            raise ValueError(f"Invalid update columns: {sorted(unknown)}")
        names = sorted(fields)
        set_sql = ", ".join(f"{n} = ?" for n in names)
        sql = f"UPDATE {self._table} SET {set_sql} WHERE tenant_id = ? AND vehicle_number = ? AND device_id = ?"
        cur = self._cursor()
        cur.execute(sql, *[fields[n] for n in names], tenant_id, vehicle_number, device_id)
        return cur.rowcount


class SqlServerMaintenanceRepository:
    def __init__(self, db: Database, schema: str = "dbo", vehicles_table: str = "vehicles"):
        self._db = db
        self._schema = schema
        self._vehicles_table = vehicles_table

    @contextmanager
    def unit_of_work(self) -> Iterator[SqlServerMaintenanceSession]:
        with self._db.transaction() as conn:
            yield SqlServerMaintenanceSession(conn, self._schema, self._vehicles_table)