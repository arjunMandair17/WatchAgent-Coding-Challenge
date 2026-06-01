from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import delete

from src.db.models import SignificantEvent, WeatherReading
from src.db.session import SessionLocal, get_db
from src.main import app

TEST_SOURCE = "endpoint-test"
TEST_EVENT_RULE = "endpoint-test-rule"


def _reading(**kwargs) -> WeatherReading:
    """Build a WeatherReading with sensible defaults; override via kwargs."""

    defaults = {
        "city": "EndpointsDefault",
        "recorded_at": datetime.now(timezone.utc),
        "temperature_2m": 10.0,
        "apparent_temperature": 10.0,
        "precipitation": 0.0,
        "wind_speed_10m": 5.0,
        "weather_code": 0,
        "source": TEST_SOURCE,
    }
    defaults.update(kwargs)
    return WeatherReading(**defaults)


def _event(**kwargs) -> SignificantEvent:
    """Build a SignificantEvent with sensible defaults; override via kwargs."""

    now = datetime.now(timezone.utc)
    defaults = {
        "event_type": "spike",
        "metric": "temperature_2m",
        "severity": 1,
        "city": "EndpointsDefault",
        "latitude": 45.42,
        "longitude": -75.69,
        "rule_triggered": TEST_EVENT_RULE,
        "actual_value": 16.0,
        "expected_value": 10.0,
        "event_timestamp": now,
        "recorded_at": now,
    }
    defaults.update(kwargs)
    return SignificantEvent(**defaults)


@fixture
def db():
    """Yield a DB session; remove endpoint-test rows after each test."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.execute(delete(WeatherReading).where(WeatherReading.source == TEST_SOURCE))
        session.execute(
            delete(SignificantEvent).where(SignificantEvent.rule_triggered == TEST_EVENT_RULE)
        )
        session.commit()
        session.close()


@fixture
def client(db):
    """TestClient with get_db overridden and background pollers disabled."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    startup_handlers = list(app.router.on_startup)
    app.router.on_startup.clear()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.on_startup[:] = startup_handlers


def test_get_health(client, db):
    """Health counts increase after seeding readings and events."""

    before = client.get("/health").json()
    db.add(_reading())
    db.add(_event())
    db.commit()

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["readings_stored"] == before["readings_stored"] + 1
    assert body["events_stored"] == before["events_stored"] + 1


def test_get_readings(client, db):
    """Readings endpoint returns wrapped list for a seeded city."""

    city = "Ottawa"
    db.add(_reading(city=city, temperature_2m=12.5))
    db.commit()

    response = client.get("/readings", params={"city": city, "limit": 10})
    assert response.status_code == 200
    ours = [r for r in response.json()["readings"] if r["source"] == TEST_SOURCE]
    assert len(ours) == 1
    assert ours[0]["city"] == city
    assert ours[0]["temperature_2m"] == 12.5


def test_get_events(client, db):
    """Events endpoint returns wrapped list for seeded events."""

    city = "Toronto"
    db.add(_event(city=city, severity=2))
    db.commit()

    response = client.get("/events", params={"city": city, "limit": 10})
    assert response.status_code == 200
    ours = [
        e for e in response.json()["events"] if e["rule_triggered"] == TEST_EVENT_RULE
    ]
    assert len(ours) == 1
    assert ours[0]["city"] == city
    assert ours[0]["severity"] == 2


def test_get_events_with_city(client, db):
    """City filter returns only matching events."""

    db.add(_event(city="Ottawa"))
    db.add(_event(city="Vancouver"))
    db.commit()

    response = client.get("/events", params={"city": "Ottawa"})
    assert response.status_code == 200
    ours = [
        e for e in response.json()["events"] if e["rule_triggered"] == TEST_EVENT_RULE
    ]
    assert {e["city"] for e in ours} == {"Ottawa"}
    assert len(ours) == 1


def test_get_events_with_limit(client, db):
    """Limit caps how many events are returned for a single city."""

    city = "Vancouver"
    base = datetime.now(timezone.utc)
    for i in range(3):
        db.add(
            _event(
                city=city,
                recorded_at=base - timedelta(hours=i),
                event_timestamp=base - timedelta(hours=i),
            )
        )
    db.commit()

    response = client.get("/events", params={"city": city, "limit": 2})
    assert response.status_code == 200
    ours = [
        e for e in response.json()["events"] if e["rule_triggered"] == TEST_EVENT_RULE
    ]
    assert len(ours) == 2
    assert all(e["city"] == city for e in ours)


def test_get_readings_returns_multiple_rows(client, db):
    """Multiple readings for the same city are all returned."""

    city = "Toronto"
    ts = datetime.now(timezone.utc)
    db.add(_reading(city=city, recorded_at=ts - timedelta(hours=1)))
    db.add(_reading(city=city, recorded_at=ts))
    db.commit()

    response = client.get("/readings", params={"city": city})
    assert response.status_code == 200
    ours = [r for r in response.json()["readings"] if r["source"] == TEST_SOURCE]
    assert len(ours) == 2


def test_get_readings_rejects_unknown_city(client):
    """Invalid city query returns 400 with a clear error message."""

    response = client.get("/readings", params={"city": "Montreal"})
    assert response.status_code == 400
    assert "Montreal" in response.json()["detail"]


def test_get_events_rejects_unknown_city(client):
    """Invalid city query returns 400 with a clear error message."""

    response = client.get("/events", params={"city": "Montreal"})
    assert response.status_code == 400
    assert "Montreal" in response.json()["detail"]
