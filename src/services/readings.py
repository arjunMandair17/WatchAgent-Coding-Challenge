from typing import List, Optional

from sqlalchemy import select

from ..db.models import WeatherReading
from ..db.session import SessionLocal
from ..schemas import Reading


async def get_recent_readings(city: Optional[str], limit: int) -> List[Reading]:
    """Fetch recent raw weather readings from the database."""
    db = SessionLocal()
    try:
        stmt = select(WeatherReading)
        if city:
            stmt = stmt.where(WeatherReading.city == city)
        stmt = stmt.order_by(WeatherReading.recorded_at.desc()).limit(limit)
        return [Reading.model_validate(row) for row in db.scalars(stmt).all()]
    finally:
        db.close()
