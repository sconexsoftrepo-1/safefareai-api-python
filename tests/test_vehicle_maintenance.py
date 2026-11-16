"""API + scheduler tests (in-memory doubles, no database).

Rules: Fleet Owner creates the schedule (previous + window = expected) and can only view. The Driver alone
completes (done_date; next previous = done_date, next expected = done_date + window) and postpones (date + reason).
Reminders go to the driver. The postponed date is NULL until the driver postpones.

Timeline used throughout: previous maintenance 30 Sep, 30-day window -> expected 30 Oct.
    15 Oct  reminder_15d        23 Oct  reminder_7d (1 week)
    27/28/29 Oct  action_3d/2d/1d (completion check)      30 Oct  due_today (postpone with a reason)
"""
from datetime import date

import pytest

from tests.conftest import ADMIN, DRIVER, DRIVER_2, OWNER, OWNER_T2, T1, T2, Env, create_body

V = "/api/vehicle-maintenance"
VEHICLE = "AP31Z0044"
D = date


def row(env, vehicle=VEHICLE):
    rows = [r for r in env.repo.rows if r.vehicle_number == vehicle]
    assert len(rows) == 1
    return rows[0]


def run_day(env, day):
    env.clock.today = day
    env.scheduler.run_once()


def created(env):
    assert env.client.post(V, json=create_body()).status_code == 201
    env.sender.clear()


def postpone(env, user, new_date, reason="Vehicle in workshop", path="postpone", **extra):
    body = {"postponed_date": new_date, **extra}
    if reason is not None:
        body["reason"] = reason
    return env.as_(user).patch(f"{V}/{VEHICLE}/{path}", json=body)


def complete(env, user, done, **extra):
    return env.as_(user).post(f"{V}/{VEHICLE}/complete", json={"done_date": done, **extra})


# ---------------------------------------------------------------- create / expected date
def test_create_calculates_expected_date(env):
    r = env.client.post(V, json=create_body())
    assert r.status_code == 201, r.json()
    d = r.json()["data"]
    assert d["expected_vehicle_maintenance_date"] == "2026-10-30"      # previous + 30
    assert d["status"] == "pending" and d["postponed_date"] is None and d["due_date"] == "2026-10-30"
    assert d["device_id"] == 1215 and d["tenant_id"] == T1
    assert [s["date"] for s in d["reminder_schedule"]] == [
        "2026-10-15", "2026-10-23", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"]


def test_create_rules(env):
    assert env.as_(DRIVER).post(V, json=create_body()).status_code == 403
    assert env.as_(ADMIN).post(V, json=create_body()).status_code == 403
    assert env.as_(OWNER).post(V, json={**create_body(), "tenant_id": T2}).status_code == 400
    assert env.client.post(V, json=create_body(vehicle_number="NOPE")).status_code == 404
    assert env.client.post(V, json=create_body(vehicle_number="TS09AB1234")).status_code == 404   # other tenant
    assert env.client.post(V, json=create_body(previous_vehicle_maintenance_date="30-09-2026")).status_code == 400
    assert env.repo.rows == []
    assert env.client.post(V, json=create_body()).status_code == 201
    assert env.client.post(V, json=create_body()).status_code == 409          # one current cycle per vehicle


# ---------------------------------------------------------------- 15 / 7 / 3 / 2 / 1 / 0 day alerts
@pytest.mark.parametrize("day,kind", [
    (D(2026, 10, 15), "reminder_15d"),
    (D(2026, 10, 23), "reminder_7d"),
    (D(2026, 10, 27), "action_3d"),
    (D(2026, 10, 28), "action_2d"),
    (D(2026, 10, 29), "action_1d"),
    (D(2026, 10, 30), "due_today"),
])
def test_alert_on_each_reminder_day(env, day, kind):
    created(env)
    run_day(env, day)
    assert env.sender.kinds() == [kind]                                    # the driver only
    assert {n.recipient.role for n in env.sender.sent} == {"driver"}
    env.scheduler.run_once()                                               # same day again: deduplicated
    assert len(env.sender.sent) == 1


def test_no_alert_on_other_days(env):
    created(env)
    for d in [D(2026, 10, n) for n in (1, 14, 16, 22, 24, 25, 26)]:
        run_day(env, d)
    assert env.sender.sent == []


@pytest.mark.parametrize("day", [D(2026, 10, 27), D(2026, 10, 28), D(2026, 10, 29)])
def test_last_three_days_check_completion_and_notify_if_not_done(env, day):
    created(env)
    run_day(env, day)
    assert "not completed yet" in env.sender.sent[0].message


def test_final_day_asks_to_complete_or_postpone_with_a_reason(env):
    created(env)
    run_day(env, D(2026, 10, 30))
    msg = env.sender.sent[0].message
    assert "due today" in msg and "postpone" in msg and "reason" in msg


def test_no_completion_check_once_completed(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    assert complete(env, DRIVER, "2026-10-24").status_code == 200
    env.sender.clear()
    for d in (D(2026, 10, 27), D(2026, 10, 28), D(2026, 10, 29), D(2026, 10, 30)):
        run_day(env, d)
    assert env.sender.sent == []


def test_driver_is_alerted_every_day_from_the_due_date_until_they_act(env):
    created(env)
    env.sender.clear()
    for n in range(0, 8):                                   # 30 Oct (due) ... 6 Nov (7 days overdue)
        day = D.fromordinal(D(2026, 10, 30).toordinal() + n)
        env.sender.clear()
        run_day(env, day)
        env.scheduler.run_once()                            # same day again: still only one alert
        assert len(env.sender.sent) == 1, day
        assert env.sender.sent[0].recipient.role == "driver"
        assert env.sender.kinds() == ["due_today" if n == 0 else "overdue"]
    assert row(env).status == "overdue"
    assert "postpone" in env.sender.sent[0].message and "reason" in env.sender.sent[0].message


def test_daily_alerts_stop_once_the_driver_postpones_or_completes(env):
    created(env)
    run_day(env, D(2026, 11, 2))
    postpone(env, DRIVER, "2026-11-10")
    env.sender.clear()
    run_day(env, D(2026, 11, 4))
    assert env.sender.sent == []                            # not overdue any more: due 10 Nov, nothing scheduled today
    env.clock.today = D(2026, 11, 12)
    complete(env, DRIVER, "2026-11-12")
    env.sender.clear()
    run_day(env, D(2026, 11, 13))
    assert env.sender.sent == []


# ---------------------------------------------------------------- postpone: separate table + alert
def test_postponed_date_is_null_until_the_driver_postpones(env):
    created(env)
    d = env.client.get(f"{V}/{VEHICLE}").json()["data"]
    assert d["postponed_date"] is None and d["postponed_reason"] is None and d["due_date"] == "2026-10-30"
    assert env.repo.postponements == []


def test_postpone_is_stored_in_its_own_table_and_vehicle_maintenance_dates_are_kept(env):
    created(env)
    before = row(env).__dict__.copy()
    env.clock.today = D(2026, 10, 30)
    r = postpone(env, DRIVER, "2026-11-10", "Vehicle unavailable")
    assert r.status_code == 200, r.json()
    d = r.json()["data"]
    assert d["expected_vehicle_maintenance_date"] == "2026-10-30"          # unchanged
    assert d["postponed_date"] == "2026-11-10" and d["due_date"] == "2026-11-10"
    assert d["postponed_reason"] == "Vehicle unavailable" and d["postponed_by"] == "driver-1"
    assert d["status"] == "pending" and d["days_until_due"] == 11
    h = env.repo.postponements
    assert len(h) == 1 and h[0]["postponed_date"] == D(2026, 11, 10) and h[0]["reason"] == "Vehicle unavailable"
    assert h[0]["expected_date"] == D(2026, 10, 30) and h[0]["cycle_previous_date"] == D(2026, 9, 30)
    after = row(env)
    for col in ("previous_vehicle_maintenance_date", "maintenance_time_window", "expected_vehicle_maintenance_date",
                "done_date", "reason"):
        assert getattr(after, col) == before[col], col


def test_postpone_alert_goes_to_the_vehicles_driver_only_naming_who_changed_it(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-10", "Vehicle unavailable")
    sent = [n for n in env.sender.sent if n.kind == "postponed"]
    assert [(n.recipient.role, n.recipient.user_id) for n in sent] == [("driver", "driver-1")]
    msg = sent[0].message
    assert "Driver driver-1" in msg and "10 Nov 2026" in msg and "30 Oct 2026" in msg and "Vehicle unavailable" in msg
    assert sent[0].data["changed_by"] == "Driver driver-1" and sent[0].data["postponed_date"] == "2026-11-10"


def test_fleet_owner_is_only_notified_when_switched_on(env):
    env.notifications._notify_owner = True
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-10")
    assert {n.recipient.role for n in env.sender.sent if n.kind == "postponed"} == {"fleet_owner", "driver"}


def test_reason_is_required_to_postpone(env):
    created(env)
    assert postpone(env, DRIVER, "2026-11-10", reason=None).status_code == 400
    assert postpone(env, DRIVER, "2026-11-10", reason="   ").status_code == 400
    assert env.repo.postponements == []


def test_reminders_follow_the_postponed_date_and_old_date_stays_silent(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-20")
    env.sender.clear()
    run_day(env, D(2026, 10, 31))
    run_day(env, D(2026, 11, 4))
    assert env.sender.sent == []
    for day, kind in {D(2026, 11, 5): "reminder_15d", D(2026, 11, 13): "reminder_7d", D(2026, 11, 17): "action_3d",
                      D(2026, 11, 19): "action_1d", D(2026, 11, 20): "due_today"}.items():
        env.sender.clear()
        run_day(env, day)
        assert env.sender.kinds() == [kind], day
        assert env.sender.sent[0].recipient.role == "driver"
    assert env.client.get(f"{V}/{VEHICLE}").json()["data"]["status"] == "pending"


def test_postponed_vehicle_is_not_overdue_until_postponed_date_passes(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-10")
    env.clock.today = D(2026, 11, 5)
    assert env.client.get(f"{V}/{VEHICLE}").json()["data"]["status"] == "pending"
    run_day(env, D(2026, 11, 5))
    assert row(env).status == "pending"
    env.clock.today = D(2026, 11, 11)
    assert env.client.get(f"{V}/{VEHICLE}").json()["data"]["status"] == "overdue"


def test_postpone_that_lands_on_a_check_day_alerts_the_driver_immediately(env):
    created(env)
    env.clock.today = D(2026, 10, 29)
    postpone(env, DRIVER, "2026-11-12")
    assert set(env.sender.kinds()) == {"postponed"}
    env.sender.clear()
    postpone(env, DRIVER, "2026-11-01")                     # now 3 days away
    assert "action_3d" in env.sender.kinds()


def test_postponing_to_the_same_date_again_adds_nothing(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    assert postpone(env, DRIVER, "2026-11-10").status_code == 200
    env.sender.clear()
    assert postpone(env, DRIVER, "2026-11-10", "again").status_code == 200
    assert env.sender.sent == [] and len(env.repo.postponements) == 1


def test_postpone_can_be_changed_again_and_history_is_kept(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-10", "first")
    env.sender.clear()
    postpone(env, DRIVER, "2026-11-15", "second")
    msg = [n for n in env.sender.sent if n.kind == "postponed"][0].message
    assert "10 Nov 2026" in msg and "15 Nov 2026" in msg
    d = env.client.get(f"{V}/{VEHICLE}").json()["data"]
    assert d["postponed_date"] == "2026-11-15" and d["postponed_reason"] == "second"
    assert [h["postponed_date"] for h in env.repo.postponements] == [D(2026, 11, 10), D(2026, 11, 15)]


@pytest.mark.parametrize("new_date,code", [("2026-10-26", 400), ("2026-10-30", 400), ("2026-10-31", 200)])
def test_postponed_date_must_be_after_expected_and_not_in_the_past(env, new_date, code):
    created(env)
    env.clock.today = D(2026, 10, 27)
    assert postpone(env, DRIVER, new_date).status_code == code


def test_postponed_date_not_in_the_past(env):
    created(env)
    env.clock.today = D(2026, 11, 5)
    assert postpone(env, DRIVER, "2026-11-04").status_code == 400
    assert env.repo.postponements == []


def test_only_the_assigned_driver_can_postpone(env):
    created(env)
    assert postpone(env, OWNER, "2026-11-10").status_code == 403
    assert postpone(env, ADMIN, "2026-11-10").status_code == 403
    assert postpone(env, DRIVER_2, "2026-11-10").status_code == 403           # not their vehicle
    assert postpone(env, OWNER_T2, "2026-11-10").status_code == 403
    env.service._driver_can_postpone = False
    assert postpone(env, DRIVER, "2026-11-10").status_code == 403
    assert env.repo.postponements == []
    env.service._driver_can_postpone = True
    assert postpone(env, DRIVER, "2026-11-10").status_code == 200


def test_old_expected_date_route_and_field_still_work(env):
    created(env)
    r = env.as_(DRIVER).patch(f"{V}/{VEHICLE}/expected-date",
                              json={"expected_vehicle_maintenance_date": "2026-11-10", "reason": "workshop"})
    assert r.status_code == 200
    assert row(env).expected_vehicle_maintenance_date == D(2026, 10, 30)
    assert env.repo.postponements[0]["postponed_date"] == D(2026, 11, 10)


def test_postpone_rejects_unknown_fields_and_bad_dates(env):
    created(env)
    assert postpone(env, DRIVER, "10-11-2026").status_code == 400
    assert postpone(env, DRIVER, "2026-11-10", tenant_id=T2).status_code == 400
    assert env.as_(DRIVER).patch(f"{V}/{VEHICLE}/postpone", json={}).status_code == 400


# ---------------------------------------------------------------- completion (driver only)
def test_driver_completes_previous_is_done_date_and_expected_is_done_plus_window(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    r = complete(env, DRIVER, "2026-10-24", reason="Oil changed")
    assert r.status_code == 200, r.json()
    d = r.json()["data"]
    assert d["status"] == "completed" and d["done_date"] == "2026-10-24"
    assert d["previous_vehicle_maintenance_date"] == "2026-10-24"           # previous = done_date
    assert d["expected_vehicle_maintenance_date"] == "2026-11-23"           # done_date + 30
    assert d["maintenance_time_window"] == 30 and d["postponed_date"] is None
    assert d["completed_cycle"] == {"done_date": "2026-10-24", "was_expected_on": "2026-10-30",
                                    "was_postponed_to": None}
    rec = row(env)
    assert rec.status == "completed" and rec.reason == "Oil changed" and rec.done_date == D(2026, 10, 24)
    assert [(n.recipient.role, n.recipient.user_id) for n in env.sender.sent if n.kind == "completed"] == [("driver", "driver-1")]


def test_completion_works_on_any_day_before_during_or_after_the_due_date(env):
    for done, nxt in (("2026-10-01", "2026-10-31"), ("2026-10-30", "2026-11-29"), ("2026-11-04", "2026-12-04")):
        e = Env()
        created(e)
        e.clock.today = D.fromisoformat(done)
        assert complete(e, DRIVER, done).json()["data"]["expected_vehicle_maintenance_date"] == nxt


def test_fleet_owner_and_admin_cannot_complete_or_edit(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    assert complete(env, OWNER, "2026-10-24").status_code == 403
    assert complete(env, ADMIN, "2026-10-24").status_code == 403
    assert complete(env, DRIVER_2, "2026-10-24").status_code == 403          # not their vehicle
    assert complete(env, OWNER_T2, "2026-10-24").status_code == 403
    assert row(env).done_date is None and row(env).status == "pending"
    # nothing else edits the row either
    assert env.as_(OWNER).put(f"{V}/{VEHICLE}", json={"reason": "x"}).status_code == 405
    assert env.as_(OWNER).patch(f"{V}/{VEHICLE}/maintenance-window", json={"maintenance_time_window": 45}).status_code == 404


def test_driver_cannot_change_the_interval(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    assert complete(env, DRIVER, "2026-10-24", next_maintenance_time_window=45).status_code == 400
    assert row(env).maintenance_time_window == 30


def test_completion_after_postponement_clears_it_and_keeps_history(env):
    created(env)
    env.clock.today = D(2026, 10, 30)
    postpone(env, DRIVER, "2026-11-10", "workshop")
    env.clock.today = D(2026, 11, 8)
    d = complete(env, DRIVER, "2026-11-08").json()["data"]
    assert d["status"] == "completed" and d["previous_vehicle_maintenance_date"] == "2026-11-08"
    assert d["expected_vehicle_maintenance_date"] == "2026-12-08"
    assert d["postponed_date"] is None and d["postponed_reason"] is None and d["due_date"] == "2026-12-08"
    assert d["completed_cycle"]["was_postponed_to"] == "2026-11-10"
    assert row(env).postponed_date is None
    assert len(env.repo.postponements) == 1                                  # history row stays


def test_completed_stays_completed_then_reopens_when_next_window_starts(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    complete(env, DRIVER, "2026-10-24")                                     # next due 23 Nov
    env.sender.clear()
    run_day(env, D(2026, 11, 7))                                           # 16 days before: still completed
    assert row(env).status == "completed" and env.sender.sent == []
    assert env.client.get(V, params={"status": "completed"}).json()["data"]["pagination"]["total"] == 1
    env.clock.today = D(2026, 11, 8)                                       # 15 days before
    assert env.client.get(f"{V}/{VEHICLE}").json()["data"]["status"] == "pending"
    env.scheduler.run_once()
    assert row(env).status == "pending"
    assert env.sender.kinds() == ["reminder_15d"] and env.sender.sent[0].recipient.role == "driver"


def test_next_cycle_can_be_postponed_and_completed_again(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    complete(env, DRIVER, "2026-10-24")
    env.clock.today = D(2026, 11, 24)
    assert postpone(env, DRIVER, "2026-11-30").status_code == 200
    env.clock.today = D(2026, 11, 29)
    assert complete(env, DRIVER, "2026-11-29").json()["data"]["expected_vehicle_maintenance_date"] == "2026-12-29"


def test_cannot_postpone_a_completed_cycle(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    complete(env, DRIVER, "2026-10-24")
    assert postpone(env, DRIVER, "2026-12-30").status_code == 409
    assert env.repo.postponements == []


def test_completion_rules(env):
    created(env)
    env.clock.today = D(2026, 10, 24)
    assert complete(env, DRIVER, "2026-10-24").status_code == 200
    assert complete(env, DRIVER, "2026-10-24").status_code == 409            # duplicate
    assert complete(env, DRIVER, "2026-12-01").status_code == 400            # future
    assert complete(env, DRIVER, "2026-09-01").status_code == 400            # before the previous date
    assert complete(env, DRIVER, "24-10-2026").status_code == 400


def test_failed_update_rolls_back(env):
    created(env)
    env.repo.rows.append(env.repo.rows[0].__class__(**{**env.repo.rows[0].__dict__}))   # corrupt: duplicate row
    r = complete(env, DRIVER, "2026-09-30")
    assert r.status_code == 409
    assert all(x.expected_vehicle_maintenance_date == D(2026, 10, 30) and x.status == "pending" for x in env.repo.rows)


# ---------------------------------------------------------------- reads / isolation
def test_tenant_isolation_and_driver_scope(env):
    created(env)
    env.client.post(V, json=create_body(vehicle_number="AP31Z0055"))
    other = env.as_(OWNER_T2)
    assert other.get(f"{V}/{VEHICLE}").status_code == 404
    assert other.get(V).json()["data"]["pagination"]["total"] == 0
    d = env.as_(DRIVER_2)
    assert d.get(f"{V}/{VEHICLE}").status_code == 403
    assert [i["vehicle_number"] for i in d.get(V).json()["data"]["items"]] == ["AP31Z0055"]
    assert env.as_(ADMIN).get(V).json()["data"]["pagination"]["total"] == 2


def test_list_filters_use_the_postponed_date(env):
    created(env)
    env.clock.today = D(2026, 10, 27)
    postpone(env, DRIVER, "2026-11-10")
    q = env.as_(OWNER).get
    assert q(V, params={"expected_date_from": "2026-11-01"}).json()["data"]["pagination"]["total"] == 1
    assert q(V, params={"expected_date_to": "2026-10-31"}).json()["data"]["pagination"]["total"] == 0
    assert q(V, params={"status": "bogus"}).status_code == 400
    assert q(V, params={"expected_date_from": "01-11-2026"}).status_code == 400


def test_no_tenant_query_parameters_in_api(env):
    paths = env.client.get("/openapi.json").json()["paths"]
    names = {p["name"] for ops in paths.values() for op in ops.values() for p in op.get("parameters", [])}
    assert "tenant_id" not in names
    assert f"{V}/{{vehicle_number}}/postpone" in paths


def test_get_404_envelope(env):
    r = env.client.get(f"{V}/NOPE")
    assert r.status_code == 404
    assert r.json() == {"success": False, "message": "Maintenance schedule not found", "data": None}


# ---------------------------------------------------------------- driver assignment (vehicles.driver_id)
def test_fleet_owner_lists_own_drivers_and_assigns_one_to_a_vehicle(env):
    r = env.as_(OWNER).get(f"{V}/drivers")
    assert [d["driver_id"] for d in r.json()["data"]["drivers"]] == ["driver-1", "driver-2", "driver-3"]
    # the schedule cannot be created until the vehicle has a driver
    r = env.client.post(V, json=create_body(vehicle_number="AP31Z0066"))
    assert r.status_code == 409 and "Assign a driver" in r.json()["message"]
    assert env.repo.rows == []
    # users.id values are integers in the real database
    env.directory.team[(T1, "owner-1")] = [1204, 1205]
    r = env.client.put(f"{V}/AP31Z0066/driver", json={"driver_id": 1205})
    assert r.status_code == 200 and r.json()["data"] == {"vehicle_number": "AP31Z0066", "driver_id": 1205}
    assert env.client.post(V, json=create_body(vehicle_number="AP31Z0066")).status_code == 201
    assert [r.user_id for r in env.directory.driver_recipients(T1, "AP31Z0066")] == [1205]


def test_assigning_moves_the_vehicle_to_one_driver_only(env):
    env.directory.team[(T1, "owner-1")] = [1204, 1205]
    env.client.put(f"{V}/AP31Z0044/driver", json={"driver_id": 1204})
    env.client.put(f"{V}/AP31Z0044/driver", json={"driver_id": 1205})
    assert [r.user_id for r in env.directory.driver_recipients(T1, "AP31Z0044")] == [1205]


def test_assign_driver_validation_and_permissions(env):
    env.directory.team[(T1, "owner-1")] = [1204]
    assert env.client.put(f"{V}/AP31Z0044/driver", json={"driver_id": 9999}).status_code == 400   # not your driver
    assert env.client.put(f"{V}/AP31Z0044/driver", json={"driver_id": "1204"}).status_code == 400
    assert env.client.put(f"{V}/AP31Z0044/driver", json={"driver_id": 1204, "tenant_id": 1}).status_code == 400
    assert env.client.put(f"{V}/NOPE/driver", json={"driver_id": 1204}).status_code == 404
    assert env.as_(OWNER_T2).put(f"{V}/AP31Z0044/driver", json={"driver_id": 1204}).status_code == 404
    for user in (DRIVER, ADMIN):
        assert env.as_(user).put(f"{V}/AP31Z0044/driver", json={"driver_id": 1204}).status_code == 403
        assert env.as_(user).get(f"{V}/drivers").status_code == 403
