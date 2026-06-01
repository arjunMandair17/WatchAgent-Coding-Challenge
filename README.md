# WatchAgent: Weather Monitor & AI Assistant
My submission to Nokia for the Weather Monitor API that uses python and Cursor Pro.

## System Overview
The aim of this project is to create an API that not only reads in weather data from three major Canadian cities through OpenMeteo, but also displays the ability to understand and parse data from an API. This is done through my event detection logic which checks against previously stored readings and city averages to determine if the current reading is abnormal in context.

## Architecture

The service runs as two Docker containers: a **FastAPI API** process and **PostgreSQL**. On startup, the API launches three long-running pollers (one per city). Each poll cycle fetches current conditions from Open-Meteo, deduplicates by `(city, recorded_at)`, runs event detection against history already in the database, and persists new readings and optional significant events.

### Component diagram

```
                    ┌─────────────────────┐
                    │   Open-Meteo API    │
                    │  (no API key)       │
                    └──────────┬──────────┘
                               │ HTTPS GET /v1/forecast
                               │ (every 5 min per city)
                               ▼
┌──────────────┐    ┌──────────────────────────────────────────────┐
│   Client     │    │              api container                    │
│  (browser,   │    │  ┌─────────────────────────────────────────┐ │
│   curl)      │    │  │  poll.py (×3 asyncio tasks)             │ │
└──────┬───────┘    │  │  Ottawa · Toronto · Vancouver           │ │
       │ HTTP        │  └───────────────┬─────────────────────────┘ │
       │ :8000       │                  │ new timestamp only         │
       ▼             │                  ▼                            │
┌──────────────┐    │  ┌──────────────────────────┐                 │
│  FastAPI     │◄───┤  │  event_detection.py      │                 │
│  routes      │    │  │  (thresholds, 12h avg, │                 │
│  /health     │    │  │   severe WMO codes)      │                 │
│  /readings   │    │  └───────────────┬──────────┘                 │
│  /events     │    │                  │                            │
└──────┬───────┘    │                  ▼                            │
       │             │  ┌──────────────────────────┐                 │
       │             │  │  db_storage.py           │                 │
       │             │  │  SQLAlchemy ORM          │                 │
       │             │  └───────────────┬──────────┘                 │
       │             └──────────────────┼──────────────────────────────┘
       │                                │ SQL (psycopg)
       │                                ▼
       │             ┌──────────────────────────────────────────────┐
       └────────────►│           postgres container                  │
                     │  weather_readings                           │
                     │  significant_events                         │
                     │  significant_event_readings (join)        │
                     │  volume: postgres_data (persists restarts)  │
                     └──────────────────────────────────────────────┘
```

### Request path (read)

| Step | Component | Role |
|------|-----------|------|
| 1 | `routes/*.py` | HTTP handlers, query params (`city`, `limit`) |
| 2 | `services/readings.py`, `services/events.py` | Load and shape rows for the API |
| 3 | `schemas.py` | Pydantic response models (`ReadingsResponse`, `EventsResponse`) |
| 4 | PostgreSQL | Source of truth for stored readings and events |

### Ingest path (write)

| Step | Component | Role |
|------|-----------|------|
| 1 | `poll.py` | Fetch Open-Meteo, skip duplicate timestamps |
| 2 | `event_detection.py` | Compare reading to last row and 12h city averages |
| 3 | `db_storage.py` | Insert reading; link event via join table if detected |
| 4 | Alembic (`migrations/`) | Schema applied on container startup |

### Project layout

```
src/
  main.py              # FastAPI app, starts pollers on startup
  config.py            # DATABASE_URL / POSTGRES_* from .env
  routes/              # /health, /readings, /events
  services/            # poll, event_detection, db_storage, query helpers
  db/                  # ORM models, session, validation schemas
migrations/            # Alembic revisions
tests/                 # pytest (poll dedupe, detection, API, DB)
.cursor/               # rules, agents, data-analysis skill
```

## Setup and Run Instructions

- Once the repo has been forked, the env variables must be copied using the command:
```bash
cp .env.example .env   
```

- After this, you can run the two docker containers with the command: 
```bash
docker compose up --build   
```

- At this point, the DB and API containers will be up and running, and you can access the API from localhost on port 8000, via any of the outlined endpoints

- If you wish to close the docker containers, this can be done via the command: 
```bash
docker compose down
```
- This command persists SQL data after removal, if you wish to keep data between container restarts simply add "-v" to the end of the command


## API Reference

Base URL (with Docker running): `http://localhost:8000`

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Monitored cities: **Ottawa**, **Toronto**, **Vancouver** (populated by background pollers).

---

### GET /health

Returns service status and how many readings and events are stored in the database.

**Response:** `200 OK`

```json
{
  "status": "ok",
  "readings_stored": 12,
  "events_stored": 3
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"ok"` when the API and DB are reachable |
| `readings_stored` | integer | Total rows in `weather_readings` |
| `events_stored` | integer | Total rows in `significant_events` |

**Example**

```bash
curl -s http://localhost:8000/health
```

---

### GET /readings

Returns recent raw weather readings, newest first.

**Query parameters**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `city` | No | — | Filter by city name (e.g. `Ottawa`) |
| `limit` | No | `50` | Max rows to return (1–1000) |

**Response:** `200 OK`

```json
{
  "readings": [
    {
      "id": 1,
      "city": "Ottawa",
      "recorded_at": "2026-05-29T15:00:00Z",
      "temperature_2m": 12.5,
      "apparent_temperature": 11.0,
      "precipitation": 0.0,
      "wind_speed_10m": 8.0,
      "weather_code": 0,
      "source": "open-meteo",
      "created_at": "2026-05-29T15:05:00Z",
      "updated_at": "2026-05-29T15:05:00Z"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `readings` | array | List of reading objects (may be empty) |
| `readings[].id` | integer | Database primary key |
| `readings[].city` | string | City name |
| `readings[].recorded_at` | string (ISO 8601) | Observation time from Open-Meteo |
| `readings[].temperature_2m` | number | Air temperature (°C) |
| `readings[].apparent_temperature` | number | Feels-like temperature (°C) |
| `readings[].precipitation` | number | Precipitation (mm, preceding hour) |
| `readings[].wind_speed_10m` | number | Wind speed (km/h) |
| `readings[].weather_code` | integer | WMO weather code |
| `readings[].source` | string | Data source (e.g. `open-meteo`) |
| `readings[].created_at` | string (ISO 8601) | Row created in this system |
| `readings[].updated_at` | string (ISO 8601) | Row last updated |

**Examples**

```bash
# Latest readings (all cities), default limit 50
curl -s "http://localhost:8000/readings"

# Ottawa only, last 10 readings
curl -s "http://localhost:8000/readings?city=Ottawa&limit=10"
```

---

### GET /events

Returns notable weather events detected by the service, newest first. Each event includes what changed, where, when, and why it was flagged (`rule_triggered`).

**Query parameters**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `city` | No | — | Filter by city name (e.g. `Toronto`) |
| `limit` | No | `50` | Max rows to return (1–1000) |

**Response:** `200 OK`

```json
{
  "events": [
    {
      "id": 1,
      "event_type": "spike",
      "metric": "temperature_2m",
      "severity": 1,
      "city": "Ottawa",
      "latitude": null,
      "longitude": null,
      "rule_triggered": "Metric temperature_2m exceeded threshold of 5",
      "actual_value": 16.0,
      "expected_value": 10.0,
      "event_timestamp": "2026-05-29T15:00:00Z",
      "recorded_at": "2026-05-29T15:00:00Z",
      "created_at": "2026-05-29T15:05:00Z",
      "updated_at": "2026-05-29T15:05:00Z"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `events` | array | List of event objects (may be empty) |
| `events[].id` | integer | Database primary key |
| `events[].event_type` | string | e.g. `spike`, `drop`, `severe_weather` |
| `events[].metric` | string | Field that triggered the event |
| `events[].severity` | integer | Severity level (higher = more severe) |
| `events[].city` | string | City name |
| `events[].latitude` | number \| null | Optional latitude |
| `events[].longitude` | number \| null | Optional longitude |
| `events[].rule_triggered` | string | Human-readable reason the event fired |
| `events[].actual_value` | number | Observed value |
| `events[].expected_value` | number | Comparison value (previous reading or city average) |
| `events[].event_timestamp` | string (ISO 8601) | When the condition occurred |
| `events[].recorded_at` | string (ISO 8601) | When the reading was recorded |
| `events[].created_at` | string (ISO 8601) | Row created in this system |
| `events[].updated_at` | string (ISO 8601) | Row last updated |

**Examples**

```bash
# Latest events (all cities), default limit 50
curl -s "http://localhost:8000/events"

# Vancouver only, last 5 events
curl -s "http://localhost:8000/events?city=Vancouver&limit=5"
```

## Running Tests

This project runs tests using the PyTest framework, which provides an interface to automatically launch tests from python files with "_test_" in the name.

To run the tests with PyTest, simply enter the project directory through the terminal and type the following command:

```bash
pytest tests/ -v
```

If you wish to run a specific test, add the file name (listed in detail below) after 'tests/'.

The tests are located under the /tests directory of the repo, and they contain four test files:

- "database_test.py" contains functions that test the functionality of database queries, as well as Pydantic schema validation for response and object types used throughout the repo


- "endpoints_test.py" contains functions that test the functionality of all API endpoints and their query parameters, asserting that the JSON response is returned according to Pydantic model expectations


- "event_detection_test.py" contains functions that test the functionality of the event detection model described in the Event Detection Design section. These tests assert that the function catches weather events from readings that fall under the criteria listed, as well as rejecting edge cases


- "poll_test.py" contains functions that test the functionality of the poller program under src/services/poll.py, ensuring that if the API returns the same call twice, it is only stored in the database once

## Technology Choices

In the creation of this project, I made many meticulous decisions as to which technologies I would use to complete the task. I will list my reasoning for choosing each one below.

### Fast API as the Python API Framework:
- I chose FastAPI as the primary API framework for it's unmatched speed when it comes to async support. It is lightning fast when it comes to parsing and sending back data while not blocking other incoming requests.
- Additionally, FastAPI has built in Pydantic model validation and documentation with Swagger UI, which makes input checks very easy as well as providing a practical interface for testing API endpoints
- For a lightweight project such as this with simple database querying and polling, a lightweight framework like FastAPI made the most sense



## Event Detection Design

## Cursor Setup

### Rules

### Agents

### Skills
