from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, TimeRangeIn


class RecordQueryIn(TimeRangeIn):
    channel: int | None = Field(None, ge=0, le=16, description="vendor channelNo (optional)")


class RecordUploadIn(TimeRangeIn):
    channel: int = Field(ge=1, le=16)
    data_type: Literal[0, 1, 2] = Field(0, description="0 audio+video, 1 audio, 2 video")
    stream_type: Literal[1, 2] = Field(1, description="1 main stream, 2 sub stream")


class LiveSessionIn(CamelModel):
    auto_wake: bool = Field(True, description="Send the wake command when the vendor reports ACC off")
