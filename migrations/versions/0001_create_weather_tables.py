"""Create weather readings and significant events tables.

Revision ID: 0001_create_weather_tables
Revises: 
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_create_weather_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weather_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_2m", sa.Float(), nullable=False),
        sa.Column("apparent_temperature", sa.Float(), nullable=False),
        sa.Column("precipitation", sa.Float(), nullable=False),
        sa.Column("wind_speed_10m", sa.Float(), nullable=False),
        sa.Column("weather_code", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("precipitation >= 0", name="ck_weather_readings_precipitation_gte_0"),
        sa.CheckConstraint("wind_speed_10m >= 0", name="ck_weather_readings_wind_speed_gte_0"),
        sa.CheckConstraint("weather_code >= 0", name="ck_weather_readings_weather_code_gte_0"),
    )
    op.create_index("ix_weather_readings_city", "weather_readings", ["city"], unique=False)
    op.create_index(
        "ix_weather_readings_city_recorded_at",
        "weather_readings",
        ["city", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_weather_readings_recorded_at",
        "weather_readings",
        ["recorded_at"],
        unique=False,
    )

    op.create_table(
        "significant_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("rule_triggered", sa.String(length=500), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=False),
        sa.Column("expected_value", sa.Float(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity >= 0", name="ck_significant_events_severity_gte_0"),
    )
    op.create_index("ix_significant_events_city", "significant_events", ["city"], unique=False)
    op.create_index(
        "ix_significant_events_city_event_timestamp",
        "significant_events",
        ["city", "event_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_significant_events_event_timestamp",
        "significant_events",
        ["event_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_significant_events_recorded_at",
        "significant_events",
        ["recorded_at"],
        unique=False,
    )

    op.create_table(
        "significant_event_readings",
        sa.Column(
            "significant_event_id",
            sa.Integer(),
            sa.ForeignKey("significant_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "weather_reading_id",
            sa.Integer(),
            sa.ForeignKey("weather_readings.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_significant_event_readings_event_id",
        "significant_event_readings",
        ["significant_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_significant_event_readings_weather_reading_id",
        "significant_event_readings",
        ["weather_reading_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_significant_event_readings_weather_reading_id", table_name="significant_event_readings")
    op.drop_index("ix_significant_event_readings_event_id", table_name="significant_event_readings")
    op.drop_table("significant_event_readings")

    op.drop_index("ix_significant_events_recorded_at", table_name="significant_events")
    op.drop_index("ix_significant_events_event_timestamp", table_name="significant_events")
    op.drop_index("ix_significant_events_city_event_timestamp", table_name="significant_events")
    op.drop_index("ix_significant_events_city", table_name="significant_events")
    op.drop_table("significant_events")

    op.drop_index("ix_weather_readings_recorded_at", table_name="weather_readings")
    op.drop_index("ix_weather_readings_city_recorded_at", table_name="weather_readings")
    op.drop_index("ix_weather_readings_city", table_name="weather_readings")
    op.drop_table("weather_readings")

