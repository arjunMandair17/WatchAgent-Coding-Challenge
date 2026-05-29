from datetime import datetime, timedelta, timezone

from pytest import fixture

from src.db.models import WeatherReading
from src.db.session import SessionLocal
from src.services.event_detection import detect_significant_events

CITY = "Ottawa"


def _reading(**kwargs) -> WeatherReading:
    """Build a WeatherReading with sensible defaults; override via kwargs."""
    defaults = {
        "city": CITY,
        "recorded_at": datetime.now(timezone.utc),
        "temperature_2m": 10.0,
        "apparent_temperature": 10.0,
        "precipitation": 0.0,
        "wind_speed_10m": 5.0,
        "weather_code": 0,
        "source": "test",
    }
    defaults.update(kwargs)
    return WeatherReading(**defaults)


def _seed_history(db, base_time: datetime, count: int, **metric_kwargs) -> None:
    """Add `count` readings one hour apart, ending one hour before base_time."""
    for i in range(count):
        t = base_time - timedelta(hours=count - i)
        db.add(_reading(recorded_at=t, **metric_kwargs))


def _seed_city_average_history(
    db,
    base_time: datetime,
    metric: str,
    stable_value: float,
    last_value: float,
    stable_count: int = 12,
) -> None:
    """Seed stable_count-1 readings at stable_value plus one near-threshold last reading."""
    # Timestamps must be strictly after (base - 12h) to fall in the 12h window.
    for i in range(stable_count - 1):
        t = base_time - timedelta(hours=stable_count - 1 - i)
        db.add(_reading(recorded_at=t, **{metric: stable_value}))
    db.add(
        _reading(
            recorded_at=base_time - timedelta(minutes=30),
            **{metric: last_value},
        )
    )


@fixture
def db():
    """Yield a DB session and roll back after each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_too_few_readings(db):
    """Fewer than three readings in the prior 12h window yields no event."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 2, temperature_2m=10.0)
    abnormal = _reading(recorded_at=base, temperature_2m=20.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is None


def test_weather_code_change(db):
    """Entering a new severe WMO code from another severe code triggers severe_weather."""
    base = datetime.now(timezone.utc)
    db.add(_reading(recorded_at=base - timedelta(hours=1), weather_code=67))
    current = _reading(recorded_at=base, weather_code=65)
    db.add(current)
    db.flush()
    event = detect_significant_events(current, db)
    assert event is not None
    assert event.event_type == "severe_weather"
    assert event.metric == "weather_code"
    assert event.severity == 2
    assert event.city == CITY
    assert event.rule_triggered == (
        "Severe condition entered: heavy rain (WMO 65), was heavy freezing rain (WMO 67)"
    )
    assert event.actual_value == 65
    assert event.expected_value == 67


def test_temperature_spike(db):
    """Temperature step up vs last reading exceeds the 5-degree threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, temperature_2m=10.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), temperature_2m=10.0))
    abnormal = _reading(recorded_at=base, temperature_2m=16.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "temperature_2m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric temperature_2m exceeded threshold of 5"
    assert event.actual_value == 16.0
    assert event.expected_value == 10.0


def test_temperature_drop(db):
    """Temperature step down vs last reading exceeds the 5-degree threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, temperature_2m=16.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), temperature_2m=16.0))
    abnormal = _reading(recorded_at=base, temperature_2m=10.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "temperature_2m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric temperature_2m dropped below threshold of 5"
    assert event.actual_value == 10.0
    assert event.expected_value == 16.0


def test_precipitation_spike(db):
    """Precipitation step up vs last reading exceeds the 2.0 threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, precipitation=10.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), precipitation=10.0))
    abnormal = _reading(recorded_at=base, precipitation=14.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "precipitation"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric precipitation exceeded threshold of 2.0"
    assert event.actual_value == 14.0
    assert event.expected_value == 10.0


def test_precipitation_drop(db):
    """Precipitation step down vs last reading exceeds the 2.0 threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, precipitation=14.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), precipitation=14.0))
    abnormal = _reading(recorded_at=base, precipitation=10.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "precipitation"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric precipitation dropped below threshold of 2.0"
    assert event.actual_value == 10.0
    assert event.expected_value == 14.0


def test_wind_speed_spike(db):
    """Wind speed step up vs last reading exceeds the 15.0 threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, wind_speed_10m=10.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), wind_speed_10m=10.0))
    abnormal = _reading(recorded_at=base, wind_speed_10m=30.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "wind_speed_10m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric wind_speed_10m exceeded threshold of 15.0"
    assert event.actual_value == 30.0
    assert event.expected_value == 10.0


def test_wind_speed_drop(db):
    """Wind speed step down vs last reading exceeds the 15.0 threshold."""
    base = datetime.now(timezone.utc)
    _seed_history(db, base, 4, wind_speed_10m=30.0)
    db.add(_reading(recorded_at=base - timedelta(minutes=30), wind_speed_10m=30.0))
    abnormal = _reading(recorded_at=base, wind_speed_10m=10.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "wind_speed_10m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == "Metric wind_speed_10m dropped below threshold of 15.0"
    assert event.actual_value == 10.0
    assert event.expected_value == 30.0


def test_temperature_spike_vs_city_average(db):
    """Temperature spike vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "temperature_2m", 10.0, 12.0)
    abnormal = _reading(recorded_at=base, temperature_2m=16.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "temperature_2m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric temperature_2m exceeded city average of {event.expected_value}"
    )
    assert event.actual_value == 16.0
    assert event.expected_value == (11 * 10.0 + 12.0) / 12


def test_temperature_drop_vs_city_average(db):
    """Temperature drop vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "temperature_2m", 10.0, 8.0)
    abnormal = _reading(recorded_at=base, temperature_2m=4.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "temperature_2m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric temperature_2m dropped below city average of {event.expected_value}"
    )
    assert event.actual_value == 4.0
    assert event.expected_value == (11 * 10.0 + 8.0) / 12


def test_precipitation_spike_vs_city_average(db):
    """Precipitation spike vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "precipitation", 10.0, 12.5)
    abnormal = _reading(recorded_at=base, precipitation=14.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "precipitation"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric precipitation exceeded city average of {event.expected_value}"
    )
    assert event.actual_value == 14.0
    assert event.expected_value == (11 * 10.0 + 12.5) / 12


def test_precipitation_drop_vs_city_average(db):
    """Precipitation drop vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "precipitation", 14.0, 11.0)
    abnormal = _reading(recorded_at=base, precipitation=10.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "precipitation"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric precipitation dropped below city average of {event.expected_value}"
    )
    assert event.actual_value == 10.0
    assert event.expected_value == (11 * 14.0 + 11.0) / 12


def test_wind_speed_spike_vs_city_average(db):
    """Wind speed spike vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "wind_speed_10m", 10.0, 20.0)
    abnormal = _reading(recorded_at=base, wind_speed_10m=30.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "spike"
    assert event.metric == "wind_speed_10m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric wind_speed_10m exceeded city average of {event.expected_value}"
    )
    assert event.actual_value == 30.0
    assert event.expected_value == (11 * 10.0 + 20.0) / 12


def test_wind_speed_drop_vs_city_average(db):
    """Wind speed drop vs 12h city average when last reading is within threshold."""
    base = datetime.now(timezone.utc)
    _seed_city_average_history(db, base, "wind_speed_10m", 30.0, 22.0)
    abnormal = _reading(recorded_at=base, wind_speed_10m=10.0)
    db.flush()
    event = detect_significant_events(abnormal, db)
    assert event is not None
    assert event.event_type == "drop"
    assert event.metric == "wind_speed_10m"
    assert event.severity == 1
    assert event.city == CITY
    assert event.rule_triggered == (
        f"Metric wind_speed_10m dropped below city average of {event.expected_value}"
    )
    assert event.actual_value == 10.0
    assert event.expected_value == (11 * 30.0 + 22.0) / 12
