from datetime import datetime, timezone
from typing import List

from ..schemas import Reading


# This function retrieves recent raw weather readings for a given city from the underlying data source.
async def get_recent_readings(city: str, limit: int) -> List[Reading]:
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
            city=city,
            temperature_c=20.5,
            humidity=0.65,
            recorded_at=now,
        )
    ]

    return dummy_readings[:limit]
