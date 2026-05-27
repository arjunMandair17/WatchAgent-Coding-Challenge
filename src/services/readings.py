from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..schemas import Reading


# This function retrieves recent raw weather readings for a given city from the underlying data source.
async def get_recent_readings(city: Optional[str], limit: int) -> List[Reading]:
    """
    Fetch recent raw weather readings for a city.

    This is a stub implementation. Replace it with real integration that uses the
    project's analyze_weather MCP skill and underlying data store.
    """
    now = datetime.now(timezone.utc)

    # TODO: Replace stubbed data with a real call to the analyze_weather MCP skill
    #       and underlying storage for the specified city and limit.
    dummy_readings: List[Reading] = [
        Reading(
            id=1,
            city=city or "Ottawa",
            temperature_c=20.5,
            humidity=0.65,
            recorded_at=now,
        ),
        Reading(
            id=2,
            city="Toronto",
            temperature_c=18.2,
            humidity=0.72,
            recorded_at=now - timedelta(minutes=10),
        ),
    ]

    filtered_readings = (
        [reading for reading in dummy_readings if reading.city == city] if city else dummy_readings
    )
    filtered_readings.sort(key=lambda reading: reading.recorded_at, reverse=True)
    return filtered_readings[:limit]
