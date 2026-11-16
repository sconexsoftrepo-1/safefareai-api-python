"""Frontend GET API results (FastAPI TestClient + in-memory repository)."""
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.bms_comparison import bms_router, bms_sensor_router, get_bms_repository
from tests.bms.harness import Harness
from tests.bms.helpers import STOPS

A1_12 = set(range(1, 13))


@pytest.fixture
def ctx():
    h = Harness()
    # tenant 2 has its own vehicle + stops
    h.repo.add_vehicle(tenant_id=2, vehicle_number="TS09AB1234", device_id=2001, iot_kit="IOT-KIT-002", stops=STOPS)
    after2 = h.visit_stop(2, A1_12, boarded=set(range(13, 19)), left={1})      # In 6 / Out 1 / Total 17 = exactly the BMS row: MATCH
    h.visit_stop(3, after2, boarded={30, 31})                                   # In 2 / Total 19 vs BMS 9 / 3 / 23: MISMATCH
    app = FastAPI()
    app.include_router(bms_router)
    app.include_router(bms_sensor_router)
    app.dependency_overrides[get_bms_repository] = lambda: h.repo
    return h, TestClient(app)


H1 = {"X-Tenant-ID": "1"}
VEH = "?vehicle_number=AP31Z0044"
COMP = "/api/bms-sensor/comparisons"


def test_comparisons_list_has_bms_sensor_difference_status_and_stop_details(ctx):
    h, client = ctx
    r = client.get(COMP + VEH, headers=H1)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and body["total"] == 2 and body["page"] == 1
    assert "ESTIMATES" in body["note"]
    item = next(i for i in body["items"] if i["stop"]["stop_sequence"] == 2)
    assert item["stop"]["stop_name"] == STOPS[1]["stop_name"]
    assert item["bms"] == {"in": 6, "out": 1, "total": 17}
    assert item["sensor"]["total"] == 17 and item["sensor"]["in_out_is_estimate"] is True
    assert item["sensor"]["in"] == 6 and item["sensor"]["out"] == 1
    assert item["total_difference"] == 0 and item["comparison_status"] == "MATCH"
    assert isinstance(item["sensor"]["timestamp"], str) and isinstance(item["created_at"], str)
    assert item["vehicle_number"] == "AP31Z0044" and item["journey_id"] is None


def test_vehicle_number_is_optional_for_both_endpoints(ctx):
    _, client = ctx
    assert client.get(COMP, headers=H1).json()["total"] == 2
    assert client.get("/api/bms/stops", headers=H1).json()["count"] == 5


def test_filters(ctx):
    _, client = ctx
    assert client.get(COMP + VEH + "&comparison_status=MISMATCH", headers=H1).json()["total"] == 1
    assert client.get(COMP + VEH + "&comparison_status=mismatch", headers=H1).json()["total"] == 1
    assert client.get(COMP + VEH + "&stop_sequence=2", headers=H1).json()["total"] == 1
    assert client.get(COMP + VEH + "&device_id=1215", headers=H1).json()["total"] == 2
    assert client.get(COMP + "?vehicle_number=NOPE", headers=H1).json()["total"] == 0
    assert client.get(COMP + VEH + "&comparison_status=BOGUS", headers=H1).status_code == 400


def test_pagination(ctx):
    _, client = ctx
    body = client.get(COMP + VEH + "&page=2&page_size=1", headers=H1).json()
    assert body["total"] == 2 and body["count"] == 1 and body["page"] == 2
    assert client.get(COMP + VEH + "&page_size=1000", headers=H1).status_code == 422


def test_tenant_isolation(ctx):
    _, client = ctx
    other = {"X-Tenant-ID": "2"}
    assert client.get(COMP + VEH, headers=other).json()["total"] == 0
    stops = client.get("/api/bms/stops?vehicle_number=TS09AB1234", headers=other).json()
    assert stops["count"] == 5 and all(s["tenant_id"] == 2 for s in stops["items"])
    assert client.get("/api/bms/stops?vehicle_number=AP31Z0044", headers=other).json()["count"] == 0
    assert all(s["tenant_id"] == 1 for s in client.get("/api/bms/stops", headers=H1).json()["items"])


def test_tenant_header_is_optional_and_validated_when_given(ctx, monkeypatch):
    _, client = ctx
    monkeypatch.delenv("DEV_TENANT_ID", raising=False)
    monkeypatch.delenv("BMS_DEFAULT_TENANT_ID", raising=False)
    assert client.get(COMP + VEH).json()["total"] == 2                       # no header -> default tenant 1
    monkeypatch.setenv("BMS_DEFAULT_TENANT_ID", "2")
    assert client.get(COMP + VEH).json()["total"] == 0                       # configured default tenant is used
    assert client.get("/api/bms/stops").json()["count"] == 5
    assert client.get(COMP + VEH, headers={"X-Tenant-ID": "0"}).status_code == 400


def test_bms_stops_endpoint(ctx):
    _, client = ctx
    body = client.get("/api/bms/stops?vehicle_number=AP31Z0044&device_id=1215", headers=H1).json()
    assert body["count"] == 5
    assert [s["stop_sequence"] for s in body["items"]] == [1, 2, 3, 4, 5]
    tuni = body["items"][1]
    assert tuni["bms"] == {"in": 6, "out": 1, "total": 17} and tuni["lat"] == 17.36856 and tuni["long"] == 82.54323


def test_repository_failure_returns_500_without_leaking_details(ctx):
    h, client = ctx
    h.repo.list_comparisons = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret sql text"))
    r = client.get(COMP + VEH, headers=H1)
    assert r.status_code == 500 and "secret" not in r.text


def test_only_two_get_endpoints_exist(ctx):
    _, client = ctx
    assert client.post(COMP, headers=H1, json={}).status_code == 405
    for gone in ("/api/bms-sensor/tracking", "/api/bms-sensor/latest", "/api/bms-sensor/comparisons/1"):
        assert client.get(gone, headers=H1).status_code in (404, 405, 422)


def test_comparisons_response_has_summary_for_all_rows_not_just_the_page(ctx):
    h, client = ctx
    s = client.get(COMP + VEH + "&page_size=1", headers=H1).json()["summary"]
    assert s["stops"] == 2 and s["compared"] == 2 and s["exact_matches"] == 1 and s["mismatches"] == 1
    assert s["match_rate_percent"] == 50.0 and s["incomplete"] == 0
    assert s["bus_capacity"] == 60 and s["over_capacity_stops"] == 0              # capacity = seats A1..A60
    assert client.get(COMP + VEH + "&bus_capacity=20", headers=H1).json()["summary"]["over_capacity_stops"] == 1     # only stop 3 (BMS 23) is above 20
    # the comparison_status filter only filters "items"; the summary keeps counting every row
    body = client.get(COMP + VEH + "&comparison_status=MISMATCH", headers=H1).json()
    assert body["total"] == 1 and body["summary"]["stops"] == 2 and body["summary"]["match_rate_percent"] == 50.0
    # tenant 2 has no rows: empty summary, no error
    empty = client.get(COMP, headers={"X-Tenant-ID": "2"}).json()["summary"]
    assert empty["stops"] == 0 and empty["match_rate_percent"] is None and empty["latest"] is None


def test_summary_numbers_of_the_dashboard_example():
    from app.api.bms_comparison import build_summary

    def row(i, bi, bo, bt, si, so, st, status):
        return {"id": i, "stop_sequence": i, "bms_in": bi, "bms_out": bo, "bms_total": bt, "sensor_in": si,
                "sensor_out": so, "sensor_total": st, "total_difference": st - bt, "comparison_status": status,
                "sensor_timestamp": None}
    rows = [row(5, 2, 8, 22, 2, 8, 19, "MISMATCH"), row(4, 4, 6, 23, 4, 6, 22, "MISMATCH"),
            row(3, 6, 4, 20, 5, 6, 21, "MISMATCH"), row(2, 8, 2, 16, 8, 2, 16, "MATCH"), row(1, 10, 0, 10, 10, 0, 10, "MATCH")]
    s = build_summary(rows, bus_capacity=44)
    assert (s["stops"], s["compared"], s["exact_matches"], s["mismatches"]) == (5, 5, 2, 3)
    assert s["match_rate_percent"] == 40.0 and s["mean_abs_error"] == 1.0 and s["max_abs_error"] == 3
    assert s["boarded"] == {"bms": 30, "sensor": 29} and s["alighted"] == {"bms": 20, "sensor": 22}
    assert s["latest"]["on_board_bms"] == 22 and s["latest"]["on_board_sensor"] == 19 and s["latest"]["difference"] == -3
    assert s["max_on_board"] == {"bms": 23, "sensor": 22} and s["over_capacity_stops"] == 0
    assert build_summary(rows, bus_capacity=20)["over_capacity_stops"] == 3          # BMS 22/23 and sensor 21/22 are above 20


def test_summary_leaves_incomplete_rows_out_of_the_comparison():
    from app.api.bms_comparison import build_summary
    rows = [{"id": 2, "comparison_status": "INCOMPLETE", "bms_total": 10, "sensor_total": None, "total_difference": None},
            {"id": 1, "comparison_status": "MATCH", "bms_total": 5, "bms_in": 5, "bms_out": 0,
             "sensor_total": 5, "sensor_in": 5, "sensor_out": 0, "total_difference": 0}]
    s = build_summary(rows)
    assert s["stops"] == 2 and s["compared"] == 1 and s["incomplete"] == 1 and s["without_sensor_count"] == 1
    assert s["match_rate_percent"] == 100.0 and s["boarded"] == {"bms": 5, "sensor": 5}