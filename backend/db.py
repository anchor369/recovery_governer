import os
from threading import Lock

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool


load_dotenv()


_pool = None
_pool_lock = Lock()


def _pool_configuration():
    min_size = int(os.getenv("PGPOOL_MIN_SIZE", "1"))
    max_size = int(os.getenv("PGPOOL_MAX_SIZE", "5"))
    timeout = float(os.getenv("PGPOOL_TIMEOUT", "30"))

    if min_size < 0 or max_size < 1 or min_size > max_size:
        raise ValueError("PGPOOL sizes must satisfy 0 <= min_size <= max_size.")
    if timeout <= 0:
        raise ValueError("PGPOOL_TIMEOUT must be greater than zero.")

    return min_size, max_size, timeout


def _reset_connection(connection):
    """Remove session state before another operation borrows the connection."""

    connection.autocommit = True
    try:
        connection.execute("DISCARD ALL")
    finally:
        connection.autocommit = False


def _create_connection_pool():
    min_size, max_size, timeout = _pool_configuration()
    return ConnectionPool(
        kwargs={
            "host": os.getenv("PGHOST"),
            "port": os.getenv("PGPORT"),
            "dbname": os.getenv("PGDATABASE"),
            "user": os.getenv("PGUSER"),
            "password": os.getenv("PGPASSWORD"),
            # DISCARD ALL clears server-side prepared statements, so pooled
            # connections must not retain a conflicting client-side cache.
            "prepare_threshold": None,
        },
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        reset=_reset_connection,
        open=False,
        name="recovery-governor",
    )


def get_connection_pool():
    global _pool

    with _pool_lock:
        if _pool is None:
            pool = _create_connection_pool()
            try:
                pool.open(wait=True, timeout=pool.timeout)
            except Exception:
                pool.close()
                raise
            _pool = pool

        return _pool


def open_connection_pool():
    return get_connection_pool()


def close_connection_pool():
    global _pool

    with _pool_lock:
        pool = _pool
        _pool = None

    if pool is not None:
        pool.close()


def get_connection():
    return get_connection_pool().connection()
