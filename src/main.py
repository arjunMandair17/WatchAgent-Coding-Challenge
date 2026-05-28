from fastapi import FastAPI


import asyncio
from .services.poll import poll_weather_data

from .routes.events import router as events_router
from .routes.health import router as health_router
from .routes.readings import router as readings_router


# This function initializes the FastAPI application instance and registers all API routers.
app = FastAPI(
    title="Nokia Weather API",
    version="1.0.0",
    description="API for tracking strange weather activity across three cities.",
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_weather_data(45.42, -75.69)) # Ottawa
    asyncio.create_task(poll_weather_data(43.70, -79.42)) # Toronto
    asyncio.create_task(poll_weather_data(49.25, -123.12)) # Vancouver


# This function configures the FastAPI application to include all route modules.
app.include_router(health_router)
app.include_router(readings_router)
app.include_router(events_router)
