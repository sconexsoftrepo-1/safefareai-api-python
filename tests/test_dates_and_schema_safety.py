"""Pure date tests and test 30: no additional tables/columns are created or required."""
import ast
import pathlib
import re
from datetime import date

import pytest

from app.repositories import vehicle_maintenance_repository as repo_mod
from app.repositories.vehicle_maintenance_repository import (
    AccessScope, ListFilters, MaintenanceRecord, SqlServerMaintenanceSession,
)
from app.utils.date_calculations import (
    calculate_expected_date, compute_status, effective_due, effective_status, is_overdue_reminder_day,
    next_expected_date, reminder_schedule,
)

APP = pathlib.Path(__file__).resolve().parents[1] / "app"
EXISTING_COLUMNS = {
    "tenant_id", "vehicle_number", "device_id", "previous_vehicle_maintenance_date", "maintenance_time_window",
    "expected_vehicle_maintenance_date", "done_date", "status", "reason", "created_at", "updated_at",
}
POSTPONE_FIELDS = {"postponed_date", "postponed_by", "postponed_at", "postponed_reason"}   # read from the postponements table
MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "001_create_postponements_table.sql"


def test_formula_examples():
    assert calculate_expected_date(date(2026, 9, 30), 30) == date(2026, 10, 30)
    # next cycle: previous = done_date, expected = done_date + window
    assert next_expected_date(date(2026, 11, 5), 30) == date(2026, 12, 5)
    assert next_expected_date(date(2026, 11, 10), 30) == date(2026, 12, 10)
    assert next_expected_date(date(2026, 11, 15), 30) == date(2026, 12, 15)
    assert calculate_expected_date(date(2026, 11, 5), 45) == date(2026, 12, 20)
    assert calculate_expected_date(date(2028, 1, 30), 30) == date(2028, 2, 29)   # leap year
    with pytest.raises(ValueError):
        calculate_expected_date(date(2026, 1, 1), 0)


def test_reminder_schedule_examples():
    assert [r.reminder_date for r in reminder_schedule(date(2026, 10, 30))] == [
        date(2026, 10, 15), date(2026, 10, 23), date(2026, 10, 27),
        date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30)]
    assert [r.days_before for r in reminder_schedule(date(2026, 11, 10))] == [15, 7, 3, 2, 1, 0]


def test_status_rules():
    e = date(2026, 10, 30)
    assert compute_status(e, date(2026, 10, 29)) == "pending"
    assert compute_status(e, e) == "pending"
    assert compute_status(e, date(2026, 10, 31)) == "overdue"
    assert compute_status(e, date(2026, 10, 31), "completed") == "completed"
    assert [d for d in range(1, 11) if is_overdue_reminder_day(e, date.fromordinal(e.toordinal() + d), 3)] == [1, 4, 7, 10]
    assert [d for d in range(1, 6) if is_overdue_reminder_day(e, date.fromordinal(e.toordinal() + d), 1)] == [1, 2, 3, 4, 5]


def test_effective_due_and_status_use_postponed_date():
    e, p = date(2026, 10, 30), date(2026, 11, 10)
    assert effective_due(e, None) == e and effective_due(e, p) == p
    assert effective_status(e, None, "pending", date(2026, 11, 1)) == "overdue"
    assert effective_status(e, p, "pending", date(2026, 11, 1)) == "pending"
    assert effective_status(e, p, "pending", date(2026, 11, 11)) == "overdue"


def test_completed_reopens_15_days_before_due():
    due = date(2026, 11, 23)
    assert effective_status(due, None, "completed", date(2026, 11, 7)) == "completed"
    assert effective_status(due, None, "completed", date(2026, 11, 8)) == "pending"
    assert effective_status(due, None, "completed", date(2026, 11, 24)) == "overdue"


# ---------------------------------------------------------------- test 30
DDL = re.compile(r"\b(CREATE|ALTER|DROP|TRUNCATE|SELECT\s+.+\s+INTO|sp_rename|EXEC)\b", re.I | re.S)


# The merged SafeFare backend also contains other modules (sensors, tyre, Iris AI) under app/.
# This test only covers the files that belong to the Vehicle Maintenance module.
VM_MODULE_FILES = [
    "api/vehicle_maintenance.py",
    "vehicle_maintenance_module.py",
    "schemas/vehicle_maintenance.py",
    "repositories/vehicle_maintenance_repository.py",
    "repositories/alerts_repository.py",
    "services/vehicle_maintenance_service.py",
    "services/maintenance_notification_service.py",
    "services/errors.py",
    "scheduler/maintenance_scheduler.py",
    "integration/auth_adapter.py",
    "integration/directory.py",
    "integration/notifier.py",
    "integration/dev_auth.py",
    "utils/date_calculations.py",
    "core/vm_config.py",
    "core/vm_database.py",
]


def _sql_strings():
    for path in (APP / rel for rel in VM_MODULE_FILES):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", node.value):
                    yield path.name, node.value


def test_30_no_ddl_anywhere_in_module():
    offenders = [(f, s) for f, s in _sql_strings() if DDL.search(s)]
    assert offenders == []


def test_30_vehicle_maintenance_columns_unchanged():
    assert set(repo_mod.COLUMNS) == EXISTING_COLUMNS                      # the table keeps its 11 columns
    assert repo_mod.UPDATABLE_COLUMNS <= EXISTING_COLUMNS
    assert set(repo_mod.ROW_COLUMNS) == EXISTING_COLUMNS | POSTPONE_FIELDS
    assert "id" not in repo_mod.COLUMNS


def test_migration_only_creates_the_postponements_table():
    sql = MIGRATION.read_text()
    code = "\n".join(line.split("--")[0] for line in sql.splitlines())
    assert re.findall(r"CREATE\s+TABLE\s+([\w.]+)", code) == ["dbo.vehicle_maintenance_postponements"]
    assert not re.search(r"\bALTER\b|\bDROP\b|\bUPDATE\b|\bDELETE\b", code, re.I)
    assert "dbo.vehicle_maintenance " not in code.replace("dbo.vehicle_maintenance_postponements", "")


class RecordingCursor:
    def __init__(self, log, result):
        self.log, self.result, self.rowcount = log, result, 1

    def execute(self, sql, *params):
        self.log.append((sql, params))

    def fetchone(self):
        return self.result

    def fetchall(self):
        return []


class RecordingConn:
    def __init__(self, result=(0,) * 9):
        self.log, self.result = [], result

    def cursor(self):
        return RecordingCursor(self.log, self.result)


def _exercise_all_sql():
    conn = RecordingConn()
    s = SqlServerMaintenanceSession(conn, "dbo", "vehicles")
    rec = MaintenanceRecord(1, "AP31Z0044", 1215, date(2026, 9, 30), 30, date(2026, 10, 30), None, "pending", "r")
    s.devices_for_vehicle(1, "AP31Z0044")
    s.find(1, "AP31Z0044", 1215, for_update=True)
    s.insert(rec)
    s.update(1, "AP31Z0044", 1215, {"status": "overdue", "updated_at": None})
    s.insert_postponement(rec, date(2026, 11, 10), "Vehicle in workshop", "driver-1", None)
    conn.result = (0,)
    s.search(AccessScope([1], ["AP31Z0044"]),
             ListFilters("AP31Z0044", 1215, "overdue", date(2026, 1, 1), date(2026, 12, 31)), date(2026, 11, 9), 0, 20)
    s.all_schedules()
    s.tenants_for_vehicle("AP31Z0044", [1, 2])
    return conn.log


def test_30_repository_touches_only_existing_tables():
    for sql, params in _exercise_all_sql():
        tables = set(re.findall(r"\[dbo\]\.\[(\w+)\]", sql))
        assert tables <= {"vehicle_maintenance", "vehicles", "vehicle_maintenance_postponements"}, sql
        assert not DDL.search(sql), sql
        assert sql.count("?") == len(params), sql      # fully parameterised


def test_30_repository_rejects_unknown_update_columns():
    s = SqlServerMaintenanceSession(RecordingConn(), "dbo", "vehicles")
    with pytest.raises(ValueError):
        s.update(1, "X", 1, {"id": 5})
    with pytest.raises(ValueError):
        s.update(1, "X", 1, {"notification_sent": 1})
    with pytest.raises(ValueError):
        s.update(1, "X", 1, {"postponed_date": date(2026, 1, 1)})      # postponements never go into vehicle_maintenance


def test_generated_sql_is_valid_tsql():
    sqlglot = pytest.importorskip("sqlglot")
    for sql, _ in _exercise_all_sql():
        sqlglot.parse_one(sql.replace(" WITH (UPDLOCK, HOLDLOCK)", ""), read="tsql")

def test_directory_sql_is_valid_and_reads_only():
    from app.integration import directory as d
    fmt = {"schema": "dbo", "vehicles": "vehicles"}
    for sql, n in ((d.DRIVER_VEHICLES_SQL, 2), (d.FLEET_OWNERS_SQL, 1), (d.VEHICLE_DRIVERS_SQL, 2)):
        text = sql.format(**fmt)
        assert text.count("?") == n and not DDL.search(text) and text.lstrip().upper().startswith("SELECT")
        sqlglot = pytest.importorskip("sqlglot")
        sqlglot.parse_one(text, read="tsql")
    assert "driver_id" in d.VEHICLE_DRIVERS_SQL and "[{schema}].[users]" in d.VEHICLE_DRIVERS_SQL


def test_only_the_driver_assignment_statement_writes_to_vehicles():
    from app.integration import directory as d
    text = d.ASSIGN_DRIVER_SQL.format(schema="dbo", vehicles="vehicles")
    assert text.count("?") == 3 and "SET driver_id = ?" in text and "WHERE tenant_id = ?" in text
    pytest.importorskip("sqlglot").parse_one(text, read="tsql")
    other = [d.DRIVER_VEHICLES_SQL, d.FLEET_OWNERS_SQL, d.VEHICLE_DRIVERS_SQL, d.OWNER_DRIVERS_SQL]
    assert all(q.lstrip().upper().startswith("SELECT") for q in other)
