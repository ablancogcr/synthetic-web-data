from unittest.mock import Mock

import psycopg

from synthetic_analytics import database


def test_connect_retries_transient_operational_errors(monkeypatch) -> None:
    connection = Mock()
    connect_attempts = Mock(
        side_effect=[
            psycopg.OperationalError("database system is starting up"),
            connection,
        ]
    )

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/db")
    monkeypatch.setenv("DATABASE_CONNECT_RETRIES", "2")
    monkeypatch.setenv("DATABASE_CONNECT_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("DATABASE_CONNECT_RETRY_BACKOFF", "1")
    monkeypatch.setattr(database.psycopg, "connect", connect_attempts)

    assert database.connect() is connection
    assert connect_attempts.call_count == 2
