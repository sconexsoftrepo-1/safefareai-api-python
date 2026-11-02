"""Shared request models. JSON uses camelCase to match the Java BFF / frontend conventions.

Datetimes: timezone-aware values are converted to UTC; naive values are interpreted as UTC (the vendor's
documented time zone).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class TimeRangeIn(CamelModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def _ordered(self):
        if self.end_time <= self.start_time:
            raise ValueError("endTime must be after startTime")
        return self


class ScopeIn(CamelModel):
    device_ids: list[PositiveInt] | None = Field(None, max_length=1000,
                                                 description="Internal device ids (dbo.devices.id)")
    group_id: PositiveInt | None = Field(None, description="Internal group id (dbo.device_groups.id)")

    @field_validator("device_ids")
    @classmethod
    def _unique(cls, value):
        return list(dict.fromkeys(value)) if value else value


class PageIn(CamelModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)


class ScopedRangeQuery(ScopeIn, TimeRangeIn, PageIn):
    pass
