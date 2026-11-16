"""The only change to existing ingestion: insert_prs_readings adds one snapshot_id per call when the column exists,
and behaves exactly as before when it does not."""
import sys
import types
from datetime import datetime

import pytest

try:                                    # machines without the ODBC driver installed (CI, sandboxes)
    import pyodbc  # noqa: F401
except ImportError:
    sys.modules["pyodbc"] = types.ModuleType("pyodbc")

import app.database.prs_repository as repo

READINGS = [dict(tenant_id=1, vehicle_number="V", iot_kit="K", timestamp=datetime(2026, 11, 16, 10, 0, 0),
                 sensor_sub_id=5, sensor_data=f"unique_number:A{i},reading:occupied", lat=17.0, long=82.0)
            for i in range(1, 61)]


class FakeCursor:
    def __init__(self, has_column):
        self.has_column, self.executed, self.many = has_column, [], None

    def execute(self, sql, *a):
        self.executed.append(sql)

    def fetchone(self):
        return (60,) if self.has_column else (None,)

    def executemany(self, sql, values):
        self.many = (sql, values)

    def close(self):
        pass


class FakeConn:
    def __init__(self, cursor):
        self._c, self.committed = cursor, False

    def cursor(self):
        return self._c

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.mark.parametrize("has_column", [True, False])
def test_insert_with_and_without_snapshot_column(monkeypatch, has_column):
    cur = FakeCursor(has_column)
    conn = FakeConn(cur)
    monkeypatch.setattr(repo, "get_db_connection", lambda: conn)

    assert repo.insert_prs_readings([dict(r) for r in READINGS]) == 60
    sql, values = cur.many
    assert conn.committed and len(values) == 60

    if has_column:
        assert "snapshot_id" in sql and all(len(v) == 9 for v in values)
        assert len({v[8] for v in values}) == 1                      # ONE id for the whole file
    else:
        assert "snapshot_id" not in sql and all(len(v) == 8 for v in values)   # unchanged legacy behaviour
