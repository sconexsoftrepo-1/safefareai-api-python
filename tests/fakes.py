"""In-memory doubles that mirror the SQL Server repository contract (no database needed)."""
from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime

from app.integration.directory import Recipient
from app.repositories.vehicle_maintenance_repository import (
    COLUMNS, UPDATABLE_COLUMNS, AccessScope, ListFilters, MaintenanceRecord,
)
from app.utils.date_calculations import effective_due, effective_status


class FakeSession:
    def __init__(self, repo: "FakeRepository"):
        self.repo = repo

    def devices_for_vehicle(self, tenant_id, vehicle_number):
        return [d for (t, v, d) in self.repo.vehicles if t == tenant_id and v == vehicle_number]

    def find(self, tenant_id, vehicle_number, device_id=None, for_update=False):
        return [replace(r) for r in self.repo.rows
                if r.tenant_id == tenant_id and r.vehicle_number == vehicle_number
                and (device_id is None or r.device_id == device_id)]

    def insert(self, record):
        self.repo.rows.append(replace(record))

    def insert_postponement(self, record, postponed_date, reason, postponed_by, created_at):
        """Mirrors the postponements table: a history row; the current cycle reads the latest one."""
        self.repo.postponements.append({
            "tenant_id": record.tenant_id, "vehicle_number": record.vehicle_number, "device_id": record.device_id,
            "cycle_previous_date": record.previous_vehicle_maintenance_date,
            "expected_date": record.expected_vehicle_maintenance_date,
            "postponed_date": postponed_date, "reason": reason, "postponed_by": postponed_by,
            "created_at": created_at})
        for r in self.repo.rows:
            if r.key() == record.key():
                r.postponed_date, r.postponed_reason = postponed_date, reason
                r.postponed_by, r.postponed_at = postponed_by, created_at

    def update(self, tenant_id, vehicle_number, device_id, fields):
        assert set(fields) <= UPDATABLE_COLUMNS
        n = 0
        for r in self.repo.rows:
            if (r.tenant_id, r.vehicle_number, r.device_id) == (tenant_id, vehicle_number, device_id):
                old_prev = r.previous_vehicle_maintenance_date
                for k, v in fields.items():
                    setattr(r, k, v)
                if r.previous_vehicle_maintenance_date != old_prev:       # new cycle: old postponement no longer matches
                    r.postponed_date = r.postponed_by = r.postponed_at = r.postponed_reason = None
                n += 1
        return n

    def _scoped(self, scope: AccessScope):
        for r in self.repo.rows:
            if scope.tenant_ids is not None and r.tenant_id not in scope.tenant_ids:
                continue
            if scope.vehicle_numbers is not None and r.vehicle_number not in scope.vehicle_numbers:
                continue
            yield r

    def search(self, scope, f: ListFilters, today, offset, limit):
        out = []
        for r in self._scoped(scope):
            due = effective_due(r.expected_vehicle_maintenance_date, r.postponed_date)
            st = effective_status(r.expected_vehicle_maintenance_date, r.postponed_date, r.status, today)
            if f.vehicle_number and r.vehicle_number != f.vehicle_number: continue
            if f.device_id is not None and r.device_id != f.device_id: continue
            if f.status and st != f.status: continue
            if f.expected_date_from and due < f.expected_date_from: continue
            if f.expected_date_to and due > f.expected_date_to: continue
            out.append((replace(r), st))
        out.sort(key=lambda x: (effective_due(x[0].expected_vehicle_maintenance_date, x[0].postponed_date),
                                x[0].vehicle_number))
        return out[offset:offset + limit], len(out)

    def all_schedules(self):
        return [replace(r) for r in self.repo.rows]

    def tenants_for_vehicle(self, vehicle_number, tenant_ids):
        return sorted({r.tenant_id for r in self.repo.rows if r.vehicle_number == vehicle_number
                       and (tenant_ids is None or r.tenant_id in tenant_ids)})


class FakeRepository:
    """Tables: only vehicle_maintenance rows + vehicles lookup. Rolls back on exception."""

    def __init__(self):
        self.rows: list[MaintenanceRecord] = []
        self.vehicles: set[tuple] = set()
        self.postponements: list[dict] = []      # history table (never deleted)

    @contextmanager
    def unit_of_work(self):
        snapshot = copy.deepcopy((self.rows, self.postponements))
        try:
            yield FakeSession(self)
        except BaseException:
            self.rows, self.postponements = snapshot
            raise


class FakeDirectory:
    def __init__(self):
        self.assignments: dict[tuple, set] = {}   # (tenant, driver_id) -> {vehicle_number}
        self.team: dict[tuple, list] = {}         # (tenant, owner_id) -> [driver ids who report to the owner]

    def driver_vehicle_numbers(self, tenant_id, driver_user_id):
        return set(self.assignments.get((tenant_id, driver_user_id), set()))

    def list_drivers(self, tenant_id, owner_user_id):
        return [{"driver_id": d, "display_name": f"Driver {d}", "email": None, "phone": None}
                for d in self.team.get((tenant_id, owner_user_id), [])]

    def assign_driver(self, tenant_id, owner_user_id, vehicle_number, driver_user_id):
        if driver_user_id not in self.team.get((tenant_id, owner_user_id), []):
            return "not_your_driver"
        for key in [k for k in self.assignments if k[0] == tenant_id]:
            self.assignments[key].discard(vehicle_number)            # one driver per vehicle
        self.assignments.setdefault((tenant_id, driver_user_id), set()).add(vehicle_number)
        return "ok"

    def fleet_owner_recipients(self, tenant_id):
        return [Recipient(f"owner-{tenant_id}", "fleet_owner")]

    def driver_recipients(self, tenant_id, vehicle_number):
        return [Recipient(d, "driver") for (t, d), vs in self.assignments.items()
                if t == tenant_id and vehicle_number in vs]


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, n):
        self.sent.append(n)

    def kinds(self):
        return [n.kind for n in self.sent]

    def clear(self):
        self.sent.clear()


class Clock:
    def __init__(self, today: date):
        self.today = today

    def __call__(self):
        return self.today

    def now(self):
        return datetime.combine(self.today, datetime.min.time()).replace(hour=10)