"""Focused guarantees for the shared PostgreSQL connection pool."""

import psycopg
import pytest

from backend.db import close_connection_pool, get_connection, get_connection_pool


@pytest.fixture(autouse=True)
def isolated_pool(monkeypatch):
    close_connection_pool()
    monkeypatch.setenv("PGPOOL_MIN_SIZE", "1")
    monkeypatch.setenv("PGPOOL_MAX_SIZE", "2")
    monkeypatch.setenv("PGPOOL_TIMEOUT", "30")
    yield
    close_connection_pool()


def test_repeated_operations_reuse_one_physical_connection():
    backend_process_ids = []

    # More than Psycopg's default prepare threshold catches stale client
    # prepared-statement caches after a comprehensive session reset.
    for _ in range(10):
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid();")
                backend_process_ids.append(cursor.fetchone()[0])

    assert len(set(backend_process_ids)) == 1


def test_pool_is_bounded_and_returns_successful_borrows():
    pool = get_connection_pool()
    assert pool.min_size == 1
    assert pool.max_size == 2

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            assert cursor.fetchone()[0] == 1

    with get_connection() as connection:
        assert connection.pgconn.transaction_status == 0


def test_failed_transaction_does_not_poison_next_borrower():
    with pytest.raises(psycopg.errors.DivisionByZero):
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 / 0;")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            assert cursor.fetchone()[0] == 1


def test_session_state_is_reset_between_borrowers():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET application_name = 'pool-leak-test';")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW application_name;")
            assert cursor.fetchone()[0] == ""
