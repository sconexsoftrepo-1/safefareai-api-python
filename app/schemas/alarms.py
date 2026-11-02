from datetime import datetime
from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from app.schemas.common import CamelModel, PageIn, ScopedRangeQuery, ScopeIn

Outcome = Literal["DISPATCH_EMERGENCY", "DISPATCH_TERMINAL", "VOICE_COMMAND", "TEST", "FALSE_POSITIVE",
                  "CONFIRMED_ALARM"]
ActionType = Literal["ACKNOWLEDGE", "ASSIGN", "COMMENT", "HIGH_PRIORITY_STEP", "CLOSE", "REOPEN",
                     "DISPATCH_EMERGENCY", "DISPATCH_TERMINAL", "VOICE_COMMAND", "TEST", "FALSE_POSITIVE",
                     "CONFIRMED_ALARM"]


class AiEventQuery(ScopedRangeQuery):
    alarm_type_ids: list[PositiveInt] | None = Field(
        None, max_length=500, description="Vendor alarm type ids; default = all active ADAS/DSM/BSD types")
    include_hidden: bool = Field(False, description="Include alarms hidden by a HIDE linkage rule")


class RoutineAlarmQuery(ScopeIn, PageIn):
    start_time: datetime | None = Field(None, description="Omit both times to get the last 24 hours (vendor 5.4)")
    end_time: datetime | None = None
    alarm_type_ids: list[PositiveInt] | None = Field(None, max_length=500,
                                                     description="Default = all active general alarm types")
    include_hidden: bool = False

    @model_validator(mode="after")
    def _both_or_none(self):
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("startTime and endTime must be supplied together")
        if self.start_time and self.end_time <= self.start_time:
            raise ValueError("endTime must be after startTime")
        return self


class AlarmActionIn(CamelModel):
    action: ActionType
    note: str | None = Field(None, max_length=1000)
    step_no: int | None = Field(None, ge=1, le=5, description="Required for HIGH_PRIORITY_STEP")
    assignee_user_id: PositiveInt | None = Field(None, description="Required for ASSIGN")
    outcome: Outcome | None = Field(None, description="Outcome recorded when the 5th high-priority step closes it")

    @model_validator(mode="after")
    def _fields_for_action(self):
        if self.action == "HIGH_PRIORITY_STEP" and self.step_no is None:
            raise ValueError("stepNo is required for HIGH_PRIORITY_STEP")
        if self.action != "HIGH_PRIORITY_STEP" and self.step_no is not None:
            raise ValueError("stepNo is only allowed for HIGH_PRIORITY_STEP")
        if self.action == "ASSIGN" and self.assignee_user_id is None:
            raise ValueError("assigneeUserId is required for ASSIGN")
        return self


class AlarmRuleBase(CamelModel):
    handling_mode: Literal["HIDE", "DISPLAY_ONLY", "PROCESS", "HIGH_PRIORITY"] | None = None
    process_mode: Literal["AUTO", "MANUAL"] | None = None
    auto_outcome: Outcome | None = None
    popup_enabled: bool | None = None
    notify_enabled: bool | None = None
    sound_enabled: bool | None = None
    group_id: PositiveInt | None = None
    priority: int | None = Field(None, ge=0, le=32767)
    enabled: bool | None = None
    alarm_type_ids: list[PositiveInt] | None = Field(None, min_length=1, max_length=500)


class AlarmRuleCreate(AlarmRuleBase):
    name: str = Field(min_length=1, max_length=120)
    handling_mode: Literal["HIDE", "DISPLAY_ONLY", "PROCESS", "HIGH_PRIORITY"]
    alarm_type_ids: list[PositiveInt] = Field(min_length=1, max_length=500)


class AlarmRuleUpdate(AlarmRuleBase):
    name: str | None = Field(None, min_length=1, max_length=120)


class LocalAlarmQuery(PageIn):
    start_time: datetime | None = None
    end_time: datetime | None = None
    statuses: list[Literal["NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "DISMISSED"]] | None = None
    device_ids: list[PositiveInt] | None = Field(None, max_length=1000)
    alarm_type_ids: list[PositiveInt] | None = Field(None, max_length=500)
    include_hidden: bool = False


class PopupSettingsIn(CamelModel):
    popup_close_sec: int = Field(ge=1, le=3600)
    popup_max: int = Field(ge=1, le=100)
