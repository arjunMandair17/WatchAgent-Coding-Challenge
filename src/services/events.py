from datetime import datetime, timedelta, timezone
from typing import List

from ..schemas import Event


# This function retrieves recent spike or event records for a given city from the underlying data source.
async def get_recent_events(city: str, limit: int) -> List[Event]:
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
            city=city,
            spike_type="temperature_spike",
            magnitude=7.3,
            detected_at=now - timedelta(minutes=5),
            description="Sudden temperature increase detected.",
        )
    ]

    return dummy_events[:limit]
