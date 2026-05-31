"""Tests for the Open-Meteo poller and reading deduplication."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import delete, func, select

from src.db.models import WeatherReading
from src.db.session import SessionLocal
from src.services.poll import poll_weather_data

OTTAWA_LAT = 45.42
OTTAWA_LON = -75.69
RECORDED_TIME = "2026-05-29T15:00:00+00:00"

MOCK_API_RESPONSE = {
    "current": {
        "time": RECORDED_TIME,
        "temperature_2m": 12.0,
        "apparent_temperature": 11.0,
        "precipitation": 0.0,
        "wind_speed_10m": 8.0,
        "weather_code": 0,
    }
}


class _StopPollLoop(Exception):
    """Raised from mocked sleep to exit poll_weather_data after two iterations."""


def _mock_http_response() -> MagicMock:
    """Build a fake requests.Response for Open-Meteo."""

    response = MagicMock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = MOCK_API_RESPONSE
    response.raise_for_status = MagicMock()
    return response


def test_poll_deduplicates_same_timestamp_reading():
    """Mock API returning the same reading twice; only one row is stored."""

    sleep_calls = 0

    async def fake_sleep(_seconds: int) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise _StopPollLoop()

    with (
        patch("src.services.poll.requests.get", return_value=_mock_http_response()),
        patch("src.services.poll.asyncio.sleep", side_effect=fake_sleep),
    ):
        with pytest.raises(_StopPollLoop):
            asyncio.run(poll_weather_data(OTTAWA_LAT, OTTAWA_LON))

    recorded_at = datetime.fromisoformat(RECORDED_TIME)
    db = SessionLocal()
    try:
        count = db.scalar(
            select(func.count())
            .select_from(WeatherReading)
            .where(
                WeatherReading.city == "Ottawa",
                WeatherReading.recorded_at == recorded_at,
                WeatherReading.source == "open-meteo",
            )
        )
        assert count == 1
    finally:
        db.execute(
            delete(WeatherReading).where(
                WeatherReading.city == "Ottawa",
                WeatherReading.recorded_at == recorded_at,
                WeatherReading.source == "open-meteo",
            )
        )
        db.commit()
        db.close()
