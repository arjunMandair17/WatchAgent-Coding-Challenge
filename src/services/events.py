from typing import List, Optional

from sqlalchemy import select

from ..db.models import SignificantEvent
from ..db.session import SessionLocal
from ..schemas import Event


async def get_recent_events(city: Optional[str], limit: int) -> List[Event]:
    """Fetch recent significant weather events from the database."""
    db = SessionLocal()
    try:
        stmt = select(SignificantEvent)
        if city:
            stmt = stmt.where(SignificantEvent.city == city)
        stmt = stmt.order_by(SignificantEvent.recorded_at.desc()).limit(limit)
        return [Event.model_validate(row) for row in db.scalars(stmt).all()]
    finally:
        db.close()
