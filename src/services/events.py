from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..schemas import Event


# This function retrieves recent spike or event records for a given city from the underlying data source.
async def get_recent_events(city: Optional[str], limit: int) -> List[Event]:
    """
    Fetch recent spike or event data for a city.

    This is a stub implementation. Replace it with real integration that uses the
    project's analyze_weather MCP skill and underlying data store.
    """
    now = datetime.now(timezone.utc)

    # TODO: Replace stubbed data with a real call to the analyze_weather MCP skill
    #       and underlying storage for the specified city and limit.
    dummy_events: List[Event] = [
        Event(
            id=1,
            city=city or "Ottawa",
            spike_type="temperature_spike",
            magnitude=7.3,
            detected_at=now - timedelta(minutes=5),
            description="Sudden temperature increase detected.",
        ),
        Event(
            id=2,
            city="Toronto",
            spike_type="humidity_spike",
            magnitude=0.2,
            detected_at=now - timedelta(minutes=30),
            description="Sudden humidity increase detected.",
        ),
    ]

    filtered_events = [event for event in dummy_events if event.city == city] if city else dummy_events
    filtered_events.sort(key=lambda event: event.detected_at, reverse=True)
    return filtered_events[:limit]
