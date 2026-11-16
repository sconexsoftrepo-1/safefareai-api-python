"""Group PRS seat rows into complete 60-seat snapshots, validate them, count occupied seats and
find seat transitions. Pure functions, no database access.

One snapshot = the 60 rows (A1..A60) of ONE sensor API response / PRS file. Rows are grouped by
dbo.prs_sensor_readings.snapshot_id (written by the ingestion since migration 003). Older rows without a
snapshot_id fall back to grouping by (tenant, vehicle, iot kit, timestamp).

A snapshot whose seats are not exactly A1..A60, once each, each 'occupied' or 'not_occupied', is NEVER used for a
normal MATCH / MISMATCH result, and a missing / 'no_data' seat is never treated as empty.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.bms_geo import valid_gps

SEAT_COUNT = 60
SEAT_IDS: Tuple[str, ...] = tuple(f"A{i}" for i in range(1, SEAT_COUNT + 1))
_SEAT_SET = frozenset(SEAT_IDS)

OCCUPIED = "occupied"
NOT_OCCUPIED = "not_occupied"
_VALID_STATUS = {OCCUPIED: True, NOT_OCCUPIED: False}


@dataclass
class Snapshot:
    key: str
    tenant_id: Any
    vehicle_number: str
    iot_kit: Optional[str]
    timestamp: datetime
    lat: Optional[float]
    lon: Optional[float]
    seats: Optional[Dict[str, bool]]          # seat id -> occupied; None when the snapshot is not valid
    problems: List[str] = field(default_factory=list)
    row_count: int = 0

    @property
    def seats_valid(self) -> bool:
        return self.seats is not None and not self.problems

    @property
    def gps_valid(self) -> bool:
        return valid_gps(self.lat, self.lon)

    @property
    def occupied_count(self) -> Optional[int]:
        return sum(1 for v in self.seats.values() if v) if self.seats_valid and self.seats else None


def parse_seat_reading(sensor_data: Any) -> Tuple[str, bool]:
    """'unique_number:A1,reading:occupied' -> ('A1', True). Raises ValueError for anything unusable."""
    values: Dict[str, str] = {}
    for item in str(sensor_data or "").split(","):
        if ":" in item:
            key, value = item.split(":", 1)
            values[key.strip().lower()] = value.strip()

    seat = (values.get("unique_number") or values.get("seat_number") or "").upper()
    reading = (values.get("reading") or values.get("seating") or "").lower().replace(" ", "_")

    if seat not in _SEAT_SET:
        raise ValueError(f"invalid seat '{seat}'")
    if reading not in _VALID_STATUS:
        raise ValueError(f"seat {seat} has unusable status '{reading}'")
    return seat, _VALID_STATUS[reading]


def _group_key(row: Dict[str, Any]) -> str:
    snapshot_id = row.get("snapshot_id")
    if snapshot_id is not None and str(snapshot_id).strip():
        return str(snapshot_id).lower()
    ts = row["timestamp"]
    ts_text = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    return f"ts:{row.get('tenant_id')}:{row.get('vehicle_number')}:{row.get('iot_kit')}:{ts_text}"


def _to_float(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def build_snapshot(key: str, rows: List[Dict[str, Any]]) -> Snapshot:
    """Validate the rows of one group and return the Snapshot."""
    problems: List[str] = []
    seats: Dict[str, bool] = {}
    seen: set = set()

    tenants = {r.get("tenant_id") for r in rows}
    vehicles = {r.get("vehicle_number") for r in rows}
    kits = {r.get("iot_kit") for r in rows}
    if len(tenants) > 1 or len(vehicles) > 1 or len(kits) > 1:
        problems.append("rows of different tenant/vehicle/iot kit in one snapshot")

    for row in rows:
        try:
            seat, occupied = parse_seat_reading(row.get("sensor_data"))
        except ValueError as exc:
            problems.append(str(exc))
            continue
        if seat in seen:
            problems.append(f"duplicate seat {seat}")
            continue
        seen.add(seat)
        seats[seat] = occupied

    missing = [s for s in SEAT_IDS if s not in seen]
    if missing:
        shown = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
        problems.append(f"{len(missing)} seat(s) missing ({shown})")

    # position: one vendor position per file; take the first usable one
    lat = lon = None
    for row in rows:
        la, lo = _to_float(row.get("lat")), _to_float(row.get("long"))
        if valid_gps(la, lo):
            lat, lon = la, lo
            break
    if lat is None:                                      # keep the raw value so the problem is visible
        lat, lon = _to_float(rows[0].get("lat")), _to_float(rows[0].get("long"))

    first = rows[0]
    return Snapshot(
        key=key,
        tenant_id=first.get("tenant_id"),
        vehicle_number=first.get("vehicle_number"),
        iot_kit=first.get("iot_kit"),
        timestamp=max(r["timestamp"] for r in rows),
        lat=lat,
        lon=lon,
        seats=seats if not problems else None,
        problems=problems,
        row_count=len(rows),
    )


def build_snapshots(rows: Iterable[Dict[str, Any]]) -> List[Snapshot]:
    """Group rows (any order) into snapshots, oldest first."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(_group_key(row), []).append(row)
    snapshots = [build_snapshot(k, g) for k, g in groups.items()]
    snapshots.sort(key=lambda s: (s.timestamp, s.key))
    return snapshots


# ---- seat state as a 60-char string (stored in dbo.bms_vehicle_state.last_seats) -----------------------------------

def seats_to_string(seats: Dict[str, bool]) -> str:
    return "".join("O" if seats[s] else "N" for s in SEAT_IDS)


def count_occupied_string(seat_string: str) -> int:
    return seat_string.count("O")


def diff_seat_strings(previous: str, current: str) -> Tuple[int, int]:
    """(estimated_in, estimated_out) between two consecutive complete snapshots, seat by seat.

    not_occupied -> occupied = candidate In;  occupied -> not_occupied = candidate Out.
    A passenger moving A1 -> A2 counts as one Out AND one In: these are seat transitions, not exact passenger events.
    """
    if len(previous) != SEAT_COUNT or len(current) != SEAT_COUNT:
        raise ValueError("seat state must be 60 characters")
    seat_in = sum(1 for a, b in zip(previous, current) if a == "N" and b == "O")
    seat_out = sum(1 for a, b in zip(previous, current) if a == "O" and b == "N")
    return seat_in, seat_out
