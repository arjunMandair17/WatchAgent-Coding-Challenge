from fastapi import APIRouter, Query
from typing import Optional
from ..schemas import EventsData, EventsResponse
from ..services.events import get_recent_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventsResponse)
async def get_events(
    city: str = Query(..., description="City to retrieve spike or event data for."),
    limit: Optional[int] = Query(
        50,
        gt=0,
        le=1000,
        description="Maximum number of recent events to return.",
    ),
) -> EventsResponse:
    """Return recent spike or event data for the specified city."""
    # This function returns recent spike or event data for a given city, limited by the specified count.
    events = await get_recent_events(city=city, limit=limit)

    data = EventsData(city=city, events=events)

    return EventsResponse(success=True, data=data, error=None)
