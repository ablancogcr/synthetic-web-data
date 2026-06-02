from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


UPSERT_COLUMNS = [
    "traffic_date",
    "site_name",
    "page_path",
    "page_type",
    "content_category",
    "phone_brand",
    "phone_model",
    "commercial_intent",
    "country",
    "region",
    "device_category",
    "traffic_source",
    "traffic_medium",
    "campaign",
    "sessions",
    "users_count",
    "new_users",
    "returning_users",
    "pageviews",
    "engaged_sessions",
    "avg_session_duration_seconds",
    "bounce_rate",
    "engagement_rate",
    "account_signup_starts",
    "account_signups",
    "newsletter_signup_starts",
    "newsletter_signups",
    "created_at",
    "updated_at",
]

GRAIN_COLUMNS = [
    "traffic_date",
    "site_name",
    "page_path",
    "page_type",
    "content_category",
    "phone_brand",
    "phone_model",
    "commercial_intent",
    "country",
    "region",
    "device_category",
    "traffic_source",
    "traffic_medium",
    "campaign",
]

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_CONNECT_RETRIES = 8
DEFAULT_CONNECT_RETRY_DELAY_SECONDS = 2.0
DEFAULT_CONNECT_RETRY_BACKOFF = 1.5


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


def get_database_url() -> str:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def dbt_env_from_database_url(database_url: str | None = None) -> dict[str, str]:
    parsed = urlparse(database_url or get_database_url())
    if not parsed.hostname or not parsed.path:
        raise RuntimeError("DATABASE_URL must include host and database name")

    env = {
        "DBT_POSTGRES_HOST": parsed.hostname,
        "DBT_POSTGRES_PORT": str(parsed.port or 5432),
        "DBT_POSTGRES_USER": unquote(parsed.username or ""),
        "DBT_POSTGRES_PASSWORD": unquote(parsed.password or ""),
        "DBT_POSTGRES_DBNAME": parsed.path.lstrip("/"),
    }
    if not env["DBT_POSTGRES_USER"] or not env["DBT_POSTGRES_DBNAME"]:
        raise RuntimeError("DATABASE_URL must include username and database name")
    return env


def connect() -> psycopg.Connection:
    database_url = get_database_url()
    connect_timeout = _env_int(
        "DATABASE_CONNECT_TIMEOUT_SECONDS",
        DEFAULT_CONNECT_TIMEOUT_SECONDS,
    )
    attempts = _env_int("DATABASE_CONNECT_RETRIES", DEFAULT_CONNECT_RETRIES)
    delay = _env_float(
        "DATABASE_CONNECT_RETRY_DELAY_SECONDS",
        DEFAULT_CONNECT_RETRY_DELAY_SECONDS,
    )
    backoff = _env_float("DATABASE_CONNECT_RETRY_BACKOFF", DEFAULT_CONNECT_RETRY_BACKOFF)

    last_error: psycopg.OperationalError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return psycopg.connect(
                database_url,
                row_factory=dict_row,
                connect_timeout=connect_timeout,
            )
        except psycopg.OperationalError as exc:
            last_error = exc
            if attempt == attempts:
                break
            print(
                f"Database connection failed on attempt {attempt}/{attempts}; "
                f"retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= backoff

    raise RuntimeError(
        "Could not connect to the database after retrying. "
        "If this is a dormant Railway Postgres instance, wait a moment and retry."
    ) from last_error


def init_database(sql_path: str | Path | None = None) -> None:
    path = Path(sql_path or Path(__file__).parent / "sql" / "create_raw_daily_traffic.sql")
    sql = path.read_text(encoding="utf-8")
    with connect() as connection:
        connection.execute(sql)


def upsert_daily_traffic(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    records = frame[UPSERT_COLUMNS].to_dict(orient="records")
    placeholders = ", ".join(f"%({column})s" for column in UPSERT_COLUMNS)
    columns = ", ".join(UPSERT_COLUMNS)
    conflict_columns = ", ".join(GRAIN_COLUMNS)
    update_columns = [
        column
        for column in UPSERT_COLUMNS
        if column not in {*GRAIN_COLUMNS, "created_at"}
    ]
    updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)

    sql = f"""
        INSERT INTO raw.daily_traffic ({columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns})
        DO UPDATE SET {updates};
    """
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(sql, records)
    return len(records)
