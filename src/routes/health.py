from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import SignificantEvent, WeatherReading
from ..db.session import get_db
from ..schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Return a simple health check with storage counts."""
    readings_stored = db.scalar(select(func.count()).select_from(WeatherReading)) or 0
    events_stored = db.scalar(select(func.count()).select_from(SignificantEvent)) or 0
    return HealthResponse(
        status="ok",
        readings_stored=readings_stored,
        events_stored=events_stored,
    )
