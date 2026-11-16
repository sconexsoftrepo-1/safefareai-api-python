"""GPS helpers for BMS stop matching (pure functions, no I/O).

Distance is the great-circle (haversine) distance in metres using BOTH latitude and longitude - the same
quantity SQL Server's geography::Point(lat, long, 4326).STDistance() returns, to well under a metre at the
50-70 m scale used here. Exact lat = lat and long = long matching is never used.
"""
from __future__ import annotations

import math
from typing import Optional

EARTH_RADIUS_M = 6_371_008.8


def valid_gps(lat: Optional[float], lon: Optional[float]) -> bool:
    """True for a usable fix: numbers, in range, and not the (0, 0) 'no fix' value."""
    try:
        la, lo = float(lat), float(lon)          # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if math.isnan(la) or math.isnan(lo) or math.isinf(la) or math.isinf(lo):
        return False
    if not (-90.0 <= la <= 90.0 and -180.0 <= lo <= 180.0):
        return False
    return not (la == 0.0 and lo == 0.0)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two lat/long points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))
