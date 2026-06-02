# AGENTS.md

## Project Overview

This project is a reusable synthetic web analytics pipeline.

It generates realistic dummy website analytics time series data, stores it in Railway Postgres, and transforms it with dbt into analytics-ready reporting models.

The project is designed to be open-source and reusable. Other users should be able to clone the repo, edit a YAML config file, and generate their own synthetic analytics dataset.

This is version 1.

## Main Goal

Build a configurable analytics engineering demo project that includes:

- Synthetic daily website traffic generation
- Configurable YAML-based business assumptions
- Randomness and seasonality
- Railway Postgres as the database
- Railway native Cron Job support
- dbt transformations
- Data quality tests
- Clear documentation

The first generated table should be:

```text
raw.daily_traffic
```

The first dbt models should include:

```text
staging.stg_daily_traffic
marts.mart_traffic_daily
marts.mart_traffic_summary
```

## Tech Stack

Use:

- Python
- uv for dependency and environment management
- Postgres
- Railway Postgres
- Railway native Cron Job
- dbt Core
- dbt Postgres adapter
- YAML configuration

Use these Python packages unless there is a strong reason not to:

- pydantic
- pydantic-settings
- pyyaml
- faker
- numpy
- pandas
- psycopg[binary]
- python-dotenv
- dbt-core
- dbt-postgres
- pytest

Do not use:

- pip
- requirements.txt
- Poetry
- LangChain
- LangGraph
- vector databases
- web scraping
- traffic bots
- browser automation
- fake visits to real websites

This project should generate synthetic analytics records in a database. It must not generate traffic against real websites.

## Dependency Management

Use uv.

Use:

- pyproject.toml
- uv.lock
- uv sync
- uv run

Do not create requirements.txt unless explicitly requested later.

Development commands should use uv:

```bash
uv sync
uv run pytest
uv run python -m synthetic_analytics.cli --help
uv run dbt build --project-dir dbt_analytics
```

## Project Structure

Use this structure:

```text
synthetic-web-analytics-pipeline/
  synthetic_analytics/
    __init__.py
    cli.py
    config.py
    database.py
    generator/
      __init__.py
      daily_traffic.py
      time_series.py
    sql/
      create_raw_daily_traffic.sql
  config/
    project.yml
  dbt_analytics/
    dbt_project.yml
    profiles.yml.example
    models/
      staging/
        stg_daily_traffic.sql
        schema.yml
      marts/
        mart_traffic_daily.sql
        mart_traffic_summary.sql
        schema.yml
  tests/
    test_config.py
    test_daily_traffic_generator.py
  .env.example
  .gitignore
  README.md
  railway.json
  pyproject.toml
  AGENTS.md
```

## Configuration

The main user-editable config file should be:

```text
config/project.yml
```

The YAML config should control:

- project name
- timezone
- start date
- random seed
- base daily sessions
- randomness/noise
- growth trend
- weekly seasonality
- monthly seasonality
- special events
- brands
- countries
- devices
- traffic channels
- metric rules

The config should support realistic time series behavior.

Do not make the data purely random.

Generate metrics using layered multipliers:

```text
base volume
× brand multiplier
× country multiplier
× channel multiplier
× device multiplier
× weekday seasonality
× monthly seasonality
× growth trend
× random noise
× optional event multiplier
= final sessions
```

## Example YAML Requirements

Create a default `config/project.yml` with realistic values.

It should include at least:

- 3 brands
- 5 countries
- 3 devices
- 5 traffic channels
- weekly seasonality
- monthly seasonality
- at least 2 special events
- randomness settings
- trend settings
- metric rules

Example brands can be fictional:

- DataPulse
- InsightHub
- MetricFlow

Example traffic channels:

- google / organic
- direct / none
- facebook / paid_social
- newsletter / email
- affiliate_partner / referral

## Environment Variables

Use environment variables for database connection and runtime configuration.

Create `.env.example` with:

```env
DATABASE_URL=postgresql://user:password@host:port/database
CONFIG_PATH=config/project.yml
DBT_PROFILES_DIR=dbt_analytics
DBT_TARGET=dev
```

Do not include real secrets.

Make sure `.env` is in `.gitignore`.

## Database

Use Railway Postgres.

The generator should connect using `DATABASE_URL`.

The raw schema should be `raw`.

The first raw table should be `raw.daily_traffic`.

The table should include:

- id
- traffic_date
- brand
- country
- region
- device_category
- traffic_source
- traffic_medium
- campaign
- sessions
- users_count
- new_users
- returning_users
- pageviews
- engaged_sessions
- avg_session_duration_seconds
- bounce_rate
- engagement_rate
- created_at
- updated_at

Use a uniqueness rule that supports upsert behavior.

Avoid nullable values in uniqueness fields when possible.

Use default values like:

- region = "Unknown"
- campaign = "none"

## CLI Requirements

Create a simple CLI.

It should support:

```bash
uv run python -m synthetic_analytics.cli init-db
```

Creates the raw schema and raw.daily_traffic table.

```bash
uv run python -m synthetic_analytics.cli generate --mode backfill --start-date 2025-01-01 --end-date 2025-12-31
```

Generates data for the requested date range.

```bash
uv run python -m synthetic_analytics.cli generate --mode daily
```

Generates data for yesterday by default.

```bash
uv run python -m synthetic_analytics.cli generate --mode daily --date 2026-05-20
```

Generates data for a specific date.

```bash
uv run python -m synthetic_analytics.cli run-pipeline --mode daily
```

Runs generation and then runs dbt transformations.

For version 1, keep CLI simple. argparse is acceptable. Do not add Click or Typer unless necessary.

## Data Generation Requirements

Generate aggregated daily traffic data, not event-level data.

The grain should be:

```text
traffic_date
brand
country
region
device_category
traffic_source
traffic_medium
campaign
```

The generator should create one row per date and dimension combination.

Generated metrics should be internally consistent:

- users_count should be less than or equal to sessions in most cases.
- new_users + returning_users should equal users_count.
- pageviews should be greater than or equal to sessions.
- engaged_sessions should be less than or equal to sessions.
- bounce_rate should be between 0 and 1.
- engagement_rate should be between 0 and 1.
- avg_session_duration_seconds should be positive.

The output should look realistic over time.

Include:

- weekday patterns
- monthly seasonality
- gradual growth trend
- random variation
- special event spikes

## dbt Requirements

Create a dbt project in `dbt_analytics/`.

Use dbt Core and dbt Postgres.

The dbt project should create:

### staging.stg_daily_traffic

Purpose:

- Clean raw.daily_traffic
- Standardize text fields
- Cast types
- Calculate safe derived fields if needed

### marts.mart_traffic_daily

Purpose:

- Analytics-ready daily traffic table
- Include common KPIs
- Aggregate by date, brand, country, device, source, and medium

### marts.mart_traffic_summary

Purpose:

- Higher-level executive summary
- Aggregate by date and brand
- Include total sessions, users, pageviews, engagement rate, bounce rate, and other useful KPIs

Add dbt tests for:

- not null fields
- accepted values where useful
- non-negative metrics
- rates between 0 and 1
- uniqueness of important grain fields

Use dbt source definitions for raw.daily_traffic.

Do not hardcode database credentials in dbt files.

Use environment variables in profiles.yml.example.

## Railway Cron Requirements

Create `railway.json`.

The Railway start command should run the daily pipeline.

Use something like:

```bash
uv run python -m synthetic_analytics.cli run-pipeline --mode daily
```

The command must finish and exit. Railway Cron Jobs should run a task and terminate.

Do not create a long-running web server for this project.

## README Requirements

The README should explain:

- What the project does
- Why it exists
- Architecture
- Tech stack
- How the synthetic data works
- How seasonality and randomness work
- How to configure `config/project.yml`
- How to set up Railway Postgres
- How to run locally
- How to initialize the database
- How to generate a backfill
- How to run the daily job
- How to run dbt
- How to deploy as a Railway Cron Job
- How other users can customize it
- That it does not generate real website traffic

Include example commands.

## Testing Requirements

Add tests for:

- Loading and validating config
- Generator output shape
- Metric consistency
- Rate bounds
- At least one date generation

The project should pass:

```bash
uv run pytest
```

## Security

Never commit real database URLs.

Never commit Railway credentials.

Never commit `.env`.

Do not include secrets in README.

## Code Style

Use:

- Type hints
- Small functions
- Clear module boundaries
- Pydantic models for config validation if useful
- Readable Python
- Clear SQL
- Simple CLI

Avoid:

- Over-engineering
- Unnecessary dependencies
- Complex orchestration
- Web servers
- Background workers
- Real traffic generation
- Browser automation
- External APIs in version 1

## Version 1 Scope

Version 1 should only generate and transform daily traffic data.

Do not add:

- page performance table
- affiliate performance table
- funnel table
- subscription table
- Streamlit UI
- dashboard
- AI chatbot
- report generator

Those can be future versions.

## Important

This project should feel like a real analytics engineering template that someone else can clone, configure, and run.

Prioritize:

- Simplicity
- Configurability
- Reusability
- Clean README
- Realistic time series behavior
- dbt modeling
- Railway Cron compatibility
