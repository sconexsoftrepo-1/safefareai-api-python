from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.vehicle_maintenance import get_vehicle_maintenance_service, router
from app.integration.auth_adapter import CurrentUser, Role, get_current_user
from app.scheduler.maintenance_scheduler import MaintenanceScheduler
from app.services.maintenance_notification_service import MaintenanceNotificationService
from app.services.vehicle_maintenance_service import VehicleMaintenanceService
from tests.fakes import Clock, FakeDirectory, FakeRepository, RecordingSender

T1, T2 = 101, 202
OWNER = CurrentUser(user_id="owner-1", role=Role.FLEET_OWNER, tenant_id=T1)
OWNER_T2 = CurrentUser(user_id="owner-2", role=Role.FLEET_OWNER, tenant_id=T2)
DRIVER = CurrentUser(user_id="driver-1", role=Role.DRIVER, tenant_id=T1)
DRIVER_2 = CurrentUser(user_id="driver-2", role=Role.DRIVER, tenant_id=T1)
ADMIN = CurrentUser(user_id="admin-1", role=Role.ADMIN, tenant_id=None, authorized_tenant_ids=(T1, T2))


class Env:
    def __init__(self, today=date(2026, 9, 30)):
        self.clock = Clock(today)
        self.repo = FakeRepository()
        self.directory = FakeDirectory()
        self.sender = RecordingSender()
        self.notifications = MaintenanceNotificationService(self.sender, self.directory)
        self.service = VehicleMaintenanceService(
            self.repo, self.directory, self.notifications, self.clock, self.clock.now)
        self.scheduler = MaintenanceScheduler(
            self.repo, self.notifications, self.clock, self.clock.now, "Asia/Kolkata")
        # vehicles table fixture: tenant_id, vehicle_number, device_id
        self.repo.vehicles |= {(T1, "AP31Z0044", 1215), (T1, "AP31Z0055", 1216), (T1, "AP31Z0066", 1217),
                               (T2, "TS09AB1234", 2001)}          # AP31Z0066 has no driver yet
        self.directory.assignments[(T1, "driver-1")] = {"AP31Z0044"}
        self.directory.assignments[(T1, "driver-2")] = {"AP31Z0055"}
        self.directory.team[(T1, "owner-1")] = ["driver-1", "driver-2", "driver-3"]
        self.user = OWNER
        app = FastAPI()
        app.include_router(router)
        app.state.vehicle_maintenance_service = self.service
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def as_(self, user):
        self.user = user
        return self.client


@pytest.fixture
def env():
    return Env()


def create_body(**over):
    body = {
        "vehicle_number": "AP31Z0044",
        "previous_vehicle_maintenance_date": "2026-09-30",
        "maintenance_time_window": 30,
        "reason": "Regular maintenance",
    }
    body.update(over)
    return body
