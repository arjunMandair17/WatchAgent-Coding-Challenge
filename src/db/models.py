from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class WeatherReading(Base, TimestampMixin):
    """Stores raw weather readings collected from an upstream weather API."""

    __tablename__ = "weather_readings"
    __table_args__ = (
        CheckConstraint("precipitation >= 0", name="ck_weather_readings_precipitation_gte_0"),
        CheckConstraint("wind_speed_10m >= 0", name="ck_weather_readings_wind_speed_gte_0"),
        CheckConstraint("weather_code >= 0", name="ck_weather_readings_weather_code_gte_0"),
        Index("ix_weather_readings_city", "city"),
        Index("ix_weather_readings_recorded_at", "recorded_at"),
        Index("ix_weather_readings_city_recorded_at", "city", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    city: Mapped[str] = mapped_column(String(120), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    temperature_2m: Mapped[float] = mapped_column(Float, nullable=False)
    apparent_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_10m: Mapped[float] = mapped_column(Float, nullable=False)
    weather_code: Mapped[int] = mapped_column(Integer, nullable=False)

    source: Mapped[str] = mapped_column(String(120), nullable=False)

    significant_events: Mapped[List[SignificantEvent]] = relationship(
        back_populates="weather_readings",
        secondary="significant_event_readings",
        passive_deletes=True,
    )


class SignificantEvent(Base, TimestampMixin):
    """Stores detected anomalies/spikes, including what/where/why/when context."""

    __tablename__ = "significant_events"
    __table_args__ = (
        CheckConstraint("severity >= 0", name="ck_significant_events_severity_gte_0"),
        Index("ix_significant_events_city", "city"),
        Index("ix_significant_events_event_timestamp", "event_timestamp"),
        Index("ix_significant_events_recorded_at", "recorded_at"),
        Index("ix_significant_events_city_event_timestamp", "city", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)

    city: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    rule_triggered: Mapped[str] = mapped_column(String(500), nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    expected_value: Mapped[float] = mapped_column(Float, nullable=False)

    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    weather_readings: Mapped[List[WeatherReading]] = relationship(
        back_populates="significant_events",
        secondary="significant_event_readings",
        passive_deletes=True,
    )


class SignificantEventReading(Base):
    """Join table linking significant events to one or more raw readings."""

    __tablename__ = "significant_event_readings"
    __table_args__ = (
        Index("ix_significant_event_readings_event_id", "significant_event_id"),
        Index("ix_significant_event_readings_weather_reading_id", "weather_reading_id"),
    )

    significant_event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("significant_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weather_reading_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("weather_readings.id", ondelete="RESTRICT"),
        primary_key=True,
    )

