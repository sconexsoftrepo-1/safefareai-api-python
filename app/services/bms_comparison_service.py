"""BMS vs Sensor comparison: processes the seat snapshots that the existing PRS ingestion already stored in
dbo.prs_sensor_readings. It never calls the sensor API / S3 itself (no duplicate polling).

Uses ONLY the three existing tables (prs_sensor_readings, bms_stop_details, bms_sensor_comparison).

Per vehicle and cycle:
  1. get the in-memory progress (rebuilt from the comparison table + stored readings after a restart)
  2. read newer rows, group them into 60-seat snapshots, validate them
  3. skip duplicates / out-of-order / stale / future snapshots
  4. feed the rest, oldest first, through the stop tracker (bms_stop_tracker)
  5. a finished stop visit is inserted into dbo.bms_sensor_comparison (idempotent); the in-memory progress moves on
     only after that insert succeeded, so a failure simply retries the same snapshots next cycle.
"""
from __future__ import annotations

import copy
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
from zoneinfo import ZoneInfo

from app.config.bms_config import BmsConfig
from app.database.bms_repository import comparison_row
from app.services.bms_snapshot import SEAT_COUNT, Snapshot, build_snapshots
from app.services.bms_state_store import STATE_STORE, StateStore
from app.services.bms_stop_tracker import (
    COMPLETED, NOT_REACHED, VISIT_PHASES, Stop, StepResult, VehicleState, advance, expire_visit,
)

logger = logging.getLogger(__name__)

FUTURE_TOLERANCE_SECONDS = 60


def _norm_kit(value: Optional[str]) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def local_now(timezone: str) -> datetime:
    """Naive 'now' in the timezone of the sensor timestamps (the CSV timestamps are naive local time)."""
    return datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)


class BmsComparisonService:
    def __init__(self, repo, cfg: BmsConfig, clock: Optional[Callable[[], datetime]] = None,
                 store: Optional[StateStore] = None):
        self.repo = repo
        self.store = store if store is not None else STATE_STORE
        self.cfg = cfg
        self.clock = clock or (lambda: local_now(cfg.timezone))
        self._locks: Dict[Any, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    # ------------------------------------------------------------------ cycle (every BMS_WORKER_INTERVAL_SECONDS)
    def run_cycle(self) -> Dict[str, Any]:
        vehicles = self.repo.list_active_vehicles()
        summary: Dict[str, Any] = {"vehicles": len(vehicles), "results": []}
        if not vehicles:
            return summary
        workers = max(1, min(self.cfg.max_parallel_vehicles, len(vehicles)))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bms-vehicle") as pool:
            summary["results"] = list(pool.map(self._safe_process, vehicles))
        return summary

    def _safe_process(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.process_vehicle(vehicle)
        except Exception as exc:               # one vehicle must never stop the others
            if "42S02" in str(exc) or "Invalid object name" in str(exc):
                self._warn_missing_tables(exc)
                return {"vehicle_number": vehicle.get("vehicle_number"), "error": True, "missing_table": True}
            logger.exception("BMS comparison failed for vehicle %s (tenant %s); will retry next cycle",
                             vehicle.get("vehicle_number"), vehicle.get("tenant_id"))
            return {"vehicle_number": vehicle.get("vehicle_number"), "error": True}

    _last_missing_warning = None

    def _warn_missing_tables(self, exc: Exception) -> None:
        """One short message per minute instead of a stack trace every 10 seconds."""
        import time
        last = BmsComparisonService._last_missing_warning
        if last is None or time.monotonic() - last > 60:
            BmsComparisonService._last_missing_warning = time.monotonic()
            logger.error("BMS comparison cannot run: table %s does not exist in this database.",
                         str(exc).split("Invalid object name")[-1][:60].strip(" '.)"))

    def _lock_for(self, key) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    # ------------------------------------------------------------------ one vehicle
    def process_vehicle(self, vehicle: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        tenant_id, vehicle_number, device_id = vehicle["tenant_id"], vehicle["vehicle_number"], vehicle["device_id"]
        iot_kit = vehicle.get("iot_kit")
        out = {"vehicle_number": vehicle_number, "processed": 0, "skipped": 0, "completed": 0, "busy": False}

        lock = self._lock_for((tenant_id, vehicle_number, device_id))
        if not lock.acquire(blocking=False):             # overlapping run for the same vehicle: skip
            out["busy"] = True
            return out
        try:
            now = now or self.clock()
            stops = self.repo.get_stops(tenant_id, vehicle_number, device_id)
            if not stops:
                return out

            state = self.store.get(tenant_id, vehicle_number, device_id)
            if state is None:
                state = self._rebuild(tenant_id, vehicle_number, device_id, stops, now)
                self.store.put(state)

            self._reset_idle(state, now)
            state = self._consume_snapshots(state, iot_kit, stops, now, out)
            self._expire(state, iot_kit, stops, now, out)
            return out
        finally:
            lock.release()

    # ------------------------------------------------------------------ steps
    def _rebuild(self, tenant_id, vehicle_number, device_id, stops, now) -> VehicleState:
        """Fresh process (or first run): continue after the last stored comparison, re-reading the stored readings."""
        state = VehicleState(tenant_id=tenant_id, vehicle_number=vehicle_number, device_id=device_id)
        last = self.repo.last_comparison(tenant_id, vehicle_number, device_id)
        if not last:
            return state
        seq, ts = last.get("stop_sequence"), last.get("sensor_timestamp")
        final_seq = max(s.sequence for s in stops)
        idle = timedelta(hours=self.cfg.journey_max_idle_hours)
        if seq is not None and seq < final_seq and ts is not None and now - ts <= idle:
            state.last_completed_sequence = seq
        if ts is not None:
            state.resume_from = max(ts, now - timedelta(seconds=2 * self.cfg.visit_timeout_seconds))
            state.replaying = True
        logger.info("BMS %s: progress rebuilt from the database (last stop %s)", vehicle_number, seq)
        return state

    def _reset_idle(self, state: VehicleState, now: datetime) -> None:
        if (state.last_completed_sequence and state.phase not in VISIT_PHASES and state.last_activity_at is not None
                and now - state.last_activity_at > timedelta(hours=self.cfg.journey_max_idle_hours)):
            logger.warning("BMS %s: idle for more than %sh -> a new journey starts at stop 1",
                           state.vehicle_number, self.cfg.journey_max_idle_hours)
            state.last_completed_sequence = 0
            state.phase = NOT_REACHED

    def _consume_snapshots(self, state, iot_kit, stops, now, out) -> VehicleState:
        cfg = self.cfg
        if state.replaying and state.resume_from is not None and state.last_snapshot_ts is None:
            cursor, inclusive = state.resume_from, True
        else:
            cursor = state.last_snapshot_ts or (now - timedelta(seconds=cfg.initial_lookback_seconds))
            inclusive = False
        limit_rows = (cfg.max_snapshots_per_cycle + 1) * SEAT_COUNT
        rows = self.repo.fetch_snapshot_rows(state.tenant_id, state.vehicle_number, cursor, limit_rows, inclusive=inclusive)
        if not rows:
            if state.replaying:
                state.replaying = False
            return state

        snapshots = build_snapshots(rows)
        truncated = len(rows) >= limit_rows and bool(snapshots)
        if truncated:
            snapshots = snapshots[:-1]                    # the last group may have been cut by the row limit
        snapshots = snapshots[: cfg.max_snapshots_per_cycle]

        for snap in snapshots:
            self._check_identity(snap, state, iot_kit)

            if state.last_snapshot_ts is not None and snap.timestamp <= state.last_snapshot_ts:
                logger.info("BMS %s: snapshot %s is a duplicate / out of order (%s <= %s); ignored",
                            state.vehicle_number, snap.key, snap.timestamp, state.last_snapshot_ts)
                out["skipped"] += 1
                continue

            if (snap.timestamp - now).total_seconds() > FUTURE_TOLERANCE_SECONDS:
                logger.warning("BMS %s: snapshot %s has a timestamp in the future (%s); ignored",
                               state.vehicle_number, snap.key, snap.timestamp)
                out["skipped"] += 1
                continue

            if not state.replaying and (now - snap.timestamp).total_seconds() > cfg.max_snapshot_age_seconds:
                # stale: do not use it, but move the cursor on so it is never looked at again
                logger.info("BMS %s: snapshot %s is stale (%s); not used", state.vehicle_number, snap.key, snap.timestamp)
                state.last_snapshot_ts, state.last_snapshot_key = snap.timestamp, snap.key
                out["skipped"] += 1
                continue

            if not snap.seats_valid:
                logger.warning("BMS %s: snapshot %s is not usable: %s", state.vehicle_number, snap.key, "; ".join(snap.problems))

            work = copy.deepcopy(state)                    # committed only after the comparison row is stored
            result = advance(work, snap, stops, cfg)
            self._store_result(work, iot_kit, result)
            state = work
            self.store.put(state)
            out["processed"] += 1
            if result.final is not None:
                out["completed"] += 1
            for event in result.events:
                logger.info("BMS %s: %s", state.vehicle_number, event)

        if state.replaying and not truncated:
            state.replaying = False                        # caught up with the stored readings
        return state

    def _expire(self, state, iot_kit, stops, now, out) -> None:
        work = copy.deepcopy(state)
        result = expire_visit(work, now, stops, self.cfg)
        if result.events:
            self._store_result(work, iot_kit, result)
            self.store.put(work)
            if result.final is not None:
                out["completed"] += 1

    @staticmethod
    def _check_identity(snap: Snapshot, state: VehicleState, iot_kit: Optional[str]) -> None:
        """Wrong vehicle / IoT kit -> the snapshot is not trusted."""
        problem = None
        if snap.tenant_id != state.tenant_id or snap.vehicle_number != state.vehicle_number:
            problem = "snapshot belongs to a different tenant/vehicle"
        elif iot_kit and snap.iot_kit and _norm_kit(snap.iot_kit) != _norm_kit(iot_kit):
            problem = f"snapshot IoT kit {snap.iot_kit} does not match the BMS IoT kit {iot_kit}"
        if problem:
            snap.problems.append(problem)
            snap.seats = None

    # ------------------------------------------------------------------ persistence
    def _store_result(self, state: VehicleState, iot_kit: Optional[str], result: StepResult) -> None:
        """Insert the finished visit (if any) into dbo.bms_sensor_comparison. Raises on failure (state not committed)."""
        final = result.final
        if final is None:
            return
        row = comparison_row(state, final.stop, iot_kit, final)
        inserted = self.repo.insert_comparison(row)
        logger.info("BMS %s: stop %s %s stored (%s new row)", state.vehicle_number, final.stop.sequence,
                    final.comparison_status, inserted)
        if final.last_stop:                                # route finished: the next trip starts again at stop 1
            state.last_completed_sequence = 0


__all__ = ["BmsComparisonService", "local_now", "COMPLETED"]