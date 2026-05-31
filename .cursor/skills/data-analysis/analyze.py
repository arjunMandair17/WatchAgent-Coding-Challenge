#!/usr/bin/env python3
"""Query stored weather readings and events; return structured analysis as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

# Allow imports from project root when run as a script.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import settings  # noqa: E402
from src.db.models import SignificantEvent, WeatherReading  # noqa: E402
from src.db.session import SessionLocal  # noqa: E402

CITIES = ("Ottawa", "Toronto", "Vancouver")


def _session():
    """Open a database session using project settings."""

    return SessionLocal()


def summary() -> dict:
    """Return row counts for readings and events overall and per city."""

    db = _session()
    try:
        readings_total = db.scalar(select(func.count()).select_from(WeatherReading)) or 0
        events_total = db.scalar(select(func.count()).select_from(SignificantEvent)) or 0
        per_city = {}
        for city in CITIES:
            per_city[city] = {
                "readings": db.scalar(
                    select(func.count())
                    .select_from(WeatherReading)
                    .where(WeatherReading.city == city)
                )
                or 0,
                "events": db.scalar(
                    select(func.count())
                    .select_from(SignificantEvent)
                    .where(SignificantEvent.city == city)
                )
                or 0,
            }
        return {
            "readings_total": readings_total,
            "events_total": events_total,
            "per_city": per_city,
        }
    finally:
        db.close()


def city_stats(city: str | None, hours: int) -> dict:
    """Return average metrics for readings in a time window."""

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    db = _session()
    try:
        stmt = (
            select(
                WeatherReading.city,
                func.count(WeatherReading.id),
                func.avg(WeatherReading.temperature_2m),
                func.avg(WeatherReading.precipitation),
                func.avg(WeatherReading.wind_speed_10m),
            )
            .where(WeatherReading.recorded_at >= since)
            .group_by(WeatherReading.city)
        )
        if city:
            stmt = stmt.where(WeatherReading.city == city)
        rows = db.execute(stmt).all()
        return {
            "window_hours": hours,
            "since_utc": since.isoformat(),
            "cities": [
                {
                    "city": row.city,
                    "reading_count": row[1],
                    "avg_temperature_2m": round(float(row[2]), 2) if row[2] is not None else None,
                    "avg_precipitation": round(float(row[3]), 2) if row[3] is not None else None,
                    "avg_wind_speed_10m": round(float(row[4]), 2) if row[4] is not None else None,
                }
                for row in rows
            ],
        }
    finally:
        db.close()


def events_summary(city: str | None, hours: int, limit: int) -> dict:
    """Return recent significant events, optionally filtered by city."""

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    db = _session()
    try:
        stmt = (
            select(SignificantEvent)
            .where(SignificantEvent.event_timestamp >= since)
            .order_by(SignificantEvent.event_timestamp.desc())
            .limit(limit)
        )
        if city:
            stmt = stmt.where(SignificantEvent.city == city)
        events = db.scalars(stmt).all()
        return {
            "window_hours": hours,
            "since_utc": since.isoformat(),
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "city": e.city,
                    "event_type": e.event_type,
                    "metric": e.metric,
                    "severity": e.severity,
                    "rule_triggered": e.rule_triggered,
                    "actual_value": e.actual_value,
                    "expected_value": e.expected_value,
                    "event_timestamp": e.event_timestamp.isoformat(),
                }
                for e in events
            ],
        }
    finally:
        db.close()


def compare_cities(hours: int) -> dict:
    """Compare average temperature and event counts across cities."""

    stats = city_stats(city=None, hours=hours)
    db = _session()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        event_counts = {}
        for city in CITIES:
            event_counts[city] = (
                db.scalar(
                    select(func.count())
                    .select_from(SignificantEvent)
                    .where(
                        SignificantEvent.city == city,
                        SignificantEvent.event_timestamp >= since,
                    )
                )
                or 0
            )
    finally:
        db.close()
    return {
        "window_hours": hours,
        "reading_averages": stats["cities"],
        "event_counts": event_counts,
    }


def answer_question(question: str, hours: int = 24) -> dict:
    """Route a natural-language question to the best built-in analysis."""

    q = question.lower()
    if any(word in q for word in ("how many", "count", "total", "summary")):
        return {"question": question, "analysis": "summary", "result": summary()}
    if "event" in q:
        city = next((c for c in CITIES if c.lower() in q), None)
        return {
            "question": question,
            "analysis": "events_summary",
            "result": events_summary(city=city, hours=hours, limit=20),
        }
    if any(word in q for word in ("compare", "comparison", "versus", " vs ")):
        return {
            "question": question,
            "analysis": "compare_cities",
            "result": compare_cities(hours=hours),
        }
    if any(word in q for word in ("average", "avg", "temperature", "wind", "precip")):
        city = next((c for c in CITIES if c.lower() in q), None)
        return {
            "question": question,
            "analysis": "city_stats",
            "result": city_stats(city=city, hours=hours),
        }
    return {
        "question": question,
        "analysis": "summary",
        "note": "No specific keyword matched; returning dataset summary.",
        "result": summary(),
        "available_commands": ["summary", "city-stats", "events", "compare", "ask"],
    }


def main() -> int:
    """Parse CLI arguments and print JSON results."""

    parser = argparse.ArgumentParser(
        description="Analyze stored weather readings and significant events."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Counts of readings and events per city")

    p_stats = sub.add_parser("city-stats", help="Average metrics over a time window")
    p_stats.add_argument("--city", choices=CITIES)
    p_stats.add_argument("--hours", type=int, default=24)

    p_events = sub.add_parser("events", help="Recent significant events")
    p_events.add_argument("--city", choices=CITIES)
    p_events.add_argument("--hours", type=int, default=48)
    p_events.add_argument("--limit", type=int, default=20)

    p_compare = sub.add_parser("compare", help="Per-city averages and event counts")
    p_compare.add_argument("--hours", type=int, default=24)

    p_ask = sub.add_parser("ask", help="Answer a question using keyword routing")
    p_ask.add_argument("question")
    p_ask.add_argument("--hours", type=int, default=24)

    args = parser.parse_args()

    if args.command == "summary":
        payload = summary()
    elif args.command == "city-stats":
        payload = city_stats(city=args.city, hours=args.hours)
    elif args.command == "events":
        payload = events_summary(city=args.city, hours=args.hours, limit=args.limit)
    elif args.command == "compare":
        payload = compare_cities(hours=args.hours)
    else:
        payload = answer_question(args.question, hours=args.hours)

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
