"""In-memory stand-in for BmsRepository (same methods, same rules: idempotent comparison insert on
(tenant, vehicle, device, stop_sequence, sensor_timestamp)). Lets the whole worker flow run without SQL Server."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.services.bms_stop_tracker import Stop

VISIT_KEY = ("tenant_id", "vehicle_number", "device_id", "stop_sequence", "sensor_timestamp")


class FakeRepo:
    def __init__(self):
        self.vehicles: List[Dict[str, Any]] = []
        self.stops: List[Dict[str, Any]] = []            # dicts like dbo.bms_stop_details
        self.rows: List[Dict[str, Any]] = []             # prs_sensor_readings
        self.comparisons: List[Dict[str, Any]] = []      # bms_sensor_comparison
        self._next_row = 1
        self._next_comparison = 1
        self.fail: Dict[str, int] = {}                   # method name -> number of upcoming calls that raise

    # ---------------- helpers for tests
    def add_vehicle(self, tenant_id=1, vehicle_number="AP31Z0044", device_id=1215, iot_kit="IOT-KIT-001", stops=None):
        self.vehicles.append({"tenant_id": tenant_id, "vehicle_number": vehicle_number, "device_id": device_id, "iot_kit": iot_kit})
        for s in stops or []:
            self.stops.append({**s, "tenant_id": tenant_id, "vehicle_number": vehicle_number, "device_id": device_id,
                               "iot_kit": iot_kit, "id": len(self.stops) + 1, "created_at": datetime(2026, 1, 1)})

    def add_rows(self, rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            self.rows.append({**r, "id": self._next_row})
            self._next_row += 1

    def _maybe_fail(self, name: str) -> None:
        if self.fail.get(name, 0) > 0:
            self.fail[name] -= 1
            raise RuntimeError(f"injected SQL failure in {name}")

    # ---------------- worker reads
    def list_active_vehicles(self):
        return [dict(v) for v in self.vehicles]

    def get_stops(self, tenant_id, vehicle_number, device_id) -> List[Stop]:
        rows = [s for s in self.stops if (s["tenant_id"], s["vehicle_number"], s["device_id"]) == (tenant_id, vehicle_number, device_id)]
        return [Stop(id=s["id"], sequence=s["stop_sequence"], name=s["stop_name"], lat=float(s["lat"]), lon=float(s["long"]),
                     bms_in=s["bms_in"], bms_out=s["bms_out"], bms_total=s["bms_total"])
                for s in sorted(rows, key=lambda s: s["stop_sequence"])]

    def fetch_snapshot_rows(self, tenant_id, vehicle_number, after, limit_rows, inclusive=False):
        self._maybe_fail("fetch_snapshot_rows")
        rows = [r for r in self.rows if r["tenant_id"] == tenant_id and r["vehicle_number"] == vehicle_number
                and (r["timestamp"] >= after if inclusive else r["timestamp"] > after)]
        rows.sort(key=lambda r: (r["timestamp"], r["id"]))
        return [dict(r) for r in rows[:limit_rows]]

    def latest_snapshot(self, tenant_id, vehicle_number):
        from app.services.bms_snapshot import build_snapshots
        rows = [r for r in self.rows if r["tenant_id"] == tenant_id and r["vehicle_number"] == vehicle_number]
        if not rows:
            return None
        latest_ts = max(r["timestamp"] for r in rows)
        snap = build_snapshots([r for r in rows if r["timestamp"] == latest_ts])[-1]
        return {"timestamp": snap.timestamp, "lat": snap.lat, "long": snap.lon, "occupied_seats": snap.occupied_count,
                "valid": snap.seats_valid, "problems": snap.problems, "row_count": snap.row_count}

    # ---------------- comparison table
    def last_comparison(self, tenant_id, vehicle_number, device_id):
        rows = [c for c in self.comparisons if (c["tenant_id"], c["vehicle_number"], c["device_id"]) == (tenant_id, vehicle_number, device_id)]
        if not rows:
            return None
        last = max(rows, key=lambda c: c["id"])
        return {"stop_sequence": last["stop_sequence"], "sensor_timestamp": last["sensor_timestamp"]}

    def insert_comparison(self, row):
        self._maybe_fail("insert_comparison")
        key = tuple(row[k] for k in VISIT_KEY)
        if any(tuple(c[k] for k in VISIT_KEY) == key for c in self.comparisons):
            return 0
        self.comparisons.append({**row, "id": self._next_comparison, "created_at": datetime(2026, 11, 16, 12, 0, 0)})
        self._next_comparison += 1
        return 1

    # ---------------- API reads
    def list_stops(self, tenant_id, vehicle_number, device_id):
        out = [dict(s) for s in self.stops if s["tenant_id"] == tenant_id
               and vehicle_number in (None, s["vehicle_number"]) and device_id in (None, s["device_id"])]
        return sorted(out, key=lambda r: (r["vehicle_number"], r["device_id"], r["stop_sequence"]))

    def list_comparisons(self, tenant_id, filters, page, page_size):
        rows = [c for c in self.comparisons if c["tenant_id"] == tenant_id]
        for column, value in filters.items():
            if value is not None:
                rows = [c for c in rows if c[column] == value]
        rows.sort(key=lambda c: c["id"], reverse=True)
        return rows[(page - 1) * page_size: page * page_size], len(rows)

    def list_comparisons_for_summary(self, tenant_id, filters, limit=5000):
        rows = [c for c in self.comparisons if c["tenant_id"] == tenant_id]
        for column, value in filters.items():
            if value is not None:
                rows = [c for c in rows if c[column] == value]
        rows.sort(key=lambda c: c["id"], reverse=True)
        return rows[:limit]

    def get_comparison(self, tenant_id, comparison_id):
        return next((c for c in self.comparisons if c["id"] == comparison_id and c["tenant_id"] == tenant_id), None)