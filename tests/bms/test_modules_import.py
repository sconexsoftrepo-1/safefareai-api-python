"""Every BMS / ingestion file must compile and import (catches syntax / indentation slips in files tests don't exercise)."""
import importlib
import py_compile
import sys
import types
from pathlib import Path

import pytest

try:
    import pyodbc  # noqa: F401
except ImportError:
    sys.modules["pyodbc"] = types.ModuleType("pyodbc")

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "app/api/bms_comparison.py", "app/config/bms_config.py", "app/database/bms_repository.py",
    "app/services/bms_comparison_service.py", "app/services/bms_geo.py", "app/services/bms_snapshot.py",
    "app/services/bms_stop_tracker.py", "app/workers/bms_comparison_worker.py",
    "app/services/csv_parser.py", "app/services/prs_ingestion.py", "app/database/prs_repository.py",
    "app/main.py", "tools/generate_bms_sample_csvs.py",
]


@pytest.mark.parametrize("path", FILES)
def test_file_compiles(path):
    py_compile.compile(str(ROOT / path), doraise=True)


@pytest.mark.parametrize("module", [f[:-3].replace("/", ".") for f in FILES if f.startswith("app/") and f != "app/main.py"])
def test_module_imports(module):
    importlib.import_module(module)


def test_worker_loop_runs_one_cycle_and_stops():
    import threading
    from app.config.bms_config import BmsConfig
    from app.workers.bms_comparison_worker import start_bms_comparison_worker

    calls, stop = [], threading.Event()

    class Service:
        def run_cycle(self):
            calls.append(1)
            stop.set()

    start_bms_comparison_worker(stop_event=stop, cfg=BmsConfig(), service=Service())
    assert calls == [1]