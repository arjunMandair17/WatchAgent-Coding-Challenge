from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas import ReadingsResponse
from ..services.readings import get_recent_readings

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("", response_model=ReadingsResponse)
async def get_readings(
    city: Optional[str] = Query(
        None,
        description="Optional city filter for readings, e.g., 'Ottawa'.",
    ),
    limit: int = Query(
        50,
        gt=0,
        le=1000,
        description="Maximum number of recent readings to return.",
    ),
) -> ReadingsResponse:
    """Return recent raw weather readings for the specified city."""
    if city is not None and city not in ("Ottawa", "Toronto", "Vancouver"):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown city '{city}'. Must be one of: Ottawa, Toronto, Vancouver",
        )
    readings = await get_recent_readings(city=city, limit=limit)
    return ReadingsResponse(readings=readings)
