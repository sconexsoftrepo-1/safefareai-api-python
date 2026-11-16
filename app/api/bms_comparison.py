"""GET endpoints for the BMS vs Sensor comparison (read-only; the frontend only displays what is stored).

    GET /api/bms/stops[?vehicle_number=...]                BMS stop details (In / Out / Total per stop)
    GET /api/bms-sensor/comparisons[?vehicle_number=...]   BMS vs Sensor comparison, newest first, plus a "summary"
                                                           object with the KPI numbers of the dashboard

The tenant always comes from get_tenant_id (X-Tenant-ID header, same as the tyre-maintenance API) and every query is
filtered by it, so one tenant can never read another tenant's rows.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.services.bms_snapshot import SEAT_COUNT      # 60 = seats A1..A60 of the sensor = bus capacity


logger = logging.getLogger(__name__)

bms_router = APIRouter(prefix="/api/bms", tags=["BMS"])
bms_sensor_router = APIRouter(prefix="/api/bms-sensor", tags=["BMS vs Sensor"])

_ESTIMATE_NOTE = (
    "sensor_in and sensor_out are ESTIMATES from seat occupancy transitions, not exact passenger boarding/alighting "
    "(a passenger changing seats counts as one In and one Out). sensor_total (occupied seats) is the primary comparison."
)


def get_tenant_id(x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID")) -> int:
    """X-Tenant-ID is OPTIONAL for the BMS APIs. When the header is missing the default tenant is used:
    BMS_DEFAULT_TENANT_ID, else DEV_TENANT_ID (already used by the dev login), else 1.
    (The shared dependency in app/core/tenant.py is left untouched for the existing APIs.)"""
    if x_tenant_id is None:
        raw = (os.getenv("BMS_DEFAULT_TENANT_ID") or os.getenv("DEV_TENANT_ID") or "1").strip()
        try:
            x_tenant_id = int(raw)
        except ValueError:
            x_tenant_id = 1
    if x_tenant_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid tenant ID.")
    return x_tenant_id


def get_bms_repository():
    """Dependency (overridden in tests)."""
    from app.config.bms_config import load_bms_config
    from app.database.bms_repository import BmsRepository
    return BmsRepository(load_bms_config().source_table)


def _json(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _clean(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _json(v) for k, v in row.items()}


def _comparison_json(row: Dict[str, Any]) -> Dict[str, Any]:
    r = _clean(row)
    g = r.get                                         # the existing table may lack optional columns (journey_id, bms_stop_id ...)
    return {
        "id": g("id"),
        "tenant_id": g("tenant_id"),
        "vehicle_number": g("vehicle_number"),
        "device_id": g("device_id"),
        "iot_kit": g("iot_kit"),
        "journey_id": g("journey_id"),
        "stop": {
            "bms_stop_id": g("bms_stop_id"),
            "stop_sequence": g("stop_sequence"),
            "stop_name": g("stop_name"),
            "lat": g("bms_lat"),
            "long": g("bms_long"),
        },
        "bms": {"in": g("bms_in"), "out": g("bms_out"), "total": g("bms_total")},
        "sensor": {
            "in": g("sensor_in"),
            "out": g("sensor_out"),
            "total": g("sensor_total"),
            "lat": g("sensor_lat"),
            "long": g("sensor_long"),
            "timestamp": g("sensor_timestamp"),
            "in_out_is_estimate": True,
        },
        "total_difference": g("total_difference"),
        "comparison_status": g("comparison_status"),
        "created_at": g("created_at"),
    }


def _num(value: Any) -> Optional[float]:
    return None if value is None else float(value)


def build_summary(rows, bus_capacity: Optional[int] = None) -> Dict[str, Any]:
    """KPI numbers of the dashboard, from comparison rows (newest first). All rows are counted, not one page.
    "Compared" = MATCH or MISMATCH rows (INCOMPLETE rows have no reliable sensor numbers, so they are left out)."""
    rows = [_clean(r) for r in rows]
    compared = [r for r in rows if r.get("comparison_status") in ("MATCH", "MISMATCH")]
    matches = [r for r in compared if r["comparison_status"] == "MATCH"]
    diffs = [abs(float(r["total_difference"])) for r in compared if r.get("total_difference") is not None]

    def total(key: str) -> Optional[int]:
        values = [r[key] for r in compared if r.get(key) is not None]
        return int(sum(values)) if values else None

    def highest(key: str) -> Optional[int]:
        values = [r[key] for r in compared if r.get(key) is not None]
        return int(max(values)) if values else None

    latest = rows[0] if rows else None
    over = None
    if bus_capacity is not None:
        over = sum(1 for r in compared
                   if max(r.get("bms_total") or 0, r.get("sensor_total") or 0) > bus_capacity)
    return {
        "bus_capacity": bus_capacity,
        "latest": None if latest is None else {
            "stop_sequence": latest.get("stop_sequence"),
            "timestamp": latest.get("sensor_timestamp"),
            "on_board_bms": latest.get("bms_total"),
            "on_board_sensor": latest.get("sensor_total"),
            "difference": latest.get("total_difference"),
        },
        "stops": len(rows),
        "compared": len(compared),
        "exact_matches": len(matches),
        "mismatches": len(compared) - len(matches),
        "incomplete": sum(1 for r in rows if r.get("comparison_status") == "INCOMPLETE"),
        "without_bms": sum(1 for r in rows if r.get("bms_total") is None),
        "without_sensor_count": sum(1 for r in rows if r.get("sensor_total") is None),
        "match_rate_percent": round(100.0 * len(matches) / len(compared), 1) if compared else None,
        "mean_abs_error": round(sum(diffs) / len(diffs), 2) if diffs else None,
        "max_abs_error": int(max(diffs)) if diffs else None,
        "boarded": {"bms": total("bms_in"), "sensor": total("sensor_in")},
        "alighted": {"bms": total("bms_out"), "sensor": total("sensor_out")},
        "max_on_board": {"bms": highest("bms_total"), "sensor": highest("sensor_total")},
        "over_capacity_stops": over,
    }


def _stop_json(row: Dict[str, Any]) -> Dict[str, Any]:
    r = _clean(row)
    item = {
        "bms_stop_id": r["id"],
        "tenant_id": r["tenant_id"],
        "vehicle_number": r["vehicle_number"],
        "device_id": r["device_id"],
        "iot_kit": r["iot_kit"],
        "stop_sequence": r["stop_sequence"],
        "stop_name": r["stop_name"],
        "lat": r["lat"],
        "long": r["long"],
        "bms": {"in": r["bms_in"], "out": r["bms_out"], "total": r["bms_total"]},
        "created_at": r["created_at"],
    }
    return item


@bms_router.get("/stops")
def get_bms_stops(
    vehicle_number: Optional[str] = Query(None, description="Optional. Vehicle number, e.g. AP31Z0044 (all vehicles when omitted)"),
    device_id: Optional[int] = Query(None),
    tenant_id: int = Depends(get_tenant_id),
    repo=Depends(get_bms_repository),
):
    """The predefined BMS stops (In / Out / Total), ordered by stop_sequence."""
    try:
        rows = repo.list_stops(tenant_id, vehicle_number, device_id)
    except Exception:
        logger.exception("Failed to read BMS stops.")
        raise HTTPException(status_code=500, detail="Unable to retrieve BMS stops")
    return {"success": True, "count": len(rows), "items": [_stop_json(r) for r in rows]}


@bms_sensor_router.get("/comparisons")
def get_comparisons(
    vehicle_number: Optional[str] = Query(None, description="Optional. Vehicle number, e.g. AP31Z0044 (all vehicles when omitted)"),
    device_id: Optional[int] = Query(None),
    stop_sequence: Optional[int] = Query(None, ge=1),
    comparison_status: Optional[str] = Query(None, description="MATCH | MISMATCH | INCOMPLETE"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    bus_capacity: Optional[int] = Query(None, ge=1, description="Optional. Seats of the bus; default = all sensor seats (A1..A60 = 60). Only used for summary.over_capacity_stops"),
    tenant_id: int = Depends(get_tenant_id),
    repo=Depends(get_bms_repository),
):
    """Stored BMS vs Sensor comparisons, newest first, read straight from dbo.bms_sensor_comparison.
    "items" is the requested page; "summary" holds the dashboard KPI numbers for ALL rows of the vehicle / device /
    stop filters (the comparison_status filter and the paging do not change the summary)."""
    status = comparison_status.strip().upper() if comparison_status else None
    if status is not None and status not in ("MATCH", "MISMATCH", "INCOMPLETE"):
        raise HTTPException(status_code=400, detail="comparison_status must be MATCH, MISMATCH or INCOMPLETE")

    filters = {
        "vehicle_number": vehicle_number, "device_id": device_id,
        "stop_sequence": stop_sequence, "comparison_status": status,
    }
    try:
        rows, total = repo.list_comparisons(tenant_id, filters, page, page_size)
        summary_rows = repo.list_comparisons_for_summary(tenant_id, {**filters, "comparison_status": None})
    except Exception:
        logger.exception("Failed to read BMS comparisons.")
        raise HTTPException(status_code=500, detail="Unable to retrieve BMS comparisons")

    return {
        "success": True,
        "page": page,
        "page_size": page_size,
        "total": total,
        "count": len(rows),
        "note": _ESTIMATE_NOTE,
        "summary": build_summary(summary_rows, bus_capacity or SEAT_COUNT),
        "items": [_comparison_json(r) for r in rows],
    }


routers = [bms_router, bms_sensor_router]