from dataclasses import replace
from datetime import timedelta

import pytest

from app.config.bms_config import BmsConfig
from app.services.bms_comparison_service import BmsComparisonService
from app.services.bms_state_store import StateStore
from app.services.bms_stop_tracker import (
    APPROACHING, ARRIVED, COMPLETED, DWELLING, NOT_REACHED, STOP_CANDIDATE, VehicleState, advance,
)
from app.services.bms_snapshot import build_snapshots
from tests.bms.fake_repo import FakeRepo
from tests.bms.harness import VEHICLE, Harness
from tests.bms.helpers import BASE, STOPS, offset_north, seat_rows
from app.services.bms_stop_tracker import Stop

TUNI = STOPS[1]
A1_12 = set(range(1, 13))


def stops_list():
    return [Stop(id=i + 1, sequence=s["stop_sequence"], name=s["stop_name"], lat=s["lat"], lon=s["long"],
                 bms_in=s["bms_in"], bms_out=s["bms_out"], bms_total=s["bms_total"]) for i, s in enumerate(STOPS)]


def snap_at(seconds, lat, lon, occupied=A1_12):
    return build_snapshots(seat_rows(BASE + timedelta(seconds=seconds), occupied, lat, lon, snapshot_id=f"s{seconds}"))[0]


# =============================================================================== state machine (pure)
def test_phases_not_reached_approaching_candidate_arrived_dwelling_completed():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)

    advance(st, snap_at(0, 17.9, 83.5), stops, cfg)
    assert st.phase == NOT_REACHED

    advance(st, snap_at(10, *offset_north(TUNI["lat"], TUNI["long"], 200)), stops, cfg)
    assert st.phase == APPROACHING

    advance(st, snap_at(20, *offset_north(TUNI["lat"], TUNI["long"], 20)), stops, cfg)
    assert st.phase == STOP_CANDIDATE and st.hit_count == 1

    advance(st, snap_at(30, *offset_north(TUNI["lat"], TUNI["long"], 22)), stops, cfg)
    assert st.phase == ARRIVED

    advance(st, snap_at(50, *offset_north(TUNI["lat"], TUNI["long"], 21)), stops, cfg)   # 30 s after the first hit
    assert st.phase == DWELLING

    far = offset_north(TUNI["lat"], TUNI["long"], 200)
    assert advance(st, snap_at(60, *far), stops, cfg).final is None        # 1 reading outside: wait
    res = advance(st, snap_at(70, *far), stops, cfg)                       # 2nd reading outside: departed
    assert res.final is not None and st.phase == COMPLETED and st.last_completed_sequence == 2


def test_bus_passing_a_stop_without_dwelling_creates_nothing():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    near = offset_north(TUNI["lat"], TUNI["long"], 20)
    far = offset_north(TUNI["lat"], TUNI["long"], 200)
    results = [advance(st, snap_at(s, *p), stops, cfg) for s, p in [(0, near), (10, far), (20, far), (30, far)]]
    assert all(r.final is None for r in results)
    assert st.phase in (NOT_REACHED, APPROACHING) and st.last_completed_sequence == 0


def test_single_reading_inside_radius_is_not_enough_to_arrive():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    advance(st, snap_at(0, *offset_north(TUNI["lat"], TUNI["long"], 20)), stops, cfg)
    assert st.phase == STOP_CANDIDATE


def test_gps_fluctuating_between_entry_and_exit_radius_keeps_one_visit():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    metres = [20, 60, 65, 45, 62, 68, 30, 66, 64, 25]          # all < 70 m exit radius, several > 50 m entry radius
    finals = []
    for i, m in enumerate(metres):
        finals.append(advance(st, snap_at(i * 10, *offset_north(TUNI["lat"], TUNI["long"], m)), stops, cfg).final)
    assert all(f is None for f in finals) and st.phase == DWELLING
    far = offset_north(TUNI["lat"], TUNI["long"], 300)
    done = [advance(st, snap_at(200 + i * 10, *far), stops, cfg).final for i in range(3)]
    assert sum(f is not None for f in done) == 1            # exactly ONE comparison


def test_one_stray_reading_outside_exit_radius_does_not_end_the_visit():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    for i, m in enumerate([20, 20, 20, 20]):
        advance(st, snap_at(i * 10, *offset_north(TUNI["lat"], TUNI["long"], m)), stops, cfg)
    advance(st, snap_at(40, *offset_north(TUNI["lat"], TUNI["long"], 400)), stops, cfg)    # GPS glitch
    advance(st, snap_at(50, *offset_north(TUNI["lat"], TUNI["long"], 20)), stops, cfg)
    assert st.phase == DWELLING and st.outside_count == 0


def test_two_overlapping_stops_are_ambiguous_and_not_guessed():
    cfg = BmsConfig()
    a = Stop(1, 1, "A", 17.0, 82.0, 1, 0, 1)
    b = Stop(2, 2, "B", *offset_north(17.0, 82.0, 30), 1, 0, 1)
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    res = advance(st, snap_at(0, *offset_north(17.0, 82.0, 15)), [a, b], cfg)
    assert "AMBIGUOUS_STOP_SKIPPED" in res.events and st.phase == NOT_REACHED


def test_invalid_gps_never_starts_a_visit():
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    res = advance(st, snap_at(0, None, None), stops_list(), BmsConfig())
    assert "GPS_INVALID_SKIPPED" in res.events and st.phase == NOT_REACHED
    assert st.last_seats is not None            # baseline still updated: previous seat state is not lost


def test_stop_sequence_validation_strict_mode():
    cfg = BmsConfig(allow_skipped_stops=False)
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    stop3 = STOPS[2]
    for i in range(4):
        advance(st, snap_at(i * 10, *offset_north(stop3["lat"], stop3["long"], 20)), stops_list(), cfg)
    assert st.phase in (NOT_REACHED, APPROACHING) and st.current_stop_sequence is None     # stop 3 is not next


# =============================================================================== worker flow (service + fake DB)
def test_tuni_visit_creates_exactly_one_final_comparison_matching_the_brief_sample():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)                       # baseline: 12 occupied
    boarded = set(range(13, 18))                            # 5 board -> 17 occupied
    h.send(*h.at_stop(2, 20), A1_12 | boarded)
    h.send(*h.at_stop(2, 22), A1_12 | boarded)
    after_leave = (A1_12 | boarded) - {1}                   # 1 leaves -> 16
    h.send(*h.at_stop(2, 21), after_leave)
    h.send(*h.at_stop(2, 20), after_leave)
    assert h.comparisons == []                              # nothing is stored while the bus is still at the stop
    h.send(*h.at_stop(2, 160), after_leave)
    h.send(*h.at_stop(2, 170), after_leave)

    tuni = [c for c in h.comparisons if c["stop_sequence"] == 2]
    assert len(tuni) == 1
    c = tuni[0]
    assert (c["bms_in"], c["bms_out"], c["bms_total"]) == (6, 1, 17)
    assert (c["sensor_in"], c["sensor_out"], c["sensor_total"], c["total_difference"]) == (5, 1, 16, -1)
    assert c["comparison_status"] == "MISMATCH"
    assert c["stop_name"] == TUNI["stop_name"]
    assert c["sensor_timestamp"] is not None and c["sensor_lat"] is not None


def test_stop_never_visited_gets_no_row_and_a_visited_stop_is_compared():
    h = Harness()
    h.visit_stop(2, A1_12, boarded=set(range(13, 18)))
    assert [c["stop_sequence"] for c in h.comparisons] == [2]      # nothing is invented for stop 1
    assert h.comparisons[0]["comparison_status"] == "MATCH"        # 17 occupied == BMS total 17


def test_full_trip_stores_five_rows_then_the_next_trip_starts_again_at_stop_1():
    h = Harness()
    occ = set()
    plan = {1: (set(range(1, 13)), set()), 2: (set(range(13, 18)), {1}), 3: (set(range(18, 27)), set()),
            4: (set(range(27, 30)), set()), 5: (set(), set())}
    for seq in range(1, 6):
        boarded, left = plan[seq]
        occ = h.visit_stop(seq, occ, boarded, left)
    assert [c["stop_sequence"] for c in h.comparisons] == [1, 2, 3, 4, 5]
    assert h.state().last_completed_sequence == 0                  # route finished -> ready for the next trip

    occ = set()
    for seq in range(1, 6):
        boarded, left = plan[seq]
        occ = h.visit_stop(seq, occ, boarded, left)
    assert len(h.comparisons) == 10
    assert len({(c["stop_sequence"], c["sensor_timestamp"]) for c in h.comparisons}) == 10


def test_duplicate_sensor_response_is_ignored():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    h.send(*h.at_stop(2, 20), A1_12)
    rows_before = list(h.repo.rows)
    h.repo.add_rows([dict(r) for r in rows_before[-60:]])          # the SAME response inserted again (S3 re-processed)
    state_before = h.state()
    out = h.run()
    state_after = h.state()
    assert out["processed"] == 0 and state_after.hit_count == state_before.hit_count


def test_stale_sensor_response_is_not_used():
    h = Harness()
    h.repo.add_rows(seat_rows(BASE - timedelta(hours=1), A1_12, *h.at_stop(2, 20), snapshot_id="old"))
    h.now = BASE
    out = h.service.process_vehicle(dict(VEHICLE), now=BASE)
    assert out["processed"] == 0
    # a one-hour-old row is outside the first-run lookback so it is never even read; force it into the cursor window:
    cfg = BmsConfig(initial_lookback_seconds=7200)
    service = BmsComparisonService(h.repo, cfg, clock=lambda: BASE, store=StateStore())
    out = service.process_vehicle(dict(VEHICLE), now=BASE)
    assert out["processed"] == 0 and out["skipped"] == 1 and h.comparisons == []


def test_out_of_order_response_is_ignored_and_does_not_move_the_cursor_back():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)                       # t = +10
    state = h.state()
    h.repo.add_rows(seat_rows(BASE + timedelta(seconds=5), A1_12, *h.at_stop(2, 20), snapshot_id="late"))
    assert h.run()["processed"] == 0                         # not fetched at all: timestamp is behind the cursor
    assert h.state().last_snapshot_ts == state.last_snapshot_ts


def test_future_timestamp_is_ignored_and_does_not_poison_the_cursor():
    h = Harness()
    h.repo.add_rows(seat_rows(BASE + timedelta(days=1), A1_12, *h.at_stop(2, 20), snapshot_id="future"))
    h.now = BASE + timedelta(seconds=5)
    out = h.service.process_vehicle(dict(VEHICLE), now=h.now)
    assert out["processed"] == 0 and out["skipped"] == 1
    assert h.state() is None or h.state().last_snapshot_ts is None


def test_incomplete_snapshots_during_the_visit_give_incomplete_status_never_mismatch():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    for m in (20, 22, 21, 20):
        h.send(*h.at_stop(2, m), A1_12, skip=["A60"])         # 59 seats only, every time
    h.send(*h.at_stop(2, 160), A1_12)
    h.send(*h.at_stop(2, 170), A1_12)
    c = [c for c in h.comparisons if c["stop_sequence"] == 2][0]
    assert c["comparison_status"] == "INCOMPLETE" and c["sensor_total"] is None and c["total_difference"] is None


def test_one_bad_snapshot_inside_the_visit_keeps_a_valid_total_and_never_assumes_empty_seats():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    h.send(*h.at_stop(2, 20), A1_12 | {13, 14, 15, 16, 17})
    h.send(*h.at_stop(2, 22), A1_12 | {13, 14, 15, 16, 17}, skip=["A1", "A2"])     # incomplete - ignored for counting
    h.send(*h.at_stop(2, 21), A1_12 | {13, 14, 15, 16, 17})
    h.send(*h.at_stop(2, 20), A1_12 | {13, 14, 15, 16, 17})
    h.send(*h.at_stop(2, 160), A1_12 | {13, 14, 15, 16, 17})
    h.send(*h.at_stop(2, 170), A1_12 | {13, 14, 15, 16, 17})
    c = [c for c in h.comparisons if c["stop_sequence"] == 2][0]
    assert c["sensor_total"] == 17 and c["comparison_status"] == "MATCH"
    assert (c["sensor_in"], c["sensor_out"]) == (5, 0)       # the missing seats were not counted as 2 outs + 2 ins


def test_wrong_iot_kit_is_not_trusted():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    for m in (20, 22, 21, 20):
        h.send(*h.at_stop(2, m), A1_12, kit="SOME-OTHER-KIT")
    h.send(*h.at_stop(2, 160), A1_12)
    h.send(*h.at_stop(2, 170), A1_12)
    c = [c for c in h.comparisons if c["stop_sequence"] == 2][0]
    assert c["comparison_status"] == "INCOMPLETE"


def test_iot_kit_punctuation_difference_is_accepted():
    h = Harness()
    h.send(*h.at_stop(2, 20), A1_12, kit="IOT_KIT001")
    assert h.state().phase == STOP_CANDIDATE


def test_gps_outside_every_stop_creates_no_comparison():
    h = Harness()
    for i in range(10):
        h.send(18.5, 84.5, A1_12)
    assert h.comparisons == []


def test_no_comparison_every_ten_seconds_while_waiting_at_the_stop():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    for _ in range(12):
        h.send(*h.at_stop(2, 20), A1_12)
    assert h.comparisons == []


def test_backend_restart_in_the_middle_of_a_stop_visit_recovers_the_state():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    h.send(*h.at_stop(2, 20), A1_12 | {13, 14, 15, 16, 17})
    h.send(*h.at_stop(2, 22), A1_12 | {13, 14, 15, 16, 17})
    h.new_service()                                           # <- restart
    after = (A1_12 | {13, 14, 15, 16, 17}) - {1}
    h.send(*h.at_stop(2, 21), after)
    h.send(*h.at_stop(2, 20), after)
    h.new_service()                                           # <- and again
    h.send(*h.at_stop(2, 160), after)
    h.send(*h.at_stop(2, 170), after)
    c = [c for c in h.comparisons if c["stop_sequence"] == 2]
    assert len(c) == 1 and (c[0]["sensor_in"], c[0]["sensor_out"], c[0]["sensor_total"]) == (5, 1, 16)


def test_restart_rereads_recent_snapshots_and_ends_in_the_same_state():
    h = Harness()
    h.send(*h.at_stop(2, 150), A1_12)
    h.send(*h.at_stop(2, 20), A1_12)
    before = h.state().phase
    h.new_service()
    h.run()
    assert h.state().phase == before and h.comparisons == []


def test_database_failure_on_final_insert_then_safe_retry_stores_exactly_one_row():
    h = Harness()
    after = A1_12 | {13, 14, 15, 16, 17}
    h.send(*h.at_stop(2, 150), A1_12)
    for m in (20, 22, 21, 20):
        h.send(*h.at_stop(2, m), after)
    h.send(*h.at_stop(2, 160), after)
    h.repo.fail["insert_comparison"] = 1
    with pytest.raises(RuntimeError):
        h.send(*h.at_stop(2, 170), after)                     # the departure snapshot: the insert fails, nothing saved
    assert [c for c in h.comparisons if c["stop_sequence"] == 2] == []
    assert h.state().phase == DWELLING       # state was NOT advanced
    h.run()                                                   # next cycle retries the same snapshot
    h.run()
    assert len([c for c in h.comparisons if c["stop_sequence"] == 2]) == 1


def test_run_cycle_survives_sql_failure_and_recovers():
    h = Harness()
    h.repo.fail["fetch_snapshot_rows"] = 1
    h.repo.add_rows(seat_rows(BASE + timedelta(seconds=10), A1_12, *h.at_stop(2, 20), snapshot_id="x"))
    h.now = BASE + timedelta(seconds=15)
    h.service.clock = lambda: h.now
    first = h.service.run_cycle()
    assert first["results"][0].get("error") is True           # logged, not raised
    second = h.service.run_cycle()
    assert second["results"][0]["processed"] == 1


def test_overlapping_run_for_the_same_vehicle_is_skipped():
    h = Harness()
    lock = h.service._lock_for((1, "AP31Z0044", 1215))
    lock.acquire()
    try:
        assert h.run()["busy"] is True
    finally:
        lock.release()


def test_different_tenants_and_devices_are_processed_independently():
    repo = FakeRepo()
    repo.add_vehicle(tenant_id=1, vehicle_number="AP31Z0044", device_id=1215, stops=STOPS)
    repo.add_vehicle(tenant_id=2, vehicle_number="AP31Z0044", device_id=9999, iot_kit="IOT-KIT-001", stops=STOPS)
    h = Harness(repo=repo)
    near = h.at_stop(2, 20)
    repo.add_rows(seat_rows(BASE + timedelta(seconds=10), A1_12, *near, tenant=1, snapshot_id="t1"))
    repo.add_rows(seat_rows(BASE + timedelta(seconds=10), {1, 2, 3}, *h.at_stop(1, 20), tenant=2, snapshot_id="t2"))
    h.now = BASE + timedelta(seconds=15)
    h.service.clock = lambda: h.now
    h.service.run_cycle()
    s1 = h.store.get(1, "AP31Z0044", 1215)
    s2 = h.store.get(2, "AP31Z0044", 9999)
    assert s1.current_stop_sequence == 2 and s2.current_stop_sequence == 1
    assert s1.last_seats.count("O") == 12 and s2.last_seats.count("O") == 3


def test_idle_for_a_day_resets_progress_so_a_new_trip_starts_at_stop_1():
    h = Harness()
    h.visit_stop(1, set(), boarded=set(range(1, 13)))
    assert h.state().last_completed_sequence == 1
    h.now = h.now + timedelta(hours=30)
    h.service.process_vehicle(dict(VEHICLE), now=h.now)
    assert h.state().last_completed_sequence == 0


def test_restart_after_a_stored_stop_continues_with_the_next_stop_without_duplicates():
    h = Harness()
    h.visit_stop(1, set(), boarded=set(range(1, 13)))
    assert [c["stop_sequence"] for c in h.comparisons] == [1]
    h.new_service()                                           # restart: memory empty, rebuilt from the 3 tables
    h.run()
    assert h.state().last_completed_sequence == 1
    assert [c["stop_sequence"] for c in h.comparisons] == [1]  # the replayed stop 1 visit is not stored twice
    h.visit_stop(2, A1_12, boarded=set(range(13, 18)))
    assert [c["stop_sequence"] for c in h.comparisons] == [1, 2]


def test_restart_after_the_last_stop_starts_the_next_trip_at_stop_1():
    h = Harness()
    occ = set()
    plan = {1: (set(range(1, 13)), set()), 2: (set(range(13, 18)), {1}), 3: (set(range(18, 27)), set()),
            4: (set(range(27, 30)), set()), 5: (set(), set())}
    for seq in range(1, 6):
        occ = h.visit_stop(seq, occ, *plan[seq])
    h.new_service()
    h.run()
    assert h.state().last_completed_sequence == 0 and len(h.comparisons) == 5


def test_visit_timeout_closes_a_visit_whose_departure_was_never_seen():
    h = Harness()
    after = A1_12 | {13, 14, 15, 16, 17}
    h.send(*h.at_stop(2, 150), A1_12)
    for m in (20, 22, 21, 20):
        h.send(*h.at_stop(2, m), after)
    assert h.state().phase == DWELLING
    h.now = h.now + timedelta(seconds=h.cfg.visit_timeout_seconds + 60)
    h.run()
    c = [c for c in h.comparisons if c["stop_sequence"] == 2][0]
    assert c["comparison_status"] == "INCOMPLETE"


def test_first_snapshot_ever_at_a_stop_has_no_baseline_so_in_out_are_unknown_not_zero():
    h = Harness()
    for m in (20, 22, 21, 20):
        h.send(*h.at_stop(2, m), A1_12)
    h.send(*h.at_stop(2, 160), A1_12)
    h.send(*h.at_stop(2, 170), A1_12)
    c = [c for c in h.comparisons if c["stop_sequence"] == 2][0]
    assert c["sensor_in"] is None and c["sensor_out"] is None and c["sensor_total"] == 12


def test_stop_with_a_non_matching_total_is_mismatch_and_matching_total_is_match():
    h = Harness()
    h.visit_stop(1, set(), boarded=set(range(1, 12)))           # 11 occupied vs BMS 12
    c = {c["stop_sequence"]: c for c in h.comparisons}
    assert c[1]["comparison_status"] == "MISMATCH" and c[1]["total_difference"] == -1


def test_bus_that_arrived_but_left_before_the_minimum_dwell_creates_nothing():
    cfg, stops = BmsConfig(), stops_list()
    st = VehicleState(tenant_id=1, vehicle_number="V", device_id=1)
    near = offset_north(TUNI["lat"], TUNI["long"], 20)
    far = offset_north(TUNI["lat"], TUNI["long"], 200)
    advance(st, snap_at(0, *near), stops, cfg)
    advance(st, snap_at(10, *near), stops, cfg)
    assert st.phase == ARRIVED                                 # 2 hits, only 10 s dwell (< 25 s)
    finals = [advance(st, snap_at(s, *far), stops, cfg).final for s in (20, 30, 40)]
    assert finals == [None, None, None] and st.last_completed_sequence == 0