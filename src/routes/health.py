from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return a simple health check with storage counts."""
    # This function returns the API health status and current storage counts.
    # TODO: Replace these stubbed values with real storage counts.
    return HealthResponse(status="ok", readings_stored=0, events_stored=0)
