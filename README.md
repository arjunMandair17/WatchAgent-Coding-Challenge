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
┌──────────────┐    ┌─────────────────────────────────────────────┐
│   Client     │    │              api container                  |
│  (browser,   │    │  ┌─────────────────────────────────────────┐│
│   curl)      │    │  │  poll.py (×3 asyncio tasks)             ││
└──────┬───────┘    │  │  Ottawa · Toronto · Vancouver           ││
       │ HTTP       │  └───────────────┬─────────────────────────┘│
       │ :8000      │                  │ new timestamp only       │
       ▼            │                  ▼                          │
┌──────────────┐    │  ┌──────────────────────────┐               │
│  FastAPI     │◄───┤  │  event_detection.py      │               │
│  routes      │    │  │  (thresholds, 12h avg, │                 │ 
│  /health     │    │  │   severe WMO codes)      │               │
│  /readings   │    │  └───────────────┬──────────┘               │
│  /events     │    │                  │                          │
└──────┬───────┘    │                  ▼                          │
       │            │  ┌──────────────────────────┐               │
       │            │  │  db_storage.py           │               │
       │            │  │  SQLAlchemy ORM          │               │
       │            │  └───────────────┬──────────┘               │
       │            └──────────────────┼──────────────────────────┘
       │                                │ SQL (psycopg)
       │                                ▼
       │             ┌──────────────────────────────────────────────┐
       └────────────►│           postgres container                 │
                     │  weather_readings                            │
                     │  significant_events                          │
                     │  significant_event_readings (join)           │
                     │  volume: postgres_data (persists restarts)   │
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

### FastAPI as the Python API framework

- I chose FastAPI as the primary API framework for its async support. The three city pollers run as background tasks while the API still handles `/health`, `/readings`, and `/events` without blocking.
- FastAPI integrates with Pydantic for response models and generates interactive docs at `/docs`, which made it easy to verify the exact JSON contracts required by the challenge.
- For a project with simple querying, polling, and clear REST endpoints, a lightweight ASGI framework was a better fit than a heavier stack.

### PostgreSQL as the database

- PostgreSQL stores all raw readings and significant events in a durable, relational schema with foreign keys between events and readings.
- It supports the counts returned by `/health`, filtering by city and time, and persists data across container restarts via the `postgres_data` Docker volume (as required by the spec).
- I use SQLAlchemy 2 as the ORM and Alembic for migrations so schema changes are versioned and applied automatically when the API container starts.

### Pydantic for validation and API contracts

- Response shapes for `/health`, `/readings`, and `/events` are defined in `src/schemas.py`, matching the challenge’s required JSON structure and keeping extra fields out of responses.
- Ingest validation lives in `src/db/schemas.py` (e.g. rejecting future timestamps, negative precipitation, implausible temperatures) so bad data is caught before insert.
- `pydantic-settings` loads `DATABASE_URL` and `POSTGRES_*` from `.env`, which keeps credentials out of the repository while still giving Docker Compose a single configuration file to copy.

### Pytest for automated testing

- The spec requires unit tests for deduplication (mocked Open-Meteo), event detection logic, and API response shape. pytest is the standard choice for Python and runs all of those in `tests/`.
- `poll_test.py` mocks `requests.get` and proves duplicate timestamps only create one row; `event_detection_test.py` covers spikes, drops, city averages, and severe weather codes; `endpoints_test.py` checks the live HTTP layer with FastAPI’s `TestClient`.
- GitHub Actions runs `pytest tests/` on every push to `main` against a Postgres service container, so tests stay aligned with production behavior.

## Event Detection Design

The event detection model that I used for this project was meticulously designed with the aim of detecting strange spikes and dips in weather data across long and short periods of time. I tried to create a balance of detecting slight differences in weather data while filtering out general noise. I also wanted the detection algorithm to be specific to the city the readings were collected from, not based on global constants. This is understandable considering the differences between the cities (for example, it is MUCH colder in Ottawa in December than it is in Vancouver). This was accomplished by creating a system that tracks changes between the most recent readings initially, then as a fallback queries the database to track changes between the current reading and recent history.

The detection model has three main criteria that it uses to categorize an event:

### Weather Code Differences
- The function checks the weather code provided by OpenMeteo at the time of the reading, which dictates the basic weather conditions
- If the weather code conveys a strange weather reading it will flag an event with matching intensity, ignoring repeat events

### Differences in Weather Data From Last Reading
- The function computes the delta between the current and most previous weather reading for every stat
- It then compares this delta to a dictionary of thresholds which dictate a noticeable jump in a statistic between the two readings
- It can differentiate between a spike or drop in the statistic based on the sign of the delta

### Differences in Weather Data From City History
- Oftentimes a small rise or dip in a particular stat will not trigger an event even though it has been steadily changing over time
- To account for this, the function computes the average of each stat over the past 12 readings in the given city and gathers the delta between this average and the current reading
- This delta represents the change in the metric in the city over a larger period of time, which oftentimes reveals more about the current weather conditions than simply querying the most recent reading
- This delta is then compared to the same thresholds as before to test deviation

## Cursor Setup

This project uses Cursor rules, subagents, and a custom skill under `.cursor/` so AI-assisted work stays aligned with the architecture, API contracts, and take-home requirements.

### Rules

Rules apply automatically when matching files are edited (via `globs` in each `.mdc` file).

| Rule file | Applies to | Purpose |
|-----------|------------|---------|
| `python-fastapi.mdc` | `src/routes/**`, `main.py` | FastAPI conventions: async endpoints, `response_model`, Pydantic schemas in `src/schemas.py`, thin routes with logic in `src/services/`, env via `src/config.py`, and exact response shapes for `/health`, `/readings`, and `/events`. |
| `api-rest.mdc` | `src/routes/**` | REST naming (nouns, plurals, query params for filters), correct HTTP methods and status codes, stateless design, and no leaking of DB/ORM internals in responses. |
| `event-detection.mdc` | `src/services/poll.py`, `src/services/event_detection.py` | When and how to run detection (before persist, ≥3 prior readings, no duplicate timestamps), rule priority (severe WMO codes → step change vs previous → deviation vs 12h baseline), thresholds, severity, required event fields, and `rule_triggered` text format. Poll failures must log city + HTTP status. |
| `tests.mdc` | `tests/**` | pytest + `TestClient`, isolated test DB, descriptive test names and docstrings, realistic fixtures, and assertions on shape/status/data—not “did not crash.” |

### Agents

Subagents are defined in `.cursor/agents/` with scoped responsibilities so changes stay in the right layer.

| Agent | Role |
|-------|------|
| **API Developer** (`api-developer.md`) | Builds and maintains FastAPI routes: REST conventions, Pydantic request/response models, `HTTPException`, `APIRouter`, async handlers, and service-layer calls (`readings.py`, `events.py`). Does not own schema design or event-detection logic. Points to the data-analysis script for ad-hoc DB inspection outside the API. |
| **Test Specialist** (`test-specialist.md`) | Owns pytest coverage for API, database, validation, and integration flows. Extends existing tests under `tests/` rather than replacing them; uses `TestClient` and fixtures, not live servers. Uses the data-analysis script only for exploratory checks, not as a substitute for unit tests. |
| **Database Designer** (`db-designer.md`) | Owns `weather_readings` and `significant_events` schema, SQLAlchemy models, Alembic migrations, indexes on `city`/`timestamp`, FK integrity, and Postgres-only config via `DATABASE_URL`. Does not write routes or detection rules. |

### Skills

| Skill | Location | Purpose |
|-------|----------|---------|
| **data-analysis** | `.cursor/skills/data-analysis/` | CLI over the **local PostgreSQL** database (same `DATABASE_URL` / `POSTGRES_*` as the app). Does not call Open-Meteo. |

Run from the repository root with Postgres up and migrations applied:

```bash
python .cursor/skills/data-analysis/analyze.py summary
python .cursor/skills/data-analysis/analyze.py city-stats --hours 24
python .cursor/skills/data-analysis/analyze.py city-stats --city Ottawa --hours 12
python .cursor/skills/data-analysis/analyze.py events --city Toronto --hours 48 --limit 10
python .cursor/skills/data-analysis/analyze.py compare --hours 24
python .cursor/skills/data-analysis/analyze.py ask "How many readings are stored per city?"
```

Commands print **JSON** to stdout: row counts, per-city averages over a window, recent events (including `rule_triggered`), cross-city comparison, and keyword-routed `ask` queries. See `.cursor/skills/data-analysis/SKILL.md` for full usage.
