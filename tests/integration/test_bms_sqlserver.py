"""Runs against a REAL SQL Server TEST database only (the 3 existing tables must exist; no migration needed).

Enable with:  BMS_TEST_DB=1  and SENSOR_DB_* in .env pointing at a database whose name contains "test".
It only writes rows for a throw-away vehicle "BMS-IT-<random>" and deletes them afterwards.
"""
import os
import uuid
from datetime import datetime

import pytest

pytestmark = pytest.mark.skipif(os.getenv("BMS_TEST_DB") != "1", reason="set BMS_TEST_DB=1 to run against SQL Server")


@pytest.fixture(scope="module")
def sql():
    from app.config.settings import settings
    from app.database.bms_repository import BmsRepository, _connect
    if "test" not in (settings.DB_NAME or "").lower():
        pytest.exit("Refusing to run: SENSOR_DB_NAME does not look like a test database")
    vehicle = f"BMS-IT-{uuid.uuid4().hex[:8]}".upper()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO dbo.bms_stop_details (tenant_id, vehicle_number, device_id, iot_kit, stop_sequence, stop_name, lat, [long], bms_in, bms_out, bms_total)
                   VALUES (1, ?, 987654, 'IT-KIT', 1, 'IT stop', 17.0, 82.0, 5, 0, 5)""", vehicle)
    conn.commit()
    yield BmsRepository(), vehicle
    cur.execute("DELETE FROM dbo.bms_sensor_comparison WHERE vehicle_number = ?", vehicle)
    cur.execute("DELETE FROM dbo.bms_stop_details WHERE vehicle_number = ?", vehicle)
    conn.commit()
    conn.close()


def test_final_comparison_is_idempotent_per_stop_visit(sql):
    from app.database.bms_repository import comparison_row
    from app.services.bms_stop_tracker import FinalVisit, VehicleState

    repo, vehicle = sql
    stop = repo.get_stops(1, vehicle, 987654)[0]
    state = VehicleState(tenant_id=1, vehicle_number=vehicle, device_id=987654)
    final = FinalVisit(stop=stop, comparison_status="MATCH", sensor_in=5, sensor_out=0, sensor_total=5, total_difference=0,
                       sensor_lat=17.0, sensor_long=82.0, sensor_timestamp=datetime(2026, 11, 16, 10, 5, 0))
    row = comparison_row(state, stop, "IT-KIT", final)
    assert repo.insert_comparison(row) == 1
    assert repo.insert_comparison(row) == 0                                   # a retry inserts nothing new
    rows, total = repo.list_comparisons(1, {"vehicle_number": vehicle}, 1, 50)
    assert total == 1 and rows[0]["comparison_status"] == "MATCH"
    assert repo.list_comparisons(2, {"vehicle_number": vehicle}, 1, 50)[1] == 0          # other tenant sees nothing
    last = repo.last_comparison(1, vehicle, 987654)
    assert last["stop_sequence"] == 1 and last["sensor_timestamp"] == datetime(2026, 11, 16, 10, 5, 0)


def test_active_vehicle_and_stop_queries_run(sql):
    repo, vehicle = sql
    assert repo.get_stops(1, vehicle, 987654)[0].name == "IT stop"
    assert repo.list_stops(1, vehicle, None)[0]["stop_sequence"] == 1
    repo.list_active_vehicles()                                                # the join with dbo.vehicles must parse
    assert repo.fetch_snapshot_rows(1, vehicle, datetime(2000, 1, 1), 60) == []