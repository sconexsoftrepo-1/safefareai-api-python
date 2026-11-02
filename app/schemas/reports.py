from typing import Literal

from pydantic import Field, PositiveInt

from app.schemas.common import ScopedRangeQuery, ScopeIn, TimeRangeIn

ReportType = Literal["mileage", "driving", "parking", "multimedia", "alarm", "ai_events"]


class MultimediaQuery(ScopedRangeQuery):
    media_type: Literal[0, 1] = Field(0, description="0 image, 1 video")


class AlarmReportQuery(ScopedRangeQuery):
    alarm_type_ids: list[PositiveInt] | None = Field(None, max_length=500)


class DashboardQuery(ScopeIn, TimeRangeIn):
    top_n: int = Field(10, ge=1, le=50)


class SafetyQuery(ScopeIn, TimeRangeIn):
    level: Literal["vehicle", "fleet"] = "vehicle"


class ExportIn(ScopeIn, TimeRangeIn):
    report_type: ReportType
    format: Literal["XLSX", "PDF", "CSV"] = "XLSX"
    media_type: Literal[0, 1] = 0
    alarm_type_ids: list[PositiveInt] | None = Field(None, max_length=500)


class DailyMileageQuery(ScopeIn, TimeRangeIn):
    pass
