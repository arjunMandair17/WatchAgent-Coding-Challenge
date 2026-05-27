from typing import Optional

from fastapi import APIRouter, Query

from ..schemas import EventsResponse
from ..services.events import get_recent_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventsResponse)
async def get_events(
    city: Optional[str] = Query(
        None,
        description="Optional city filter for events, e.g., 'Ottawa'.",
    ),
    limit: int = Query(
        50,
        gt=0,
        le=1000,
        description="Maximum number of recent events to return.",
    ),
) -> EventsResponse:
    """Return recent spike or event data for the specified city."""
    # This function returns recent spike or event data for a given city, limited by the specified count.
    events = await get_recent_events(city=city, limit=limit)
    return EventsResponse(events=events)
