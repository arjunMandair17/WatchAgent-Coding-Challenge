from fastapi import APIRouter, Query

from ..schemas import ReadingsData, ReadingsResponse
from ..services.readings import get_recent_readings

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("", response_model=ReadingsResponse)
async def get_readings(
    city: str = Query(..., description="City to retrieve readings for, e.g., 'Toronto'."),
    limit: int = Query(
        100,
        gt=0,
        le=1000,
        description="Maximum number of recent readings to return.",
    ),
) -> ReadingsResponse:
    """Return recent raw weather readings for the specified city."""
    # This function returns recent raw weather readings for a given city, limited by the specified count.
    readings = await get_recent_readings(city=city, limit=limit)

    data = ReadingsData(city=city, readings=readings)

    return ReadingsResponse(success=True, data=data, error=None)
