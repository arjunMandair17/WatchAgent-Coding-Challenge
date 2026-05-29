from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..db.models import SignificantEvent, WeatherReading

THRESHOLDS = {
    "temperature_2m": 5,
    "apparent_temperature": 5,
    "precipitation": 2.0,
    "wind_speed_10m": 15.0,
}

# WMO codes (Open-Meteo) considered severe enough to alert on entry, not mere cloud-cover shifts.
SERIOUS_WEATHER_CODES = frozenset({
    65,  # Rain: heavy intensity
    67,  # Freezing rain: heavy intensity
    75,  # Snow fall: heavy intensity
    82,  # Rain showers: violent
    86,  # Snow showers: heavy
    95,  # Thunderstorm: slight or moderate
    96,  # Thunderstorm with slight hail
    99,  # Thunderstorm with heavy hail
})

WEATHER_CODE_LABELS = {
    65: "heavy rain",
    67: "heavy freezing rain",
    75: "heavy snowfall",
    82: "violent rain showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}

def detect_significant_events(
    weather_reading: WeatherReading, db: Session
) -> Optional[SignificantEvent]:
    """Detect significant events in the weather reading."""

    last_reading = (
        db.query(WeatherReading)
        .filter(
            WeatherReading.city == weather_reading.city,
            WeatherReading.recorded_at < weather_reading.recorded_at,
        )
        .order_by(WeatherReading.recorded_at.desc())
        .first()
    )

    if last_reading is not None:
        current_code = weather_reading.weather_code
        previous_code = last_reading.weather_code
        if (
            current_code in SERIOUS_WEATHER_CODES
            and current_code != previous_code
        ):
            label = WEATHER_CODE_LABELS.get(current_code, f"code {current_code}")
            previous_label = WEATHER_CODE_LABELS.get(previous_code, f"code {previous_code}")
            severity = 3 if current_code in {96, 99} else 2
            return SignificantEvent(
                event_type="severe_weather",
                metric="weather_code",
                severity=severity,
                city=weather_reading.city,
                latitude=None,
                longitude=None,
                rule_triggered=(
                    f"Severe condition entered: {label} (WMO {current_code}), "
                    f"was {previous_label} (WMO {previous_code})"
                ),
                actual_value=float(current_code),
                expected_value=float(previous_code),
                event_timestamp=weather_reading.recorded_at,
                recorded_at=weather_reading.recorded_at,
            )

    previous_12_hours = (
        db.query(WeatherReading)
        .filter(
            WeatherReading.city == weather_reading.city,
            WeatherReading.recorded_at > weather_reading.recorded_at - timedelta(hours=12),
            WeatherReading.recorded_at < weather_reading.recorded_at,
        )
        .all()
    )
    city_average = {metric: 0.0 for metric in THRESHOLDS.keys()}
    if len(previous_12_hours) < 3:
        return None
    for reading in previous_12_hours:
        for metric in THRESHOLDS.keys():
            city_average[metric] += getattr(reading, metric)
    for metric in THRESHOLDS.keys():
        city_average[metric] /= len(previous_12_hours)

    # check against last reading
    if last_reading is not None:
        for metric in THRESHOLDS.keys():
            delta = getattr(weather_reading, metric) - getattr(last_reading, metric)
            if delta >= THRESHOLDS[metric]:
                return SignificantEvent(
                    event_type="spike",
                    metric=metric,
                    severity=1,
                    city=weather_reading.city,
                    latitude=None,
                    longitude=None,
                    rule_triggered=f"Metric {metric} exceeded threshold of {THRESHOLDS[metric]}",
                    actual_value=getattr(weather_reading, metric),
                    expected_value=getattr(last_reading, metric),
                    event_timestamp=weather_reading.recorded_at,
                    recorded_at=weather_reading.recorded_at,
                )
            elif delta <= -THRESHOLDS[metric]:
                return SignificantEvent(
                    event_type="drop",
                    metric=metric,
                    severity=1,
                    city=weather_reading.city,
                    latitude=None,
                    longitude=None,
                    rule_triggered=f"Metric {metric} dropped below threshold of {THRESHOLDS[metric]}",
                    actual_value=getattr(weather_reading, metric),
                    expected_value=getattr(last_reading, metric),
                    event_timestamp=weather_reading.recorded_at,
                    recorded_at=weather_reading.recorded_at,
                )

    # check against city average
    for metric in city_average.keys():
        delta = getattr(weather_reading, metric) - city_average[metric]
        if delta >= THRESHOLDS[metric]:
            return SignificantEvent(
                event_type="spike",
                metric=metric,
                severity=1,
                city=weather_reading.city,
                latitude=None,
                longitude=None,
                rule_triggered=f"Metric {metric} exceeded city average of {city_average[metric]}",
                actual_value=getattr(weather_reading, metric),
                expected_value=city_average[metric],
                event_timestamp=weather_reading.recorded_at,
                recorded_at=weather_reading.recorded_at,
            )
        elif delta <= -THRESHOLDS[metric]:
            return SignificantEvent(
                event_type="drop",
                metric=metric,
                severity=1,
                city=weather_reading.city,
                latitude=None,
                longitude=None,
                rule_triggered=f"Metric {metric} dropped below city average of {city_average[metric]}",
                actual_value=getattr(weather_reading, metric),
                expected_value=city_average[metric],
                event_timestamp=weather_reading.recorded_at,
                recorded_at=weather_reading.recorded_at,
            )

    return None
