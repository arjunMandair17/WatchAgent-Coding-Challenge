import asyncio
import logging

import requests
from datetime import datetime, timezone
from sqlalchemy import select

from ..db.models import WeatherReading
from ..db.schemas import WeatherReadingCreate
from ..db.session import SessionLocal
from .event_detection import detect_significant_events

logger = logging.getLogger(__name__)


def city_for_coords(lat: float, lon: float) -> str:
    """Return the city name for known polling coordinates."""

    if lat == 45.42 and lon == -75.69:
        return "Ottawa"
    if lat == 43.70 and lon == -79.42:
        return "Toronto"
    if lat == 49.25 and lon == -123.12:
        return "Vancouver"
    raise ValueError("Invalid latitude and longitude")


def request_weather_data(lat: float, lon: float) -> tuple[dict, str]:
    """
    Request the weather API for the latest weather data for a given city.
    """

    city = city_for_coords(lat, lon)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code&wind_speed_unit=kmh&timezone=auto"

    response = requests.get(url)
    if not response.ok:
        logger.error("%s weather poll failed with HTTP status %s", city, response.status_code)
        response.raise_for_status()
    return response.json(), city


async def poll_weather_data(lat: float, lon: float) -> None:
    """Poll weather data for a city and store only when a new timestamp appears."""

    city = city_for_coords(lat, lon)

    while True:
        try:
            data, city = await asyncio.to_thread(request_weather_data, lat, lon)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            logger.error("%s weather poll failed with HTTP status %s", city, status)
            await asyncio.sleep(300)
            continue
        except requests.RequestException as exc:
            logger.error("%s weather poll failed: %s", city, exc)
            await asyncio.sleep(300)
            continue

        recorded_at = datetime.fromisoformat(data["current"]["time"])
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        payload = WeatherReadingCreate(
            city=city,
            recorded_at=recorded_at,
            temperature_2m=data["current"]["temperature_2m"],
            apparent_temperature=data["current"]["apparent_temperature"],
            precipitation=data["current"]["precipitation"],
            wind_speed_10m=data["current"]["wind_speed_10m"],
            weather_code=data["current"]["weather_code"],
            source="open-meteo",
        )

        db = SessionLocal()
        try:
            exists = db.scalar(
                select(WeatherReading.id).where(
                    WeatherReading.city == city,
                    WeatherReading.recorded_at == recorded_at,
                )
            )
            if exists is None:
                reading = WeatherReading(**payload.model_dump())
                event = detect_significant_events(reading, db)
                db.add(reading)
                db.flush()
                if event is not None:
                    event.weather_readings = [reading]
                    db.add(event)
                db.commit()
                if event is not None:
                    logger.info("Significant event detected: %s", event)

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        await asyncio.sleep(300)  # sleep for 300 seconds
