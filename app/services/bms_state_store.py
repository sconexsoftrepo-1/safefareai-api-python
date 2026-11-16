"""In-memory progress of every vehicle (stop phase, previous seat state, last processed snapshot).

Nothing extra is stored in SQL Server: after a restart the service rebuilds a vehicle's progress from the two existing
tables (dbo.bms_sensor_comparison tells which stop was completed last, dbo.prs_sensor_readings is re-read from there).
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from app.services.bms_stop_tracker import VehicleState

Key = Tuple[int, str, int]


class StateStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._states: Dict[Key, VehicleState] = {}

    def get(self, tenant_id, vehicle_number, device_id) -> Optional[VehicleState]:
        with self._lock:
            return self._states.get((tenant_id, vehicle_number, device_id))

    def put(self, state: VehicleState) -> None:
        with self._lock:
            self._states[(state.tenant_id, state.vehicle_number, state.device_id)] = state

    def list_for_tenant(self, tenant_id, vehicle_number=None, device_id=None) -> List[Dict[str, Any]]:
        with self._lock:
            states = list(self._states.values())
        return [
            {"tenant_id": s.tenant_id, "vehicle_number": s.vehicle_number, "device_id": s.device_id,
             "phase": s.phase, "current_stop_sequence": s.current_stop_sequence,
             "last_completed_sequence": s.last_completed_sequence, "first_hit_at": s.first_hit_at,
             "last_in_area_at": s.last_in_area_at, "visit_in": s.visit_in, "visit_out": s.visit_out,
             "visit_last_total": s.visit_last_total, "last_snapshot_ts": s.last_snapshot_ts}
            for s in states
            if s.tenant_id == tenant_id and vehicle_number in (None, s.vehicle_number) and device_id in (None, s.device_id)
        ]


STATE_STORE = StateStore()          # shared by the worker thread and the /tracking API