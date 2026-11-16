"""Configuration of the BMS vs Sensor comparison module.

Every GPS threshold and timing value comes from .env (BMS_*), with the defaults from the project brief.
Kept in its own file so app/config/settings.py is untouched.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, Optional


def _flag(value: Optional[str], default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class BmsConfig:
    enabled: bool = True
    interval_seconds: int = 10               # worker cycle
    entry_radius_m: float = 50.0             # inside this = "at the stop"
    exit_radius_m: float = 70.0              # outside this = "left the stop" (hysteresis against GPS jitter)
    approach_radius_m: float = 300.0         # inside this (but not at the stop) = APPROACHING
    min_dwell_seconds: int = 25              # must stay at the stop this long, otherwise it was a pass-by
    min_consecutive_hits: int = 2            # consecutive readings inside the entry radius needed to ARRIVE
    departure_consecutive_readings: int = 2  # consecutive readings outside the exit radius needed to DEPART
    max_snapshot_age_seconds: int = 300      # older than this (vs. now) = stale, not used
    max_valid_gap_seconds: int = 60          # last valid seat snapshot must be this close to the end of the visit
    initial_lookback_seconds: int = 120      # first run for a vehicle: only look this far back
    max_snapshots_per_cycle: int = 30        # per vehicle per cycle (backlog protection)
    visit_timeout_seconds: int = 900         # no data for this long during a visit -> close it
    journey_max_idle_hours: int = 24         # progress resets (next trip starts at stop 1) after this many idle hours
    allow_skipped_stops: bool = True         # False = strict order: stop N only after stop N-1 is completed
    max_parallel_vehicles: int = 4
    timezone: str = "Asia/Kolkata"           # timezone of the (naive) sensor timestamps
    source_table: str = "dbo.prs_sensor_readings"   # table the worker reads seat rows from (leave as is)

    def validate(self) -> "BmsConfig":
        if self.exit_radius_m < self.entry_radius_m:
            raise ValueError("BMS_EXIT_RADIUS_M must be >= BMS_ENTRY_RADIUS_M")
        if self.approach_radius_m < self.exit_radius_m:
            raise ValueError("BMS_APPROACH_RADIUS_M must be >= BMS_EXIT_RADIUS_M")
        if self.min_consecutive_hits < 1 or self.departure_consecutive_readings < 1:
            raise ValueError("BMS_MIN_CONSECUTIVE_HITS and BMS_DEPARTURE_CONSECUTIVE_READINGS must be >= 1")
        if self.interval_seconds < 1:
            raise ValueError("BMS_WORKER_INTERVAL_SECONDS must be >= 1")
        if not re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?", self.source_table):
            raise ValueError("BMS_SOURCE_TABLE must look like dbo.table_name")
        return self


def load_bms_config(env: Optional[Mapping[str, str]] = None) -> BmsConfig:
    """Read BmsConfig from the environment (or a mapping, for tests)."""
    if env is None:
        from dotenv import load_dotenv      # .env is loaded by app.config.settings too; harmless twice
        load_dotenv()
        env = os.environ

    d = BmsConfig()

    def num(name: str, default, cast):
        raw = env.get(name)
        return default if raw is None or str(raw).strip() == "" else cast(raw)

    return BmsConfig(
        enabled=_flag(env.get("BMS_COMPARISON_ENABLED"), d.enabled),
        interval_seconds=num("BMS_WORKER_INTERVAL_SECONDS", d.interval_seconds, int),
        entry_radius_m=num("BMS_ENTRY_RADIUS_M", d.entry_radius_m, float),
        exit_radius_m=num("BMS_EXIT_RADIUS_M", d.exit_radius_m, float),
        approach_radius_m=num("BMS_APPROACH_RADIUS_M", d.approach_radius_m, float),
        min_dwell_seconds=num("BMS_MIN_DWELL_SECONDS", d.min_dwell_seconds, int),
        min_consecutive_hits=num("BMS_MIN_CONSECUTIVE_HITS", d.min_consecutive_hits, int),
        departure_consecutive_readings=num("BMS_DEPARTURE_CONSECUTIVE_READINGS", d.departure_consecutive_readings, int),
        max_snapshot_age_seconds=num("BMS_MAX_SNAPSHOT_AGE_SECONDS", d.max_snapshot_age_seconds, int),
        max_valid_gap_seconds=num("BMS_MAX_VALID_GAP_SECONDS", d.max_valid_gap_seconds, int),
        initial_lookback_seconds=num("BMS_INITIAL_LOOKBACK_SECONDS", d.initial_lookback_seconds, int),
        max_snapshots_per_cycle=num("BMS_MAX_SNAPSHOTS_PER_CYCLE", d.max_snapshots_per_cycle, int),
        visit_timeout_seconds=num("BMS_VISIT_TIMEOUT_SECONDS", d.visit_timeout_seconds, int),
        journey_max_idle_hours=num("BMS_JOURNEY_MAX_IDLE_HOURS", d.journey_max_idle_hours, int),
        allow_skipped_stops=_flag(env.get("BMS_ALLOW_SKIPPED_STOPS"), d.allow_skipped_stops),
        max_parallel_vehicles=num("BMS_MAX_PARALLEL_VEHICLES", d.max_parallel_vehicles, int),
        timezone=(env.get("TIMEZONE") or d.timezone).strip() or d.timezone,
        source_table=(env.get("BMS_SOURCE_TABLE") or d.source_table).strip(),
    ).validate()