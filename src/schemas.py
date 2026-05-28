from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    """Base model that forbids extra fields in all derived models."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictBaseModel):
    """Response model for the `/health` endpoint."""

    status: str = Field(..., description="Overall health status of the API, e.g., 'ok'.")
    readings_stored: int = Field(..., ge=0, description="Number of stored readings.")
    events_stored: int = Field(..., ge=0, description="Number of stored notable events.")


class Reading(StrictBaseModel):
    """Represents a single raw weather reading for a city."""

    id: int
    city: str
    recorded_at: datetime
    temperature_2m: float
    apparent_temperature: float
    precipitation: float
    wind_speed_10m: float
    weather_code: int
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ReadingsResponse(StrictBaseModel):
    """Response model for the `/readings` endpoint."""

    readings: List[Reading] = Field(..., description="List of readings, most recent first.")


class Event(StrictBaseModel):
    """Represents a single spike or notable weather event for a city."""

    id: int
    event_type: str
    metric: str
    severity: int
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rule_triggered: str
    actual_value: float
    expected_value: float
    event_timestamp: datetime
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EventsResponse(StrictBaseModel):
    """Response model for the `/events` endpoint."""

    events: List[Event] = Field(..., description="List of events, most recent first.")
