# Nokia Weather API

Tracks weather for Ottawa, Toronto, and Vancouver; detects significant events; exposes a REST API.

## Running the stack (Docker)

Requires [Docker](https://docs.docker.com/get-docker/) and Git.

```bash
git clone <your-repo>
cd Nokia-WeatherAPI
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

On startup, the `api` container runs Alembic migrations, starts the HTTP server, and runs background pollers for Ottawa, Toronto, and Vancouver.

**Database persistence:** data is stored in the `postgres_data` Docker volume and survives `docker compose stop` / `docker compose up`. Use `docker compose down -v` only if you want to wipe the database.

If you see `role "weather_app" does not exist`, the volume was created with older settings. Reset it:

```bash
docker compose down -v
cp .env.example .env
docker compose up --build
```

**Environment variables:** all required variables are documented in `.env.example`. Copy that file to `.env` (gitignored). No credentials are committed to this repository; the default Compose file uses trust authentication for local development only.

Windows (CMD): `copy .env.example .env` instead of `cp`.

## Local development (optional)

Postgres in Docker, API on the host:

```bash
docker compose up -d postgres
cp .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```bash
docker compose up -d postgres
cp .env.example .env
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
pytest tests/ -v
```
