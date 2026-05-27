from datetime import datetime, timezone

from fastapi import APIRouter

from ..schemas import HealthData, HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return a simple health check with basic service metadata."""
    # This function returns the API health status and basic service metadata.
    now = datetime.now(timezone.utc)

    health_data = HealthData(
        status="ok",
        service="nokia-weather-api",
        version="1.0.0",
        timestamp=now,
    )

    return HealthResponse(success=True, data=health_data, error=None)
