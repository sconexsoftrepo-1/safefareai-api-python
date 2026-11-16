import pytest

from app.config.bms_config import BmsConfig, load_bms_config
from app.services.bms_geo import haversine_m, valid_gps
from app.services.bms_snapshot import (
    build_snapshots, count_occupied_string, diff_seat_strings, parse_seat_reading, seats_to_string,
)
from tests.bms.helpers import BASE, STOPS, metres_between, offset_north, seat_rows

TUNI = (STOPS[1]["lat"], STOPS[1]["long"])


# ----------------------------------------------------------------------------- GPS
def test_exact_gps_match_is_zero_metres():
    assert haversine_m(*TUNI, *TUNI) == 0


def test_nearby_gps_with_different_lat_and_long_is_close():
    near = (17.36875, 82.54340)                       # both coordinates differ from the BMS stop
    assert near != TUNI
    assert 0 < haversine_m(*TUNI, *near) < 50


def test_tuni_point_30m_north_is_30m():
    p = offset_north(*TUNI, 30)
    assert metres_between(TUNI, p) == pytest.approx(30, abs=0.5)


def test_gps_outside_radius():
    p = offset_north(*TUNI, 120)
    assert haversine_m(*TUNI, *p) > BmsConfig().exit_radius_m


def test_prompt_example_coordinates_are_about_430m_away_not_inside_a_50m_radius():
    # The brief's "nearby" Tuni example (17.3650000, 82.5450000) is NOT inside the default 50 m / 70 m radii.
    d = haversine_m(*TUNI, 17.3650000, 82.5450000)
    assert 400 < d < 470


def test_latitude_range_alone_does_not_confirm_a_match():
    # same latitude band as Tuni, but 100+ km away in longitude
    assert haversine_m(*TUNI, TUNI[0], 83.9) > 100_000


@pytest.mark.parametrize("lat,lon,ok", [
    (17.3, 82.5, True), (0, 0, False), (None, 82.5, False), (17.3, None, False), (91, 82, False), (17, 181, False),
    (float("nan"), 82, False), ("abc", 82, False),
])
def test_valid_gps(lat, lon, ok):
    assert valid_gps(lat, lon) is ok


# ----------------------------------------------------------------------------- config
def test_config_defaults_and_env_override():
    cfg = load_bms_config({})
    assert (cfg.entry_radius_m, cfg.exit_radius_m, cfg.min_dwell_seconds, cfg.min_consecutive_hits) == (50, 70, 25, 2)
    cfg = load_bms_config({"BMS_ENTRY_RADIUS_M": "80", "BMS_EXIT_RADIUS_M": "120", "BMS_APPROACH_RADIUS_M": "600",
                           "BMS_ALLOW_SKIPPED_STOPS": "false", "TIMEZONE": "UTC"})
    assert (cfg.entry_radius_m, cfg.exit_radius_m, cfg.allow_skipped_stops, cfg.timezone) == (80, 120, False, "UTC")


def test_config_rejects_exit_radius_smaller_than_entry():
    with pytest.raises(ValueError):
        load_bms_config({"BMS_ENTRY_RADIUS_M": "100", "BMS_EXIT_RADIUS_M": "50"})


# ----------------------------------------------------------------------------- snapshot validation
def test_all_60_seats_valid_and_counted():
    snap = build_snapshots(seat_rows(BASE, range(1, 18), 17.0, 82.0))[0]
    assert snap.seats_valid and snap.problems == []
    assert len(snap.seats) == 60 and snap.occupied_count == 17


def test_missing_seat_is_never_treated_as_empty():
    snap = build_snapshots(seat_rows(BASE, range(1, 18), 17.0, 82.0, skip=["A60"]))[0]
    assert not snap.seats_valid and snap.occupied_count is None
    assert any("missing" in p for p in snap.problems)


def test_duplicate_seat_makes_snapshot_invalid():
    snap = build_snapshots(seat_rows(BASE, range(1, 5), 17.0, 82.0, duplicate=["A3"]))[0]
    assert not snap.seats_valid and any("duplicate seat A3" in p for p in snap.problems)


@pytest.mark.parametrize("status", ["no_data", "broken", ""])
def test_unusable_status_makes_snapshot_invalid(status):
    snap = build_snapshots(seat_rows(BASE, [], 17.0, 82.0, statuses={"A9": status}))[0]
    assert not snap.seats_valid


def test_status_text_variants_and_seat_parsing():
    assert parse_seat_reading("unique_number:A1,reading:occupied") == ("A1", True)
    assert parse_seat_reading("unique_number:a60, reading:not occupied") == ("A60", False)
    for bad in ("unique_number:A61,reading:occupied", "unique_number:A0,reading:occupied", "garbage", None):
        with pytest.raises(ValueError):
            parse_seat_reading(bad)


def test_rows_group_by_snapshot_id_even_when_timestamps_differ():
    rows = seat_rows(BASE, [1], 17.0, 82.0, snapshot_id="aaaa")
    for i, r in enumerate(rows):
        r["timestamp"] = BASE.replace(second=i % 5)
    snaps = build_snapshots(rows)
    assert len(snaps) == 1 and snaps[0].seats_valid


def test_rows_without_snapshot_id_group_by_vehicle_and_timestamp():
    rows = seat_rows(BASE, [1], 17.0, 82.0) + seat_rows(BASE.replace(second=10), [2], 17.0, 82.0)
    snaps = build_snapshots(rows)
    assert [s.occupied_count for s in snaps] == [1, 1] and snaps[0].timestamp < snaps[1].timestamp


def test_two_vehicles_never_share_a_snapshot():
    rows = seat_rows(BASE, [1], 17.0, 82.0) + seat_rows(BASE, [1, 2], 17.0, 82.0, vehicle="OTHER")
    assert len(build_snapshots(rows)) == 2


def test_invalid_gps_is_flagged_but_seats_still_valid():
    snap = build_snapshots(seat_rows(BASE, [1], None, None))[0]
    assert snap.seats_valid and not snap.gps_valid


# ----------------------------------------------------------------------------- In / Out transitions
def _s(occupied):
    return seats_to_string({f"A{i}": (i in occupied) for i in range(1, 61)})


def test_brief_example_in_2_out_1():
    prev = _s({1, 2})                      # A1, A2 occupied; A3, A4 empty
    cur = _s({1, 3, 4})                    # A1 stays, A2 leaves, A3 and A4 occupied
    assert diff_seat_strings(prev, cur) == (2, 1)


def test_occupied_to_not_occupied_is_out():
    assert diff_seat_strings(_s({5}), _s(set())) == (0, 1)


def test_not_occupied_to_occupied_is_in():
    assert diff_seat_strings(_s(set()), _s({5})) == (1, 0)


def test_no_change_gives_zero():
    assert diff_seat_strings(_s({1, 2}), _s({1, 2})) == (0, 0)


def test_passenger_changing_seats_counts_as_one_in_and_one_out_an_estimate():
    assert diff_seat_strings(_s({1}), _s({2})) == (1, 1)


def test_occupied_count_from_string():
    assert count_occupied_string(_s(set(range(1, 18)))) == 17
