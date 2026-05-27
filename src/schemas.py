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

    id: int = Field(..., description="Unique identifier for the reading.")
    city: str = Field(..., description="City associated with the reading.")
    temperature_c: float = Field(..., description="Temperature in degrees Celsius.")
    humidity: float = Field(..., description="Relative humidity as a fraction between 0 and 1.")
    recorded_at: datetime = Field(..., description="Timestamp when the reading was recorded.")


class ReadingsResponse(StrictBaseModel):
    """Response model for the `/readings` endpoint."""

    readings: List[Reading] = Field(..., description="List of readings, most recent first.")


class Event(StrictBaseModel):
    """Represents a single spike or notable weather event for a city."""

    id: int = Field(..., description="Unique identifier for the event.")
    city: str = Field(..., description="City where the event occurred.")
    spike_type: str = Field(..., description="Type of spike or unusual weather event.")
    magnitude: float = Field(..., description="Magnitude or intensity of the event.")
    detected_at: datetime = Field(..., description="Timestamp when the event was detected.")
    description: Optional[str] = Field(
        None,
        description="Human-readable description or context for the event.",
    )

class EventsResponse(StrictBaseModel):
    """Response model for the `/events` endpoint."""

    events: List[Event] = Field(..., description="List of events, most recent first.")
