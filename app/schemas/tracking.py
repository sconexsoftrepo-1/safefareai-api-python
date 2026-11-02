from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from app.schemas.common import CamelModel, TimeRangeIn


class TrackOptions(CamelModel):
    filter_parking_minutes: int = Field(0, ge=0, le=1440, description="vendor filterTime (minutes)")
    filter_stops: bool = Field(False, description="vendor stopStatus: true -> 0 (filter), false -> 1 (keep)")
    position_filter: Literal[0, 1, 2] = Field(
        0, description="vendor posStatus: 0 drop non-located points, 1 keep all, 2 drop located points")


class ReminderIn(CamelModel):
    rule_type: Literal[1, 2, 5]
    display_usage: Literal[8, 32] = Field(description="8 TTS broadcast, 32 custom voice")
    text: str | None = Field(None, max_length=300, description="TTS text, required when displayUsage = 8")
    voice_id: PositiveInt | None = Field(None, description="dbo.custom_voices.id, required when displayUsage = 32")
    play_count: int = Field(1, ge=1, le=10)

    @model_validator(mode="after")
    def _content(self):
        if self.display_usage == 8 and not (self.text and self.text.strip()):
            raise ValueError("text is required for TTS reminders (displayUsage 8)")
        if self.display_usage == 32 and self.voice_id is None:
            raise ValueError("voiceId is required for custom voice reminders (displayUsage 32)")
        return self


class FenceFromTrackIn(TimeRangeIn, TrackOptions):
    device_id: PositiveInt
    name: str = Field(min_length=1, max_length=150)
    rule_types: list[Literal[1, 2, 5]] = Field(
        min_length=1, max_length=3, description="Line rules: 1 overspeed, 2 offset, 5 route completion")
    max_speed_kmh: int | None = Field(None, ge=1, le=300, description="Required for rule 1")
    offset_meters: int | None = Field(None, ge=1, le=32767, description="Required for rule 2")
    completion_pct: int | None = Field(None, ge=0, le=100, description="Required for rule 5")
    color: int = Field(0, ge=0, le=5)
    area_type: int = Field(0, ge=0, le=9)
    bind_type: Literal["DEVICE", "GROUP"] | None = None
    bind_ids: list[PositiveInt] = Field(default_factory=list, max_length=1000)
    reminders: list[ReminderIn] = Field(default_factory=list, max_length=3)
    max_points: int = Field(200, ge=2, le=1000)
    position_filter: Literal[0, 1, 2] = 0  # a fence needs located points only

    @model_validator(mode="after")
    def _rules(self):
        if len(set(self.rule_types)) != len(self.rule_types):
            raise ValueError("ruleTypes must be unique")
        if 1 in self.rule_types and self.max_speed_kmh is None:
            raise ValueError("maxSpeedKmh is required for rule 1 (line overspeed)")
        if 2 in self.rule_types and self.offset_meters is None:
            raise ValueError("offsetMeters is required for rule 2 (line offset)")
        if 5 in self.rule_types and self.completion_pct is None:
            raise ValueError("completionPct is required for rule 5 (route completion)")
        if bool(self.bind_type) != bool(self.bind_ids):
            raise ValueError("bindType and bindIds must be supplied together")
        for reminder in self.reminders:
            if reminder.rule_type not in self.rule_types:
                raise ValueError("each reminder ruleType must be one of ruleTypes")
        if len({r.rule_type for r in self.reminders}) != len(self.reminders):
            raise ValueError("only one reminder per ruleType is allowed")
        return self
