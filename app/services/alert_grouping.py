"""Sensor alerts = every run of 1s, and how long that run lasts.

For each sensor (tenant, vehicle, IoT kit, sensor_sub_id) the rows are read in time order. Each run of 1s is ONE
alert: it starts on the row where the 1 first appears (after a 0, or at the very first reading) and ends on the
first row where the value is 0 again; `lasted_seconds` is the time between the two. If the value has not gone back
to 0 yet the alert is `ongoing`, and the time runs to the latest reading.

    0 0 0 1 1 1 1 1 0      one alert, starts at the first 1, ends at the 0
    1 1 0 0 1 1 0          two alerts (the leading 1s, and the later 1s)

Changes from 1 to 0 are not alerts; they only mark the end of one. A long silence (more than
`max_gap_seconds` between the last 1 and the next reading) ends the alert at that last 1. Rows that are an exact repeat of the row just
before (same timestamp, value and data, e.g. a file ingested twice) are counted once.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from app.services.sensor_types import SENSOR_TYPE_BY_SUB_ID


def _parse_ts(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _flag(value: Any) -> int:
    return 1 if value in (1, True, "1") else 0


def _iso(ts: Optional[datetime]) -> Optional[str]:
    return ts.isoformat(sep=" ") if ts else None


DEFAULT_MAX_GAP_SECONDS = 60


def detect_alerts(rows: Iterable[dict], max_gap_seconds: int = DEFAULT_MAX_GAP_SECONDS) -> list[dict]:
    """rows: dicts with tenant_id, vehicle_number, iot_kit, timestamp, sensor_sub_id, sensor_data, is_alert,
    ordered by tenant, vehicle, kit, sensor_sub_id, timestamp. Returns the alerts in time order, oldest first.

    max_gap_seconds: if the next reading arrives more than this many seconds after the last 1 (the device was
    silent), the alert is ended at that last 1 and the silent time is not counted. 0 = off (an alert then runs to
    the first 0, however late it arrives)."""
    max_gap = max(0, int(max_gap_seconds))
    alerts: list[dict] = []
    key = None
    prev_value: Optional[int] = None
    last_sig = None
    open_alert: Optional[dict] = None

    def finish(alert: Optional[dict], ended: Optional[datetime], gap: bool = False) -> None:
        if alert is None:
            return
        start, last = alert.pop("_start"), alert.pop("_last")
        stop = ended or last
        alert["ongoing"] = ended is None
        alert["ended_after_gap"] = gap
        alert["ended_at"] = _iso(ended)
        alert["lasted_seconds"] = int((stop - start).total_seconds()) if start and stop else None

    for row in rows:
        row_key = (row["tenant_id"], row["vehicle_number"], row["iot_kit"], row["sensor_sub_id"])
        ts = _parse_ts(row["timestamp"])
        value = _flag(row["is_alert"])
        if row_key != key:                                   # a new sensor starts a fresh sequence
            finish(open_alert, None)
            open_alert, key, prev_value, last_sig = None, row_key, None, None
        sig = (ts, value, row["sensor_data"])
        if sig == last_sig:                                  # exact repeat of the previous row
            continue
        last_sig = sig

        if open_alert is not None and max_gap and ts and open_alert["_last"] \
                and (ts - open_alert["_last"]).total_seconds() > max_gap:
            finish(open_alert, open_alert["_last"], gap=True)   # silent gap: the alert ended at its last 1
            open_alert, prev_value = None, None

        if open_alert is not None:
            if value == 1:
                open_alert["_last"] = ts                     # the 1 is still going
            else:
                finish(open_alert, ts)                       # back to 0: the alert is over
                open_alert = None
        if value == 1 and prev_value != 1:                   # a 1 after a 0 (or the first reading): a new alert
            open_alert = {
                "tenant_id": row["tenant_id"], "vehicle_number": row["vehicle_number"],
                "iot_kit": row["iot_kit"], "sensor_sub_id": row["sensor_sub_id"],
                "sensor_type": SENSOR_TYPE_BY_SUB_ID.get(row["sensor_sub_id"]),
                "started_at": _iso(ts),
                "sensor_data": row["sensor_data"],
                "_start": ts, "_last": ts,
            }
            alerts.append(open_alert)
        prev_value = value

    finish(open_alert, None)
    alerts.sort(key=lambda a: (a["started_at"] or "", a["sensor_sub_id"]))      # oldest first
    return alerts


def summarise(alerts: list[dict], sensor_sub_id: Optional[int] = None) -> dict:
    """Total alerts and total seconds, per sensor_sub_id. Every sensor (1..5, or only the requested one) is
    listed; a sensor with no alerts shows 0."""
    ids = [sensor_sub_id] if sensor_sub_id is not None else sorted(SENSOR_TYPE_BY_SUB_ID)
    by: dict = {i: {"sensor_sub_id": i, "sensor_type": SENSOR_TYPE_BY_SUB_ID.get(i),
                    "alert_count": 0, "total_lasted_seconds": 0} for i in ids}
    for a in alerts:
        s = by.setdefault(a["sensor_sub_id"], {"sensor_sub_id": a["sensor_sub_id"], "sensor_type": a["sensor_type"],
                                               "alert_count": 0, "total_lasted_seconds": 0})
        s["alert_count"] += 1
        s["total_lasted_seconds"] += a.get("lasted_seconds") or 0
    per_sensor = [by[k] for k in sorted(by, key=lambda x: (x is None, x))]
    return {"total_alerts": len(alerts), "by_sensor": per_sensor}