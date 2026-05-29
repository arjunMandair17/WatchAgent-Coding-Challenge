from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from pytest import fixture
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.db.models import SignificantEvent, SignificantEventReading, WeatherReading
from src.db.schemas import SignificantEventCreate, WeatherReadingCreate
from src.db.session import SessionLocal

TEST_SOURCE = "db-test"
TEST_EVENT_RULE = "db-test-rule"


def _reading(**kwargs) -> WeatherReading:
    """Build a WeatherReading with sensible defaults; override via kwargs."""

    defaults = {
        "city": "DbTestDefault",
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
        "city": "DbTestDefault",
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
    """Yield a DB session; remove db-test rows after each test."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.execute(
            delete(SignificantEvent).where(SignificantEvent.rule_triggered == TEST_EVENT_RULE)
        )
        session.execute(delete(WeatherReading).where(WeatherReading.source == TEST_SOURCE))
        session.commit()
        session.close()


def _link_event_to_reading(db, event: SignificantEvent, reading: WeatherReading) -> None:
    """Persist reading and event and associate them via the join table."""

    db.add(reading)
    db.flush()
    event.weather_readings.append(reading)
    db.add(event)
    db.commit()


def test_persistence_survives_new_session(db):
    """Committed reading and event are visible from a fresh database session."""

    city = "DbTestPersistence"
    reading = _reading(city=city, temperature_2m=14.2)
    event = _event(city=city, severity=2, actual_value=18.0)
    db.add(reading)
    db.add(event)
    db.commit()
    reading_id = reading.id
    event_id = event.id

    other = SessionLocal()
    try:
        stored_reading = other.get(WeatherReading, reading_id)
        stored_event = other.get(SignificantEvent, event_id)
        assert stored_reading is not None
        assert stored_reading.city == city
        assert stored_reading.temperature_2m == 14.2
        assert stored_reading.source == TEST_SOURCE
        assert stored_event is not None
        assert stored_event.city == city
        assert stored_event.severity == 2
        assert stored_event.rule_triggered == TEST_EVENT_RULE
    finally:
        other.close()


def test_timestamps_auto_populated_on_insert(db):
    """created_at and updated_at are set automatically when a row is inserted."""

    before = datetime.now(timezone.utc)
    reading = _reading(city="DbTestTimestamps")
    db.add(reading)
    db.commit()
    after = datetime.now(timezone.utc)

    assert reading.created_at is not None
    assert reading.updated_at is not None
    assert reading.created_at.tzinfo is not None
    assert reading.updated_at.tzinfo is not None
    assert before <= reading.created_at <= after
    assert before <= reading.updated_at <= after


def test_join_table_links_event_to_reading(db):
    """Associating an event with a reading creates a significant_event_readings row."""

    reading = _reading(city="DbTestJoin")
    event = _event(city="DbTestJoin")
    _link_event_to_reading(db, event, reading)

    link = db.execute(
        select(SignificantEventReading).where(
            SignificantEventReading.significant_event_id == event.id,
            SignificantEventReading.weather_reading_id == reading.id,
        )
    ).scalar_one_or_none()
    assert link is not None

    db.refresh(event)
    assert len(event.weather_readings) == 1
    assert event.weather_readings[0].id == reading.id


def test_fk_restrict_blocks_deleting_linked_reading(db):
    """A weather reading referenced by the join table cannot be deleted."""

    reading = _reading(city="DbTestRestrict")
    event = _event(city="DbTestRestrict")
    _link_event_to_reading(db, event, reading)

    with pytest.raises(IntegrityError):
        db.delete(reading)
        db.commit()
    db.rollback()


def test_cascade_deleting_event_removes_join_rows(db):
    """Deleting a significant event cascades to its join-table rows."""

    reading = _reading(city="DbTestCascade")
    event = _event(city="DbTestCascade")
    _link_event_to_reading(db, event, reading)
    event_id = event.id
    reading_id = reading.id

    db.delete(event)
    db.commit()

    link = db.execute(
        select(SignificantEventReading).where(
            SignificantEventReading.significant_event_id == event_id
        )
    ).scalar_one_or_none()
    assert link is None
    assert db.get(WeatherReading, reading_id) is not None


@pytest.mark.parametrize(
    "factory_kwargs",
    [
        {"precipitation": -0.1},
        {"wind_speed_10m": -1.0},
    ],
)
def test_check_constraints_reject_negative_reading_metrics(db, factory_kwargs):
    """Database CHECK constraints reject negative precipitation and wind speed."""

    reading = _reading(city="DbTestCheckReading", **factory_kwargs)
    db.add(reading)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_check_constraint_rejects_negative_severity(db):
    """Database CHECK constraint rejects negative event severity."""

    event = _event(city="DbTestCheckSeverity", severity=-1)
    db.add(event)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_weather_reading_create_rejects_future_recorded_at():
    """Pydantic rejects weather readings with a future recorded_at."""

    future = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValidationError):
        WeatherReadingCreate(
            city="Ottawa",
            recorded_at=future,
            temperature_2m=10.0,
            apparent_temperature=10.0,
            precipitation=0.0,
            wind_speed_10m=5.0,
            weather_code=0,
            source="validation-test",
        )


def test_weather_reading_create_rejects_negative_precipitation():
    """Pydantic rejects negative precipitation before database insert."""

    with pytest.raises(ValidationError):
        WeatherReadingCreate(
            city="Ottawa",
            recorded_at=datetime.now(timezone.utc),
            temperature_2m=10.0,
            apparent_temperature=10.0,
            precipitation=-1.0,
            wind_speed_10m=5.0,
            weather_code=0,
            source="validation-test",
        )


def test_weather_reading_create_rejects_extreme_temperature():
    """Pydantic rejects temperatures outside plausible bounds."""

    with pytest.raises(ValidationError):
        WeatherReadingCreate(
            city="Ottawa",
            recorded_at=datetime.now(timezone.utc),
            temperature_2m=200.0,
            apparent_temperature=10.0,
            precipitation=0.0,
            wind_speed_10m=5.0,
            weather_code=0,
            source="validation-test",
        )


def test_significant_event_create_rejects_empty_city():
    """Pydantic rejects significant events with an empty city name."""

    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        SignificantEventCreate(
            event_type="spike",
            metric="temperature_2m",
            severity=1,
            city="",
            rule_triggered="validation-test",
            actual_value=16.0,
            expected_value=10.0,
            event_timestamp=now,
            recorded_at=now,
        )


def test_significant_event_create_rejects_naive_datetime():
    """Pydantic rejects significant events with timezone-naive timestamps."""

    naive = datetime.now()
    with pytest.raises(ValidationError):
        SignificantEventCreate(
            event_type="spike",
            metric="temperature_2m",
            severity=1,
            city="Ottawa",
            rule_triggered="validation-test",
            actual_value=16.0,
            expected_value=10.0,
            event_timestamp=naive,
            recorded_at=naive,
        )


def test_not_null_rejects_incomplete_weather_reading(db):
    """ORM insert without required city is rejected at flush/commit."""

    reading = _reading()
    reading.city = None
    db.add(reading)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
