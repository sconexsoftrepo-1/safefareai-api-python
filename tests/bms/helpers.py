from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from app.config.bms_config import BmsConfig
from app.services.bms_snapshot import SEAT_IDS

# the five sample stops from the brief (Visakhapatnam -> Ongole)
STOPS = [
    dict(stop_sequence=1, stop_name="Anakapalle APSRTC Bus Station",        lat=17.6863300, long=83.0023400, bms_in=12, bms_out=0, bms_total=12),
    dict(stop_sequence=2, stop_name="Tuni APSRTC Bus Station",              lat=17.3685600, long=82.5432300, bms_in=6,  bms_out=1, bms_total=17),
    dict(stop_sequence=3, stop_name="Rajamahendravaram APSRTC Bus Station", lat=17.0012000, long=81.7897000, bms_in=9,  bms_out=3, bms_total=23),
    dict(stop_sequence=4, stop_name="Vijayawada Pandit Nehru Bus Station",  lat=16.5088038, long=80.6156014, bms_in=7,  bms_out=5, bms_total=25),
    dict(stop_sequence=5, stop_name="Ongole APSRTC Bus Station",            lat=15.5112042, long=80.0418439, bms_in=0,  bms_out=25, bms_total=0),
]

BASE = datetime(2026, 11, 16, 10, 0, 0)
CFG = BmsConfig()          # defaults: entry 50 m, exit 70 m, dwell 25 s, 2 hits, 2 departure readings


def offset_north(lat: float, lon: float, metres: float):
    """A point `metres` north of (lat, lon)."""
    return lat + metres / 111_195.0, lon


def seat_rows(ts: datetime, occupied: Iterable[int], lat: Optional[float], lon: Optional[float], *, tenant=1,
              vehicle="AP31Z0044", kit="IOT-KIT-001", snapshot_id: Optional[str] = None,
              statuses: Optional[Dict[str, str]] = None, skip: Iterable[str] = (), duplicate: Iterable[str] = ()) -> List[dict]:
    """The 60 PRS rows of one sensor response. occupied = seat NUMBERS (1..60)."""
    occ = {f"A{n}" for n in occupied}
    rows = []
    for seat in SEAT_IDS:
        if seat in set(skip):
            continue
        statuses = statuses or {}
        status = statuses[seat] if seat in statuses else ("occupied" if seat in occ else "not_occupied")
        row = dict(tenant_id=tenant, vehicle_number=vehicle, iot_kit=kit, timestamp=ts, lat=lat, long=lon,
                   sensor_data=f"unique_number:{seat},reading:{status}", snapshot_id=snapshot_id)
        rows.append(row)
        if seat in set(duplicate):
            rows.append(dict(row))
    return rows


def metres_between(a, b) -> float:
    from app.services.bms_geo import haversine_m
    return haversine_m(a[0], a[1], b[0], b[1])