# Synthetic Web Analytics Pipeline

This project is a reusable analytics engineering demo that generates realistic synthetic page-level website traffic and conversion metrics, loads them into Postgres, and transforms them with dbt into reporting-ready models.

It is intentionally a data generator, not a traffic generator. It never visits real websites, runs traffic bots, uses browser automation, scrapes the web, or calls external APIs.

## What It Solves

Analytics engineers often need believable data for demos, portfolio projects, dbt practice, and warehouse modeling examples. This template gives you a configurable synthetic dataset with seasonality, growth, page mix, channel mix, device mix, country mix, special events, account signups, newsletter signups, and internally consistent metrics.

Clone it, edit `config/project.yml`, connect a Postgres database, and generate a dataset that behaves like a small real web analytics source.

## Architecture

```text
config/project.yml
        |
        v
Python generator -> raw.daily_traffic in Postgres
        |
        v
dbt staging model -> dbt mart models -> tested reporting tables
```

The first raw table is `raw.daily_traffic`.

The first dbt models are:

- `staging.stg_daily_traffic`
- `marts.mart_traffic_daily`
- `marts.mart_traffic_summary`

## Tech Stack

- Python
- uv
- Postgres
- dbt Core
- dbt Postgres
- Streamlit
- Plotly
- YAML configuration
- pytest

Optional deployment support:

- Railway Postgres
- Railway native Cron Jobs

## Imaginary Website Scenario

The default scenario is `PhoneScope`, an imaginary cell phone reviews, comparisons, deals, discount club, and newsletter website at `phonescope.example`.

Visitors can read phone reviews, compare phones, browse phone deals, visit buying guides, inspect carrier pages, sign up for a discount service, and sign up for a newsletter. The generator creates aggregated daily analytics records for website pages, not real visits, real traffic, affiliate clicks, or browser activity.

The main page-level dimensions are:

- `site_name`
- `page_path`
- `page_type`
- `content_category`
- `phone_brand`
- `phone_model`
- `commercial_intent`

## How Synthetic Data Works

The generator creates aggregated daily records at this grain:

```text
traffic_date
site_name
page_path
page_type
content_category
phone_brand
phone_model
commercial_intent
country
region
device_category
traffic_source
traffic_medium
campaign
```

Sessions are built from layered assumptions:

```text
base volume
* page traffic weight
* country multiplier
* channel multiplier
* device multiplier
* weekday seasonality
* monthly seasonality
* growth trend
* random noise
* optional event multiplier
```

Metrics are generated to stay consistent:

- `users_count` is less than or equal to `sessions`
- `new_users + returning_users = users_count`
- `pageviews >= sessions`
- `engaged_sessions <= sessions`
- `bounce_rate` and `engagement_rate` are between 0 and 1
- `avg_session_duration_seconds` is positive
- `account_signups <= account_signup_starts`
- `newsletter_signups <= newsletter_signup_starts`

Conversion metrics are derived from sessions with configurable start rates and completion rates. Channel multipliers, device multipliers, page multipliers, commercial intent, random variation, and special event conversion multipliers can all affect account signup and newsletter signup behavior.

## Configuration

Edit `config/project.yml` to customize the scenario.

You can control:

- project name and timezone
- start date and random seed
- base daily session volume
- site metadata
- page catalog
- countries and regions
- devices
- traffic channels
- weekly seasonality
- monthly seasonality
- growth trend
- randomness bounds
- special event spikes
- metric rules
- conversion rules for account signups and newsletter signups

The default config includes a realistic PhoneScope page catalog with reviews, comparisons, guides, deals, landing pages, phone database pages, carrier pages, and news articles.

## Environment

Create a local `.env` from `.env.example`:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
CONFIG_PATH=config/project.yml
DBT_PROFILES_DIR=dbt_analytics
DBT_TARGET=dev
DATABASE_CONNECT_TIMEOUT_SECONDS=10
DATABASE_CONNECT_RETRIES=8
DATABASE_CONNECT_RETRY_DELAY_SECONDS=2
DATABASE_CONNECT_RETRY_BACKOFF=1.5
RUN_DAILY_PIPELINE_ON_START=false
```

Do not commit `.env` or real database credentials.

The `DATABASE_CONNECT_*` settings are optional. They let the CLI and Streamlit app retry while a dormant or cold-starting Postgres instance wakes up.

`RUN_DAILY_PIPELINE_ON_START` is only used by the optional Railway start command. Leave it as `false` for a normal deploy that should not generate data on startup. Set it to `true` only for a scheduled job service that should run the daily pipeline.

## Local Setup

Install dependencies with uv:

```bash
uv sync
```

Show the CLI:

```bash
uv run python -m synthetic_analytics.cli --help
```

## Postgres Setup

Use any Postgres database you can connect to locally or remotely. Local Postgres, Docker Postgres, hosted Postgres, and Railway Postgres all work.

1. Create a Postgres database.
2. Copy its connection string.
3. Set it as `DATABASE_URL` in `.env`.
4. Set `CONFIG_PATH=config/project.yml`, `DBT_PROFILES_DIR=dbt_analytics`, and `DBT_TARGET=dev`.

Example local connection string:

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/synthetic_analytics
```

If your Postgres provider sleeps while idle, the first connection can fail while the database wakes. The Python CLI and Streamlit app retry database connections automatically using the `DATABASE_CONNECT_*` settings.

## Initialize the Database

Run this after `DATABASE_URL` is configured:

```bash
uv run python -m synthetic_analytics.cli init-db
```

This creates the `raw` schema and `raw.daily_traffic` table with an upsert-friendly unique constraint.

Version 2 replaces the old brand-level raw grain with a page-level grain. If your database already has the earlier brand-based `raw.daily_traffic` table, use a fresh database or drop and recreate `raw.daily_traffic` before regenerating data. This avoids mixing old brand rows with the new PhoneScope page-level rows.

## Generate a Historical Backfill

```bash
uv run python -m synthetic_analytics.cli generate --mode backfill --start-date 2025-01-01 --end-date 2025-12-31
```

## Run the Daily Job

Generate yesterday by default:

```bash
uv run python -m synthetic_analytics.cli generate --mode daily
```

Generate a specific date:

```bash
uv run python -m synthetic_analytics.cli generate --mode daily --date 2026-05-20
```

## Run dbt

The repo includes `dbt_analytics/profiles.yml` and `dbt_analytics/profiles.yml.example`. Both use environment variables and do not contain credentials.

The Python CLI derives the `DBT_POSTGRES_*` variables from `DATABASE_URL` automatically.

Run:

```bash
uv run python -m synthetic_analytics.cli dbt-build
```

If you run `uv run dbt build --project-dir dbt_analytics --profiles-dir dbt_analytics` directly, set the `DBT_POSTGRES_*` variables in your shell first.

## Run the Full Pipeline

This generates data and then runs `dbt build`:

```bash
uv run python -m synthetic_analytics.cli run-pipeline --mode daily
```

## Version 2: Streamlit Data Explorer

Version 2 adds a lightweight local Streamlit app for inspecting the generated analytics data visually during development.

The app connects to the same Postgres database through `DATABASE_URL` and can preview:

- `raw.daily_traffic`
- `staging.stg_daily_traffic`
- `marts.mart_traffic_daily`
- `marts.mart_traffic_summary`

It includes database status, sidebar filters, KPI cards, time series charts, breakdown charts, raw data preview, dbt model preview, and simple data quality checks for traffic and conversion metrics.

Run it locally:

```bash
uv sync
uv run streamlit run ui/streamlit_app.py
```

The Streamlit explorer is for local inspection and development. It does not replace the CLI and is not intended for public deployment yet.

## Optional Railway Cron Deployment

`railway.json` uses this start command:

```bash
uv run python -m synthetic_analytics.cli railway-start
```

By default, this command exits without touching the database. This prevents a first deployment or manual service restart from inserting data.

For a Railway Cron Job that should generate daily data, set this service variable:

```bash
RUN_DAILY_PIPELINE_ON_START=true
```

Then configure the Railway service as a native Cron Job. When the cron starts the service, `railway-start` runs the daily pipeline and exits; it does not start a web server.

## Tests

Run:

```bash
uv run pytest
```

The tests cover config loading, generator shape, traffic metric consistency, conversion metric consistency, rate bounds, and deterministic generation for a date.

## Customization

To create a new demo dataset:

1. Edit `config/project.yml`.
2. Adjust the site, pages, countries, devices, and channels.
3. Tune weekly and monthly seasonality.
4. Add special events for launches, promotions, or seasonal spikes.
5. Change the random seed if you want a different but repeatable dataset.
6. Run a backfill, then schedule the daily job locally, with cron, or with a hosted scheduler such as Railway Cron.
