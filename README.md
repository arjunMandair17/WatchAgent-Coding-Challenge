# Nokia Weather API

Tracks weather for Ottawa, Toronto, and Vancouver; detects significant events; exposes a REST API.

## Quick start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose).

```bash
git clone <your-repo>
cd Nokia-WeatherAPI
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

The `api` container runs Alembic migrations on startup, then serves the app and background pollers.

Stop with `Ctrl+C`, or run `docker compose down` in another terminal.

## Local development (optional)

Run Postgres only in Docker, API on the host:

```bash
docker compose up -d postgres
cp .env.example .env
# Edit .env: set DATABASE_URL host to localhost instead of postgres
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```bash
docker compose up -d postgres
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
pytest tests/ -v
```

For tests against Docker Postgres, use `localhost` in `DATABASE_URL` (port `5432` is published).
