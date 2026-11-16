from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Iterable, Optional

from app.config.bms_config import BmsConfig
from app.services.bms_comparison_service import BmsComparisonService
from app.services.bms_state_store import StateStore
from tests.bms.fake_repo import FakeRepo
from tests.bms.helpers import BASE, STOPS, offset_north, seat_rows

VEHICLE = {"tenant_id": 1, "vehicle_number": "AP31Z0044", "device_id": 1215, "iot_kit": "IOT-KIT-001"}


class Harness:
    """Feeds 10-second sensor snapshots into the fake DB and runs one worker pass after each."""

    def __init__(self, cfg: Optional[BmsConfig] = None, repo: Optional[FakeRepo] = None, stops=STOPS):
        self.cfg = cfg or BmsConfig()
        self.repo = repo or FakeRepo()
        if not self.repo.vehicles:
            self.repo.add_vehicle(stops=stops)
        self.now = BASE
        self.t = BASE
        self.store = StateStore()
        self.service = BmsComparisonService(self.repo, self.cfg, clock=lambda: self.now, store=self.store)
        self.snapshot_no = 0

    def new_service(self) -> BmsComparisonService:
        """Simulates a backend restart: new service object and EMPTY memory, same database."""
        self.store = StateStore()
        self.service = BmsComparisonService(self.repo, self.cfg, clock=lambda: self.now, store=self.store)
        return self.service

    def send(self, lat, lon, occupied: Iterable[int], *, dt: int = 10, run: bool = True, **row_kwargs):
        self.t = self.t + timedelta(seconds=dt)
        self.snapshot_no += 1
        self.repo.add_rows(seat_rows(self.t, occupied, lat, lon, snapshot_id=f"snap-{self.snapshot_no}", **row_kwargs))
        self.now = self.t + timedelta(seconds=1)
        return self.service.process_vehicle(dict(VEHICLE), now=self.now) if run else None

    def run(self):
        return self.service.process_vehicle(dict(VEHICLE), now=self.now)

    def at_stop(self, seq: int, metres_north: float = 20.0):
        s = STOPS[seq - 1]
        return offset_north(s["lat"], s["long"], metres_north)

    def visit_stop(self, seq: int, before: set, boarded: set = frozenset(), left: set = frozenset()):
        """approach (150 m) -> 4 readings at the stop (boarding happens at the 1st, leaving at the 3rd) -> leave."""
        after_board = (before | boarded)
        final = after_board - left
        self.send(*self.at_stop(seq, 150), before)
        self.send(*self.at_stop(seq, 20), after_board)
        self.send(*self.at_stop(seq, 22), after_board)
        self.send(*self.at_stop(seq, 21), final)
        self.send(*self.at_stop(seq, 20), final)
        self.send(*self.at_stop(seq, 160), final)
        self.send(*self.at_stop(seq, 170), final)
        return final

    def state(self):
        return self.store.get(1, "AP31Z0044", 1215)

    @property
    def comparisons(self):
        return self.repo.comparisons