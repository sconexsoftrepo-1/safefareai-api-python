"""Stop arrival / dwell / departure state machine for the BMS vs Sensor comparison (pure logic, no I/O).

Per vehicle phases:
    NOT_REACHED   no eligible stop nearby
    APPROACHING   inside the approach radius of an eligible stop, not yet at it
    STOP_CANDIDATE  inside the ENTRY radius, fewer than min_consecutive_hits readings so far
    ARRIVED       min_consecutive_hits consecutive readings inside the entry radius
    DWELLING      stayed at the stop for min_dwell_seconds
    DEPARTED      left the EXIT radius (min departure readings) after dwelling -> visit is finalised
    COMPLETED     the stop comparison was produced (the next snapshot moves on)

Rules:
  * distance = haversine of latitude AND longitude, never exact lat/long equality
  * entry radius < exit radius: readings between the two keep the current state (no flapping at the boundary)
  * a bus that leaves before dwelling long enough "passed without stopping" -> nothing is recorded
  * only stops after the last completed one are eligible (strict order when allow_skipped_stops is False);
    two eligible stops inside the entry radius = ambiguous -> nothing is selected
  * every valid seat snapshot refreshes the baseline (last_seats) even when it is not used for a stop, so the
    previous complete seat state is never lost
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.bms_config import BmsConfig
from app.services.bms_geo import haversine_m
from app.services.bms_snapshot import Snapshot, diff_seat_strings, seats_to_string

NOT_REACHED = "NOT_REACHED"
APPROACHING = "APPROACHING"
STOP_CANDIDATE = "STOP_CANDIDATE"
ARRIVED = "ARRIVED"
DWELLING = "DWELLING"
DEPARTED = "DEPARTED"
COMPLETED = "COMPLETED"

VISIT_PHASES = (STOP_CANDIDATE, ARRIVED, DWELLING)

MATCH = "MATCH"
MISMATCH = "MISMATCH"
INCOMPLETE = "INCOMPLETE"


@dataclass
class Stop:
    id: int
    sequence: int
    name: str
    lat: float
    lon: float
    bms_in: int
    bms_out: int
    bms_total: int


@dataclass
class VehicleState:
    """Everything that must survive a restart (persisted in dbo.bms_vehicle_state)."""
    tenant_id: int
    vehicle_number: str
    device_id: int
    journey_id: Optional[int] = None
    last_completed_sequence: int = 0
    phase: str = NOT_REACHED
    current_stop_sequence: Optional[int] = None
    hit_count: int = 0
    outside_count: int = 0
    first_hit_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    last_in_area_at: Optional[datetime] = None
    visit_in: int = 0
    visit_out: int = 0
    visit_valid_count: int = 0
    visit_invalid_count: int = 0
    visit_baseline_missing: bool = False
    visit_last_total: Optional[int] = None
    visit_last_valid_ts: Optional[datetime] = None
    visit_min_dist: Optional[float] = None
    visit_lat: Optional[float] = None
    visit_long: Optional[float] = None
    last_seats: Optional[str] = None
    last_snapshot_ts: Optional[datetime] = None
    last_snapshot_key: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    version: int = 0
    persisted: bool = False
    resume_from: Optional[datetime] = None   # after a restart: re-read stored snapshots from here (inclusive)
    replaying: bool = False                  # True while catching up on stored (not live) snapshots

    def reset_visit(self) -> None:
        self.current_stop_sequence = None
        self.hit_count = 0
        self.outside_count = 0
        self.first_hit_at = None
        self.arrived_at = None
        self.last_in_area_at = None
        self.visit_in = 0
        self.visit_out = 0
        self.visit_valid_count = 0
        self.visit_invalid_count = 0
        self.visit_baseline_missing = False
        self.visit_last_total = None
        self.visit_last_valid_ts = None
        self.visit_min_dist = None
        self.visit_lat = None
        self.visit_long = None


@dataclass
class FinalVisit:
    """The result of one confirmed stop visit - becomes one row of dbo.bms_sensor_comparison."""
    stop: Stop
    comparison_status: str
    sensor_in: Optional[int]
    sensor_out: Optional[int]
    sensor_total: Optional[int]
    total_difference: Optional[int]
    sensor_lat: Optional[float]
    sensor_long: Optional[float]
    sensor_timestamp: Optional[datetime]
    incomplete_reason: Optional[str] = None
    skipped_sequences: List[int] = field(default_factory=list)
    last_stop: bool = False          # this was the last stop of the route -> the journey is finished


@dataclass
class StepResult:
    events: List[str] = field(default_factory=list)
    final: Optional[FinalVisit] = None


def _dist(snap: Snapshot, stop: Stop) -> float:
    return haversine_m(snap.lat, snap.lon, stop.lat, stop.lon)       # type: ignore[arg-type]


def _accumulate(state: VehicleState, snap: Snapshot, transition) -> None:
    """Add this snapshot's seat transitions to the current visit."""
    if snap.seats_valid:
        state.visit_valid_count += 1
        state.visit_last_total = snap.occupied_count
        state.visit_last_valid_ts = snap.timestamp
        if transition is not None:
            state.visit_in += transition[0]
            state.visit_out += transition[1]
    else:
        state.visit_invalid_count += 1


def build_final(state: VehicleState, stop: Stop, stops: List[Stop], cfg: BmsConfig, forced_reason: Optional[str] = None) -> FinalVisit:
    """Turn the accumulated visit into a FinalVisit (MATCH / MISMATCH / INCOMPLETE)."""
    reason = forced_reason
    if reason is None and state.visit_valid_count == 0:
        reason = "no complete valid seat snapshot during the stop visit"
    if reason is None and state.last_in_area_at is not None and state.visit_last_valid_ts is not None:
        gap = (state.last_in_area_at - state.visit_last_valid_ts).total_seconds()
        if gap > cfg.max_valid_gap_seconds:
            reason = f"last valid seat snapshot is {int(gap)}s older than the end of the visit"

    last_sequence = max(s.sequence for s in stops)
    skipped = [s.sequence for s in stops if state.last_completed_sequence < s.sequence < stop.sequence]

    have_total = state.visit_last_total is not None
    # In / Out are ESTIMATES from seat transitions; they are unknown if no baseline snapshot existed when the visit began
    estimates_known = have_total and not state.visit_baseline_missing
    if reason is None and have_total and not estimates_known:
        reason = "no earlier seat snapshot, so sensor In / Out cannot be compared"
    status_incomplete = reason is not None or not have_total

    sensor_total = state.visit_last_total          # None when there was no valid snapshot
    return FinalVisit(
        stop=stop,
        comparison_status=INCOMPLETE if status_incomplete else (
            MATCH if (sensor_total == stop.bms_total and state.visit_in == stop.bms_in and state.visit_out == stop.bms_out)
            else MISMATCH),    # MATCH needs In, Out AND Total to be equal
        sensor_in=state.visit_in if estimates_known else None,
        sensor_out=state.visit_out if estimates_known else None,
        sensor_total=sensor_total,
        total_difference=None if (status_incomplete or sensor_total is None) else sensor_total - stop.bms_total,
        sensor_lat=state.visit_lat,
        sensor_long=state.visit_long,
        sensor_timestamp=state.visit_last_valid_ts or state.last_in_area_at,   # identifies the visit (idempotent insert)
        incomplete_reason=reason if reason else (None if have_total else "no sensor total"),
        skipped_sequences=skipped,
        last_stop=stop.sequence == last_sequence,
    )


def _complete(state: VehicleState, stop: Stop, stops: List[Stop], cfg: BmsConfig, result: StepResult,
              forced_reason: Optional[str] = None) -> None:
    final = build_final(state, stop, stops, cfg, forced_reason)
    result.final = final
    result.events.append(f"COMPLETED stop {stop.sequence} {final.comparison_status}")
    state.last_completed_sequence = stop.sequence
    state.reset_visit()
    state.phase = COMPLETED


def advance(state: VehicleState, snap: Snapshot, stops: List[Stop], cfg: BmsConfig) -> StepResult:
    """Feed ONE snapshot (already de-duplicated / ordered / fresh) through the state machine.

    Mutates `state`. The caller persists the new state, and the FinalVisit if there is one, in one transaction.
    """
    result = StepResult()
    stops_by_seq: Dict[int, Stop] = {s.sequence: s for s in stops}

    current = seats_to_string(snap.seats) if snap.seats_valid and snap.seats else None
    transition = None
    if current is not None and state.last_seats is not None:
        transition = diff_seat_strings(state.last_seats, current)

    if state.phase in VISIT_PHASES and state.current_stop_sequence in stops_by_seq:
        _step_in_visit(state, snap, stops, stops_by_seq[state.current_stop_sequence], cfg, transition, result)
    else:
        if state.phase in VISIT_PHASES:                       # stop was deleted while a visit was open
            result.events.append("VISIT_DROPPED_UNKNOWN_STOP")
            state.reset_visit()
            state.phase = NOT_REACHED
        _step_search(state, snap, stops, cfg, transition, result)

    # baseline for the next transition: every complete valid snapshot, whatever the GPS says
    if current is not None:
        state.last_seats = current
    state.last_snapshot_ts = snap.timestamp
    state.last_snapshot_key = snap.key
    state.last_activity_at = snap.timestamp
    return result


def _eligible(state: VehicleState, stops: List[Stop], cfg: BmsConfig) -> List[Stop]:
    after = [s for s in stops if s.sequence > state.last_completed_sequence]
    if cfg.allow_skipped_stops:
        return after
    return [s for s in after if s.sequence == state.last_completed_sequence + 1]


def _step_search(state, snap, stops, cfg, transition, result) -> None:
    if not snap.gps_valid:
        result.events.append("GPS_INVALID_SKIPPED")
        state.phase = NOT_REACHED
        return

    ranked = sorted(((_dist(snap, s), s) for s in _eligible(state, stops, cfg)), key=lambda t: t[0])
    if not ranked:
        state.phase = NOT_REACHED
        return

    inside = [(d, s) for d, s in ranked if d <= cfg.entry_radius_m]
    if len(inside) > 1:
        result.events.append("AMBIGUOUS_STOP_SKIPPED")        # two stops overlap here: do not guess
        state.phase = NOT_REACHED
        return

    if inside:
        dist, stop = inside[0]
        state.reset_visit()
        state.current_stop_sequence = stop.sequence
        state.phase = STOP_CANDIDATE
        state.hit_count = 1
        state.first_hit_at = snap.timestamp
        state.last_in_area_at = snap.timestamp
        state.visit_min_dist, state.visit_lat, state.visit_long = dist, snap.lat, snap.lon
        state.visit_baseline_missing = state.last_seats is None
        _accumulate(state, snap, transition)
        result.events.append(f"STOP_CANDIDATE {stop.sequence}")
        _promote(state, snap, cfg, result)
        return

    state.current_stop_sequence = None
    if ranked[0][0] <= cfg.approach_radius_m:
        state.phase = APPROACHING
        result.events.append(f"APPROACHING {ranked[0][1].sequence}")
    else:
        state.phase = NOT_REACHED


def _promote(state: VehicleState, snap: Snapshot, cfg: BmsConfig, result: StepResult) -> None:
    """STOP_CANDIDATE -> ARRIVED -> DWELLING as the counters allow."""
    if state.phase == STOP_CANDIDATE and state.hit_count >= cfg.min_consecutive_hits:
        state.phase = ARRIVED
        state.arrived_at = snap.timestamp
        result.events.append(f"ARRIVED {state.current_stop_sequence}")
    if state.phase == ARRIVED and state.first_hit_at is not None:
        if (snap.timestamp - state.first_hit_at).total_seconds() >= cfg.min_dwell_seconds:
            state.phase = DWELLING
            result.events.append(f"DWELLING {state.current_stop_sequence}")


def _step_in_visit(state, snap, stops, stop, cfg, transition, result) -> None:
    if not snap.gps_valid:
        # position unknown: keep the visit alive, keep counting seat changes, never count it as a departure
        result.events.append("GPS_INVALID_IN_VISIT")
        _accumulate(state, snap, transition)
        return

    dist = _dist(snap, stop)

    if dist <= cfg.exit_radius_m:
        state.outside_count = 0
        state.last_in_area_at = snap.timestamp
        if state.visit_min_dist is None or dist < state.visit_min_dist:
            state.visit_min_dist, state.visit_lat, state.visit_long = dist, snap.lat, snap.lon
        _accumulate(state, snap, transition)
        # readings between the entry and exit radius hold the state (no hit, no reset): boundary jitter is harmless
        if state.phase == STOP_CANDIDATE and dist <= cfg.entry_radius_m:
            state.hit_count += 1
        _promote(state, snap, cfg, result)
        return

    state.outside_count += 1
    if state.outside_count < cfg.departure_consecutive_readings:
        return                                        # maybe a GPS glitch: wait for the next reading

    if state.phase == DWELLING:
        result.events.append(f"DEPARTED {stop.sequence}")
        _complete(state, stop, stops, cfg, result)
    else:
        result.events.append(f"PASSED_WITHOUT_STOPPING {stop.sequence}")
        state.reset_visit()
        state.phase = NOT_REACHED


def expire_visit(state: VehicleState, now: datetime, stops: List[Stop], cfg: BmsConfig) -> StepResult:
    """No data for BMS_VISIT_TIMEOUT_SECONDS while a visit is open (device offline, bus left unseen).

    A visit that already dwelled is closed as INCOMPLETE (we never saw the departure); a shorter one is dropped.
    """
    result = StepResult()
    if state.phase not in VISIT_PHASES or state.last_snapshot_ts is None:
        return result
    if (now - state.last_snapshot_ts).total_seconds() <= cfg.visit_timeout_seconds:
        return result

    stops_by_seq = {s.sequence: s for s in stops}
    stop = stops_by_seq.get(state.current_stop_sequence)
    if stop is not None and state.phase == DWELLING:
        _complete(state, stop, stops, cfg, result, forced_reason="no sensor data until the visit timed out")
    else:
        result.events.append("VISIT_TIMED_OUT_DROPPED")
        state.reset_visit()
        state.phase = NOT_REACHED
    return result