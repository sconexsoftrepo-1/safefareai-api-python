"""Runs against a REAL SQL Server TEST database only.

Enable with:
    VM_TEST_DB=1  plus the usual DB_* variables pointing at a TEST database.
    VM_TEST_VEHICLE="<tenant_id>|<vehicle_number>|<device_id>"   (an existing row in vehicles that has NO
                                                                   vehicle_maintenance row yet)

Safety: refuses to run unless DB_DATABASE contains "test". Only touches the
vehicle_maintenance row for VM_TEST_VEHICLE and deletes it afterwards.
"""
import os
from datetime import date

import pytest

from app.core.vm_config import get_settings
from app.core.vm_database import Database
from app.repositories.vehicle_maintenance_repository import (
    COLUMNS, AccessScope, ListFilters, MaintenanceRecord, SqlServerMaintenanceRepository,
)

pytestmark = pytest.mark.skipif(os.getenv("VM_TEST_DB") != "1", reason="set VM_TEST_DB=1 to run against SQL Server")


@pytest.fixture(scope="module")
def ctx():
    s = get_settings()
    if "test" not in s.db_database.lower():
        pytest.exit("Refusing to run integration tests: DB_DATABASE does not look like a test database")
    raw = os.getenv("VM_TEST_VEHICLE")
    if not raw:
        pytest.skip("VM_TEST_VEHICLE not set")
    tenant, vehicle, device = raw.split("|")
    db = Database(s)
    repo = SqlServerMaintenanceRepository(db, s.db_schema, s.vehicles_table)

    def schema_snapshot():
        with db.transaction() as conn:
            cur = conn.cursor()
            cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
            tables = sorted(tuple(r) for r in cur.fetchall())
            cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'vehicle_maintenance'")
            cols = sorted(r[0] for r in cur.fetchall())
        return tables, cols

    def cleanup():
        with db.transaction() as conn:
            conn.cursor().execute(
                f"DELETE FROM [{s.db_schema}].[vehicle_maintenance] WHERE tenant_id = ? AND vehicle_number = ? AND device_id = ?",
                tenant, vehicle, device)

    with repo.unit_of_work() as sess:
        if sess.find(tenant, vehicle):
            pytest.skip("VM_TEST_VEHICLE already has a maintenance row; choose another vehicle")
    before = schema_snapshot()
    yield repo, tenant, vehicle, device, before, schema_snapshot
    cleanup()


def test_schema_matches_expected_columns(ctx):
    *_, before, _ = ctx
    assert set(before[1]) == set(COLUMNS), "vehicle_maintenance columns differ from the specification"


def test_round_trip_and_queries(ctx):
    repo, tenant, vehicle, device, before, snapshot = ctx
    with repo.unit_of_work() as s:
        assert device in [str(d) for d in s.devices_for_vehicle(tenant, vehicle)]
        s.insert(MaintenanceRecord(tenant, vehicle, device, date(2026, 9, 30), 30, date(2026, 10, 30),
                                   None, "pending", "integration test"))
    with repo.unit_of_work() as s:
        rows = s.find(tenant, vehicle, device, for_update=True)
        assert len(rows) == 1 and rows[0].expected_vehicle_maintenance_date == date(2026, 10, 30)
        assert s.update(tenant, vehicle, device, {"expected_vehicle_maintenance_date": date(2026, 11, 10)}) == 1
        items, total = s.search(AccessScope([tenant]), ListFilters(vehicle_number=vehicle, status="overdue"),
                                date(2026, 11, 11), 0, 10)
        assert total == 1 and items[0][1] == "overdue"
        counts = s.dashboard(AccessScope([tenant], [vehicle]), date(2026, 11, 3))
        assert counts.total == 1 and counts.due_within_7_days == 1
    # rollback check
    with pytest.raises(RuntimeError):
        with repo.unit_of_work() as s:
            s.update(tenant, vehicle, device, {"reason": "should be rolled back"})
            raise RuntimeError("boom")
    with repo.unit_of_work() as s:
        assert s.find(tenant, vehicle, device)[0].reason == "integration test"
    assert snapshot() == before        # test 30: no tables or columns were added
