from app.services.bms_state_store import StateStore
"""Source-table config, CSV position columns and the missing-table log message."""
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    import pyodbc  # noqa: F401
except ImportError:
    sys.modules["pyodbc"] = types.ModuleType("pyodbc")

import app.database.bms_repository as bms_repo
from app.api.bms_comparison import bms_router, bms_sensor_router, get_bms_repository
from app.config.bms_config import BmsConfig, load_bms_config
from app.services.bms_comparison_service import BmsComparisonService
from app.services.csv_parser import parse_csv_file
from tests.bms.fake_repo import FakeRepo
from tests.bms.harness import Harness
from tests.bms.helpers import BASE, STOPS

ROOT = Path(__file__).resolve().parents[2]


def client_for(repo):
    app = FastAPI(); app.include_router(bms_router); app.include_router(bms_sensor_router)
    app.dependency_overrides[get_bms_repository] = lambda: repo
    return TestClient(app)


def test_source_table_defaults_to_the_real_table_and_is_validated():
    assert load_bms_config({}).source_table == "dbo.prs_sensor_readings"
    for bad in ("dbo.x; DROP TABLE y", "a b", "dbo.[x]"):
        with pytest.raises(ValueError):
            load_bms_config({"BMS_SOURCE_TABLE": bad})
        with pytest.raises(ValueError):
            bms_repo.BmsRepository(bad)


def test_missing_table_gives_one_short_message_not_a_stack_trace(caplog):
    repo = FakeRepo()
    repo.add_vehicle(stops=STOPS)
    repo.last_comparison = lambda *a: (_ for _ in ()).throw(RuntimeError("[42S02] Invalid object name 'dbo.bms_sensor_comparison'."))
    service = BmsComparisonService(repo, BmsConfig(), clock=lambda: datetime(2026, 11, 16), store=StateStore())
    BmsComparisonService._last_missing_warning = None
    with caplog.at_level("ERROR"):
        service.run_cycle(); service.run_cycle()
    assert len([r for r in caplog.records if "does not exist" in r.message]) == 1
    assert not any(r.exc_info for r in caplog.records)