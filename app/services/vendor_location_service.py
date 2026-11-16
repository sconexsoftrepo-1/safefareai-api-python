"""Current position of a vehicle from the GPS vendor's API.

Vendor endpoint  : POST {VENDOR_API_BASE_URL}/monitor/getRealTimeInfo   ("3.1 Load vehicle location information")
Request body     : {"queryType": "0", "queryParams": ["<device name>"]}
                   queryType 0 = by device name (the vendor's "plate"), 1 = by device ID
Response         : {"code": 200, "data": {"list": [{"plate": ..., "terminalNo": ..., "lat": ..., "lon": ..., ...}]}}

Only lat and lon are used. The result is the vehicle's CURRENT position (at the time of the call).
Nothing is raised to the caller: on any problem the function logs a warning and returns None,
so a PRS file is still saved (with empty lat/long) when the vendor is unreachable.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple

from app.config.settings import settings

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
_cache: dict = {}        # identifier -> (expires_at, (lat, lon) | None)


def _build_request(identifier: str) -> urllib.request.Request:
    url = settings.VENDOR_API_BASE_URL.rstrip("/") + "/" + settings.VENDOR_API_PATH.lstrip("/")

    body = json.dumps({
        "queryType": str(settings.VENDOR_QUERY_TYPE),
        "queryParams": [identifier],
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}

    if settings.VENDOR_API_HEADERS:
        headers.update(json.loads(settings.VENDOR_API_HEADERS))

    return urllib.request.Request(url, data=body, headers=headers, method="POST")


def parse_location(payload: dict, identifier: str) -> Optional[Tuple[float, float]]:
    """(lat, lon) from a getRealTimeInfo response, or None if there is no usable position."""

    if not isinstance(payload, dict) or payload.get("code") != 200:
        logger.warning("Vendor API returned code=%s msg=%s", payload.get("code"), payload.get("msg"))
        return None

    items = ((payload.get("data") or {}).get("list")) or []

    if not items:
        logger.warning("Vendor API has no device for '%s'", identifier)
        return None

    # Prefer the entry whose plate / terminalNo equals what we asked for.
    item = next(
        (i for i in items if identifier in (str(i.get("plate")), str(i.get("terminalNo")))),
        items[0],
    )

    lat, lon = item.get("lat"), item.get("lon")

    # 0 / 0 or no value means the device has no position (never online, no GPS fix).
    if lat is None or lon is None or (float(lat) == 0 and float(lon) == 0):
        logger.warning("Vendor API has no position for '%s' (state: %s)", identifier, item.get("formatTime"))
        return None

    return float(lat), float(lon)


def get_vehicle_location(vehicle_number: str, device_id) -> Optional[Tuple[float, float]]:
    """
    (lat, lon) for a vehicle, or None.

    VENDOR_QUERY_TYPE=0 -> asks by device name, using vehicles.vehicle_number
    VENDOR_QUERY_TYPE=1 -> asks by device ID,   using vehicles.device_id
    """

    if not settings.VENDOR_API_BASE_URL:
        logger.warning("VENDOR_API_BASE_URL is not set; PRS lat/long left empty.")
        return None

    identifier = str(device_id if settings.VENDOR_QUERY_TYPE == 1 else vehicle_number or "").strip()

    if not identifier or identifier == "None":
        logger.warning("No identifier to ask the vendor API for (vehicle %s).", vehicle_number)
        return None

    now = time.time()

    with _cache_lock:
        cached = _cache.get(identifier)

        if cached and cached[0] > now:
            return cached[1]

    try:
        request = _build_request(identifier)

        with urllib.request.urlopen(request, timeout=settings.VENDOR_API_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))

        location = parse_location(payload, identifier)

    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        logger.warning("Vendor API call failed for '%s': %s", identifier, error)
        return None

    with _cache_lock:
        _cache[identifier] = (now + settings.VENDOR_LOCATION_CACHE_SECONDS, location)

    return location