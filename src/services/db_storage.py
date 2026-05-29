from sqlalchemy.orm import Session
from ..db.models import WeatherReading, SignificantEvent
import logging

logger = logging.getLogger(__name__)

def store_weather_data(weather_data: WeatherReading, event: SignificantEvent , db: Session ) -> None:
    """Store weather data and significant events in the database."""
    db.add(weather_data)
    db.flush()
    if event is not None:
        event.weather_readings = [weather_data]
        db.add(event)
    db.commit()
    if event is not None:
        logger.info("Significant event detected: %s", event)
