from fastapi import FastAPI

from .routes.events import router as events_router
from .routes.health import router as health_router
from .routes.readings import router as readings_router


# This function initializes the FastAPI application instance and registers all API routers.
app = FastAPI(
    title="Nokia Weather API",
    version="1.0.0",
    description="API for tracking strange weather activity across three cities.",
)


# This function configures the FastAPI application to include all route modules.
app.include_router(health_router)
app.include_router(readings_router)
app.include_router(events_router)
