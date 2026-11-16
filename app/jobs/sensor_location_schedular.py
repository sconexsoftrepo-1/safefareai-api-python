"""
vendor_location.py
Fetch lat/long from the vendor API (POST /monitor/getRealTimeInfo) and write them
into dbo.prs_sensor_readings.

Settings (put in .env, never in code):
    VENDOR_API_URL          e.g. https://vendor-host.com        (no trailing /monitor/...)
    VENDOR_API_KEY          the key the vendor gave you
    VENDOR_API_KEY_HEADER   header name for the key, default "Authorization"
    VENDOR_TIMEOUT_SEC      default 10
    SENSOR_LOCATION_MAX_AGE_MIN   only fill readings newer than this, default 5
"""
import json
import logging
import os
import time
import urllib.request
from typing import Optional, Tuple
from app.core.database import get_db_connection

log = logging.getLogger("vendor_location")

PATH = "/monitor/getRealTimeInfo"
_CACHE: dict = {}          # device_id -> (timestamp, (lat, lon) or None)
_CACHE_TTL_SEC = 5


def _cfg(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def fetch_position(device_id: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for one device id, or None if unavailable."""
    now = time.time()
    hit = _CACHE.get(device_id)
    if hit and now - hit[0] < _CACHE_TTL_SEC:
        return hit[1]

    base = (_cfg("VENDOR_API_URL") or "").rstrip("/")
    key = _cfg("VENDOR_API_KEY")
    if not base or not key:
        log.error("VENDOR_API_URL / VENDOR_API_KEY not set")
        return None

    # queryType "1" = query by device ID (terminalNo); "0" = by device name (plate)
    payload = json.dumps({"queryType": "1", "queryParams": [str(device_id)]}).encode()
    req = urllib.request.Request(
        base + PATH,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            _cfg("VENDOR_API_KEY_HEADER", "Authorization"): key,
        },
    )

    result = None
    try:
        with urllib.request.urlopen(req, timeout=float(_cfg("VENDOR_TIMEOUT_SEC", "10"))) as r:
            body = json.loads(r.read().decode())
        if body.get("code") == 200:
            items = (body.get("data") or {}).get("list") or []
            if items:
                it = items[0]
                lat, lon = it.get("lat"), it.get("lon")
                # posState 0 = no positioning; 0,0 means the vendor has no fix
                if lat is not None and lon is not None and it.get("posState") != 0 \
                        and not (float(lat) == 0 and float(lon) == 0):
                    result = (float(lat), float(lon))
        else:
            log.warning("vendor returned code=%s msg=%s", body.get("code"), body.get("msg"))
    except Exception as e:                      # network error, bad JSON, timeout
        log.warning("vendor call failed for %s: %s", device_id, e)

    _CACHE[device_id] = (now, result)
    return result


def fill_missing_locations(conn) -> int:
    """
    Fill lat/long on recent prs_sensor_readings rows that still have NULL.
    `conn` is an open pyodbc connection. Returns number of rows updated.
    Call this from your 5 s scheduler loop, or right after inserting a reading.
    """
    max_age = int(_cfg("SENSOR_LOCATION_MAX_AGE_MIN", "5"))
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.id, v.device_id
            FROM dbo.prs_sensor_readings s
            JOIN dbo.vehicles v
              ON v.tenant_id = s.tenant_id AND v.vehicle_number = s.vehicle_number
            WHERE s.lat IS NULL
              AND s.created_at >= DATEADD(MINUTE, ?, SYSUTCDATETIME())
            """,
            -max_age,
        )
        rows = cur.fetchall()

        updated = 0
        for row_id, device_id in rows:
            pos = fetch_position(str(device_id).strip())
            if not pos:
                continue
            cur.execute(
                "UPDATE dbo.prs_sensor_readings SET lat = ?, [long] = ? "
                "WHERE id = ? AND lat IS NULL",
                pos[0], pos[1], row_id,
            )
            updated += cur.rowcount
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()