"""Profile + share persistence.

Stores generated profiles and share snapshots as JSON blobs. Two backends,
selected automatically from DATABASE_URL:

  - SQLite  (sqlite:///...)      — zero-config local dev, single file.
  - Postgres (postgres[ql]://...) — durable production storage (Neon/Supabase),
    so shared résumé links survive restarts and redeploys.

The public surface (save/get/save_share/get_share/bump_share_view/share_views)
is identical for both. Call init() once at startup and close() at shutdown.

All functions are blocking; call them from a worker thread (sync endpoints or
asyncio.to_thread), never directly on the event loop.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings
from .schemas import Profile

# Table definitions valid on both SQLite and Postgres (TEXT/INTEGER/TIMESTAMP
# and ON CONFLICT upserts are portable across the two).
_TABLES = [
    """CREATE TABLE IF NOT EXISTS profiles (
        username TEXT PRIMARY KEY,
        data     TEXT NOT NULL,
        updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS shares (
        token    TEXT PRIMARY KEY,
        data     TEXT NOT NULL,
        views    INTEGER NOT NULL DEFAULT 0,
        created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
]

# Postgres connection pool, created by init(). Reusing connections skips a TLS
# handshake + auth round trip to Neon/Supabase on every request.
_pool = None


def _is_postgres(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql://")


def _using_postgres() -> bool:
    return _is_postgres(get_settings().database_url)


def _sql(query: str) -> str:
    """Adapt the `?` placeholder style to `%s` when talking to Postgres."""
    return query.replace("?", "%s") if _using_postgres() else query


def _sqlite_path() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return "./proof.db"


@contextmanager
def _conn() -> Iterator:
    """Yield a DB-API connection; commit on success, roll back on error."""
    if _using_postgres():
        if _pool is None:
            init()
        # The pool's context manager commits on clean exit and rolls back on
        # an exception, then returns the connection to the pool.
        with _pool.connection() as conn:
            yield conn
        return

    # SQLite connections are cheap (a file open), so one per call is fine and
    # sidesteps sqlite3's same-thread restriction.
    conn = sqlite3.connect(_sqlite_path(), timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init() -> None:
    """Create the pool (Postgres) and ensure the schema exists. Idempotent."""
    global _pool
    if _using_postgres():
        if _pool is None:
            from psycopg_pool import ConnectionPool  # lazy: SQLite runs need no driver

            _pool = ConnectionPool(
                get_settings().database_url,
                min_size=1,
                max_size=5,
                # Free-tier Postgres drops idle connections; verify on checkout.
                check=ConnectionPool.check_connection,
                open=True,
            )
        with _pool.connection() as conn:
            for stmt in _TABLES:
                conn.execute(stmt)
            # Backfill the views column on shares tables created before it existed.
            conn.execute(
                "ALTER TABLE shares ADD COLUMN IF NOT EXISTS views INTEGER NOT NULL DEFAULT 0"
            )
        return

    path = _sqlite_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        # WAL lets readers proceed while a write is in progress.
        conn.execute("PRAGMA journal_mode=WAL")
        for stmt in _TABLES:
            conn.execute(stmt)
        # SQLite has no ADD COLUMN IF NOT EXISTS; try and ignore if already present.
        try:
            conn.execute("ALTER TABLE shares ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def save(profile: Profile) -> None:
    with _conn() as conn:
        conn.execute(
            _sql(
                "INSERT INTO profiles (username, data) VALUES (?, ?) "
                "ON CONFLICT(username) DO UPDATE SET data = excluded.data, "
                "updated = CURRENT_TIMESTAMP"
            ),
            (profile.username.lower(), profile.model_dump_json()),
        )


def get(username: str) -> Profile | None:
    with _conn() as conn:
        row = conn.execute(
            _sql("SELECT data FROM profiles WHERE username = ?"), (username.lower(),)
        ).fetchone()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def save_share(token: str, profile: Profile) -> None:
    with _conn() as conn:
        # Upsert (portable) instead of SQLite-only INSERT OR REPLACE; preserves
        # the views counter if a token were ever reused (tokens are unique, so
        # in practice this is always an insert).
        conn.execute(
            _sql(
                "INSERT INTO shares (token, data) VALUES (?, ?) "
                "ON CONFLICT(token) DO UPDATE SET data = excluded.data"
            ),
            (token, profile.model_dump_json()),
        )


def get_share(token: str) -> Profile | None:
    with _conn() as conn:
        row = conn.execute(_sql("SELECT data FROM shares WHERE token = ?"), (token,)).fetchone()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def bump_share_view(token: str) -> int | None:
    """Increment and return the view count, or None if the token doesn't exist."""
    with _conn() as conn:
        # One atomic statement (RETURNING works on SQLite 3.35+ and Postgres),
        # so concurrent opens can't read a stale count between update and select.
        row = conn.execute(
            _sql("UPDATE shares SET views = views + 1 WHERE token = ? RETURNING views"),
            (token,),
        ).fetchone()
    return row[0] if row else None


def share_views(token: str) -> int | None:
    with _conn() as conn:
        row = conn.execute(_sql("SELECT views FROM shares WHERE token = ?"), (token,)).fetchone()
    return row[0] if row else None
