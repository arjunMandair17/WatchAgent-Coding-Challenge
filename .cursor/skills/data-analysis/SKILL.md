---
name: data-analysis
description: Query and analyze stored weather readings and significant events in PostgreSQL. Use when the user asks about trends, counts, per-city comparisons, time windows, or validation of stored data.
---

# Data Analysis

Run the analysis script from the **repository root** with `.env` configured and Postgres running (e.g. `docker compose up`).

## Commands

```bash
python .cursor/skills/data-analysis/analyze.py summary
python .cursor/skills/data-analysis/analyze.py city-stats --hours 24
python .cursor/skills/data-analysis/analyze.py city-stats --city Ottawa --hours 12
python .cursor/skills/data-analysis/analyze.py events --city Toronto --hours 48 --limit 10
python .cursor/skills/data-analysis/analyze.py compare --hours 24
python .cursor/skills/data-analysis/analyze.py ask "How many readings are stored per city?"
python .cursor/skills/data-analysis/analyze.py ask "Compare average temperature across cities"
```

All commands print **JSON** to stdout.

## When to use

- Counts of readings or events (overall or per city)
- Averages over a time window (temperature, precipitation, wind)
- Recent significant events and their `rule_triggered` text
- Cross-city comparison for a period
- Ad-hoc questions (use `ask`; routes by keywords)

## Requirements

- `DATABASE_URL` or `POSTGRES_*` in `.env` (same as the main app)
- Database migrated (`alembic upgrade head`) and populated by the poller

## Do not

- Call the live Open-Meteo API from this skill — it only reads the local database
- Hardcode credentials; use environment variables via `src.config`
