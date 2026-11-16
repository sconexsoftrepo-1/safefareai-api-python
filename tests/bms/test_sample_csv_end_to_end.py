from app.services.bms_state_store import StateStore
"""20 generated sample CSV files -> PRS CSV parser/ingestion (lat/long from the file) -> BMS worker -> 5 comparisons."""
import subprocess
import sys
import types
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

try:
    import pyodbc  # noqa: F401
except ImportError:
    sys.modules["pyodbc"] = types.ModuleType("pyodbc")

import app.services.prs_ingestion as ingestion
from app.config.bms_config import BmsConfig
from app.services.bms_comparison_service import BmsComparisonService
from app.services.bms_geo import haversine_m
from tests.bms.fake_repo import FakeRepo
from tests.bms.helpers import STOPS

ROOT = Path(__file__).resolve().parents[2]
VEHICLE = {"tenant_id": 1, "vehicle_number": "AP31Z0044", "iot_kit": "IOT-KIT-001", "device_id": 1215}

# One CSV per stop is all the sample has, so the demo needs these relaxed values (see docs).
DEMO_CFG = BmsConfig(min_consecutive_hits=1, min_dwell_seconds=0, departure_consecutive_readings=1,
                     initial_lookback_seconds=900, max_snapshot_age_seconds=900)


@pytest.fixture(scope="module")
def csv_files(tmp_path_factory):
    out = tmp_path_factory.mktemp("prs")
    subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "generate_bms_sample_csvs.py"), "--offline",
                    "--out-dir", str(out), "--start", "2026-11-16 10:00:00"], check=True, capture_output=True)
    return sorted(out.glob("PRS_*.csv"))


@pytest.fixture
def db_rows(csv_files, monkeypatch):
    """Run every file through the real process_prs_csv; capture what would be inserted into dbo.prs_sensor_readings."""
    captured = []
    monkeypatch.setattr(ingestion, "get_vehicle_device_by_iot_kit", lambda kit: dict(VEHICLE))
    monkeypatch.setattr(ingestion, "get_vehicle_location", lambda *a: pytest.fail("vendor API must not be called"))

    def fake_insert(readings):
        snapshot = str(uuid.uuid4())
        captured.extend({**r, "snapshot_id": snapshot} for r in readings)
        return len(readings)

    monkeypatch.setattr(ingestion, "insert_prs_readings", fake_insert)
    for f in csv_files:
        result = ingestion.process_prs_csv(f.read_bytes(), f.name)
        assert result["inserted_count"] == 60 and result["positions_matched"] == 60
    return captured


def test_20_files_with_60_seats_and_exactly_5_files_at_the_bms_stops(csv_files, db_rows):
    assert len(csv_files) == 20 and len(db_rows) == 1200
    at_stop = {}
    for f in csv_files:
        rows = [r for r in db_rows if r["timestamp"] == datetime.strptime(f.stem[-19:], "%d-%m-%Y_%H-%M-%S")]
        lat, lon = rows[0]["lat"], rows[0]["long"]
        nearest = min((haversine_m(lat, lon, s["lat"], s["long"]), s["stop_sequence"]) for s in STOPS)
        if nearest[0] <= 50:
            at_stop[f.name] = nearest[1]
        else:
            assert nearest[0] > 1000                              # all other files are far from every stop
    assert sorted(at_stop.values()) == [1, 2, 3, 4, 5]            # exactly 5 files, one per stop


def test_worker_stores_5_comparisons_with_expected_in_out_and_totals(db_rows):
    repo = FakeRepo()
    repo.add_vehicle(stops=STOPS)
    repo.add_rows(db_rows)
    now = max(r["timestamp"] for r in db_rows) + timedelta(seconds=5)
    service = BmsComparisonService(repo, DEMO_CFG, clock=lambda: now, store=StateStore())
    out = service.process_vehicle(dict(VEHICLE), now=now)
    assert out["processed"] == 20 and out["completed"] == 5

    got = {c["stop_sequence"]: (c["sensor_in"], c["sensor_out"], c["sensor_total"], c["total_difference"],
                                c["comparison_status"]) for c in repo.comparisons}
    assert got == {
        1: (12, 0, 12, 0, "MATCH"),
        2: (5, 1, 16, -1, "MISMATCH"),
        3: (9, 2, 23, 0, "MATCH"),
        4: (7, 3, 27, 2, "MISMATCH"),
        5: (4, 8, 23, 0, "MATCH"),
    }
    assert len(repo.comparisons) == 5


def test_with_the_default_strict_settings_one_file_per_stop_is_not_enough(db_rows):
    repo = FakeRepo()
    repo.add_vehicle(stops=STOPS)
    repo.add_rows(db_rows)
    now = max(r["timestamp"] for r in db_rows) + timedelta(seconds=5)
    BmsComparisonService(repo, BmsConfig(initial_lookback_seconds=900, max_snapshot_age_seconds=900),
                         clock=lambda: now, store=StateStore()).process_vehicle(dict(VEHICLE), now=now)
    assert repo.comparisons == []                                  # a single reading is a pass-by, nothing stored


def test_csv_without_lat_long_columns_still_works_as_before():
    from app.services.csv_parser import parse_csv_file
    body = "timestamp,sensor_sub_id,sensor_data\n2026-11-16 10:00:00,5,\"unique_number:A1,reading:occupied\"\n"
    rows = parse_csv_file(body.encode(), "PRS_IOT-KIT-001_16-11-2026_10-00-00.csv")
    assert "lat" not in rows[0]


def test_bad_lat_long_in_csv_is_rejected_with_the_row_number():
    from app.services.csv_parser import parse_csv_file
    body = "timestamp,sensor_data,lat,long\n2026-11-16 10:00:00,\"unique_number:A1,reading:occupied\",95,82\n"
    with pytest.raises(ValueError, match="row 2"):
        parse_csv_file(body.encode(), "PRS_IOT-KIT-001_16-11-2026_10-00-00.csv")