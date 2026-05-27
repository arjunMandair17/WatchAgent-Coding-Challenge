from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictBaseModel(BaseModel):
    """Base model that forbids extra fields in all derived models."""

    model_config = ConfigDict(extra="forbid")


class WeatherReadingBase(StrictBaseModel):
    """Shared fields for weather reading schemas."""

    city: str = Field(..., min_length=1, max_length=120)
    recorded_at: datetime
    temperature_2m: float
    apparent_temperature: float
    precipitation: float
    wind_speed_10m: float
    weather_code: int
    source: str = Field(..., min_length=1, max_length=120)

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_not_future(cls, v: datetime) -> datetime:
        """Reject readings with a recorded_at timestamp in the future."""

        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        if v > now:
            raise ValueError("recorded_at cannot be in the future")
        return v

    @field_validator("precipitation", "wind_speed_10m")
    @classmethod
    def non_negative_floats(cls, v: float) -> float:
        """Reject non-negative metrics that cannot be below zero."""

        if v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("weather_code")
    @classmethod
    def weather_code_non_negative(cls, v: int) -> int:
        """Reject weather codes that cannot be negative."""

        if v < 0:
            raise ValueError("weather_code must be >= 0")
        return v

    @model_validator(mode="after")
    def temperature_plausible(self) -> "WeatherReadingBase":
        """Reject extreme outlier temperatures that are almost certainly invalid."""

        for name in ("temperature_2m", "apparent_temperature"):
            value = getattr(self, name)
            if value < -150 or value > 150:
                raise ValueError(f"{name} is outside plausible bounds")
        return self


class WeatherReadingCreate(WeatherReadingBase):
    """Schema for creating a new weather reading."""


class WeatherReadingRead(WeatherReadingBase):
    """Schema for reading a weather reading from the database."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class SignificantEventBase(StrictBaseModel):
    """Shared fields for significant event schemas (what/where/why/when)."""

    event_type: str = Field(..., min_length=1, max_length=80)
    metric: str = Field(..., min_length=1, max_length=80)
    severity: int = Field(..., ge=0)

    city: str = Field(..., min_length=1, max_length=120)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    rule_triggered: str = Field(..., min_length=1, max_length=500)
    actual_value: float
    expected_value: float

    event_timestamp: datetime
    recorded_at: datetime

    @field_validator("event_timestamp", "recorded_at")
    @classmethod
    def timestamps_timezone_aware_and_not_future(cls, v: datetime) -> datetime:
        """Reject event timestamps that are naive or in the future."""

        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if v > now:
            raise ValueError("timestamp cannot be in the future")
        return v


class SignificantEventCreate(SignificantEventBase):
    """Schema for creating a significant event."""

    weather_reading_ids: List[int] = Field(
        default_factory=list,
        description="IDs of raw readings that contributed to this event.",
    )


class SignificantEventRead(SignificantEventBase):
    """Schema for reading a significant event from the database."""

    id: int
    created_at: datetime
    updated_at: datetime
    weather_reading_ids: List[int] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", from_attributes=True)

