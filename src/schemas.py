from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    """Base model that forbids extra fields in all derived models."""

    model_config = ConfigDict(extra="forbid")


class HealthData(StrictBaseModel):
    """Represents basic health and metadata for the API service."""

    status: str = Field(..., description="Overall health status of the API, e.g., 'ok'.")
    service: str = Field(..., description="Name of the service.")
    version: str = Field(..., description="Version of the running service.")
    timestamp: datetime = Field(..., description="Timestamp when the health was evaluated.")


class HealthResponse(StrictBaseModel):
    """Standard envelope for the health check response."""

    success: bool = Field(..., description="Indicates whether the request was successful.")
    data: HealthData = Field(..., description="Health information payload.")
    error: Optional[str] = Field(
        None,
        description="Error message if the request failed; otherwise null.",
    )


class Reading(StrictBaseModel):
    """Represents a single raw weather reading for a city."""

    id: int = Field(..., description="Unique identifier for the reading.")
    city: str = Field(..., description="City associated with the reading.")
    temperature_c: float = Field(..., description="Temperature in degrees Celsius.")
    humidity: float = Field(..., description="Relative humidity as a fraction between 0 and 1.")
    recorded_at: datetime = Field(..., description="Timestamp when the reading was recorded.")


class ReadingsData(StrictBaseModel):
    """Container for a list of raw readings for a specific city."""

    city: str = Field(..., description="City for which readings are returned.")
    readings: List[Reading] = Field(..., description="List of recent raw readings for the city.")


class ReadingsResponse(StrictBaseModel):
    """Standard envelope for the readings endpoint response."""

    success: bool = Field(..., description="Indicates whether the request was successful.")
    data: ReadingsData = Field(..., description="Readings payload for the specified city.")
    error: Optional[str] = Field(
        None,
        description="Error message if the request failed; otherwise null.",
    )


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


class EventsData(StrictBaseModel):
    """Container for a list of spike or event records for a specific city."""

    city: str = Field(..., description="City for which events are returned.")
    events: List[Event] = Field(..., description="List of spike or event records for the city.")


class EventsResponse(StrictBaseModel):
    """Standard envelope for the events endpoint response."""

    success: bool = Field(..., description="Indicates whether the request was successful.")
    data: EventsData = Field(..., description="Events payload for the specified city.")
    error: Optional[str] = Field(
        None,
        description="Error message if the request failed; otherwise null.",
    )
