"""Request/response schemas. Bodies forbid unknown fields, so tenant_id / role
can never be smuggled in through a request body."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_WINDOW_DAYS = 3650


def _strict_date(value: Any) -> Any:
    if value is None or isinstance(value, date):
        return value
    if not isinstance(value, str) or not _ISO_DATE.match(value.strip()):
        raise ValueError("Date must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("Date is not a valid calendar date")


def _clean_reason(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("reason must be text")
    value = value.strip()
    return value or None


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Window = Field(gt=0, le=MAX_WINDOW_DAYS, strict=True)


class CreateMaintenanceRequest(_Body):
    """Only the vehicle and its last maintenance date. The window (30 days by default, VM_DEFAULT_WINDOW_DAYS) and
    the expected date (previous + window) are worked out by the server and cannot be sent."""
    vehicle_number: str = Field(min_length=1, max_length=50)
    previous_vehicle_maintenance_date: date
    reason: Optional[str] = Field(default=None, max_length=1000)

    _dates = field_validator("previous_vehicle_maintenance_date", mode="before")(_strict_date)
    _reason = field_validator("reason", mode="before")(_clean_reason)


class PostponeRequest(_Body):
    """The date the driver says the maintenance will actually be completed. The expected date is never sent:
    it is always previous date + window, calculated by the server."""
    driver_id: int = Field(gt=0, strict=True)        # the driver enters their own id (= vehicles.driver_id)
    postponed_date: date
    reason: str = Field(min_length=1, max_length=1000)          # a reason is required to postpone

    _dates = field_validator("postponed_date", mode="before")(_strict_date)
    _reason = field_validator("reason", mode="before")(_clean_reason)


class CompleteRequest(_Body):
    driver_id: int = Field(gt=0, strict=True)        # the driver enters their own id (= vehicles.driver_id)
    done_date: date
    reason: Optional[str] = Field(default=None, max_length=1000)

    _dates = field_validator("done_date", mode="before")(_strict_date)
    _reason = field_validator("reason", mode="before")(_clean_reason)