from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TyreMaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: int
    device_id: int
    vehicle_number: Optional[str] = None

    tyre_life_limit_km: Decimal
    tyre_change_odometer_km: Decimal
    current_distance_km: Decimal

    usage_percentage: Decimal
    remaining_km: Decimal

    maintenance_status: str

    last_tyre_change_date: Optional[datetime] = None
    last_limit_reminder_at: Optional[datetime] = None


class RegisterTyreMaintenanceRequest(BaseModel):
    installation_date: datetime = Field(
        ...,
        description="Actual date and time when the currently installed tyres were fitted."
    )


class UpdateTyreLimitRequest(BaseModel):
    tyre_life_limit_km: Decimal = Field(
        ...,
        gt=0,
        description="Configured tyre lifespan in kilometres."
    )


class TyreChangeCompleteRequest(BaseModel):
    replacement_date: Optional[datetime] = Field(
        default=None,
        description="Actual tyre replacement date. If omitted, server UTC time is used."
    )


class TyreMaintenanceListResponse(BaseModel):
    count: int
    items: list[TyreMaintenanceResponse]