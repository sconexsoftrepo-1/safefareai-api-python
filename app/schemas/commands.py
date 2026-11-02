"""Device command payloads (vendor 8.20 - 8.23, 8.29, 8.30). Fields mirror the documented vendor bodies."""
from typing import Literal

from pydantic import Field, PositiveInt, field_validator, model_validator

from app.schemas.common import CamelModel, TimeRangeIn


class CommandTargets(CamelModel):
    device_ids: list[PositiveInt] = Field(min_length=1, max_length=1000,
                                          description="Internal device ids; up to 1000 per batch")

    @field_validator("device_ids")
    @classmethod
    def _unique(cls, value):
        return list(dict.fromkeys(value))


class FuelScale(CamelModel):
    oil_no: int = Field(ge=1, le=8, description="Fuel route number")
    oil_number: float = Field(ge=0, description="Oil quantity")
    scale: float = Field(ge=0, description="Scale value")
    unit: Literal[1, 2] = Field(description="1 litre, 2 gallon")


class FuelCalibrationIn(CommandTargets):
    scales: list[FuelScale] = Field(min_length=1, max_length=100)


class TemperatureParam(CamelModel):
    high: float = Field(ge=-100, le=200)
    low: float = Field(ge=-100, le=200)
    number: int = Field(ge=1, le=16, description="Channel number")

    @model_validator(mode="after")
    def _ordered(self):
        if self.low >= self.high:
            raise ValueError("low must be below high")
        return self


class TemperatureCalibrationIn(CommandTargets):
    name: str = Field(min_length=1, max_length=60)
    temperature_param: list[TemperatureParam] = Field(min_length=1, max_length=16)


class LoadInfo(CamelModel):
    channel: int = Field(ge=1, le=16)
    load_ad: float = Field(ge=0, description="Full-load AD value")
    load_quality: float = Field(ge=0, description="Full-load vehicle mass (tons)")
    no_load_ad: float = Field(ge=0, description="No-load AD value")
    no_load_quality: float = Field(ge=0, description="Empty vehicle mass (tons)")


class LoadCalibrationIn(CommandTargets):
    load_info_list: list[LoadInfo] = Field(min_length=1, max_length=16)


class AinData(CamelModel):
    ad_value: float = Field(ge=0)
    channel: int = Field(ge=1, le=16)
    fuel_value: float = Field(ge=0)
    full_ad_value: float = Field(ge=0)
    full_fuel_value: float = Field(ge=0)
    unit: Literal[1, 2] = Field(description="1 litre, 2 gallon")


class SensorReq(CamelModel):
    data: list[AinData] = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=60)
    sensor: Literal[0, 1, 2, 3] = Field(description="0 oil rod, 1 load, 2 temperature, 3 custom")


class AinCalibrationIn(CommandTargets):
    sensor_req: SensorReq


class PassThroughIn(CommandTargets):
    pass_through_type: int = Field(ge=0, le=65535)
    content: str = Field(min_length=2, max_length=2048, description="Hexadecimal payload")

    @field_validator("content")
    @classmethod
    def _hex(cls, value: str):
        value = value.strip().replace(" ", "")
        if len(value) % 2 or any(c not in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("content must be an even-length hexadecimal string")
        return value.upper()


class PassThroughQueryIn(CommandTargets, TimeRangeIn):
    pass_through_type: int = Field(ge=0, le=65535)
