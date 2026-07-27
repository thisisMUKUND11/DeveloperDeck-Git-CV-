"""Profile + share persistence.

Stores generated profiles and share snapshots as JSON blobs. Two backends,
selected automatically from DATABASE_URL:

  - SQLite  (sqlite:///...)      — zero-config local dev, single file.
  - Postgres (postgres[ql]://...) — durable production storage (Neon/Supabase),
    so shared résumé links survive restarts and redeploys.

Connections are pooled and the schema is created once per process. Opening a
fresh connection per query would mean a TCP+TLS handshake on every read against
a hosted Postgres, and would exhaust free-tier connection caps under load.

The public surface (save/get/get_age_hours/delete/save_share/get_share/
bump_share_view/share_views) is identical for both.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
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

# Columns added after the tables shipped. SQLite has no ADD COLUMN IF NOT
# EXISTS, so each is attempted and "already exists" is swallowed.
_MIGRATIONS = [
    "ALTER TABLE shares ADD COLUMN views INTEGER NOT NULL DEFAULT 0",
    # Lets a deletion request remove a user's share snapshots too, without
    # scanning every stored JSON blob.
    "ALTER TABLE shares ADD COLUMN username TEXT",
]

_init_lock = threading.Lock()
_initialised = False
_pool = None  # psycopg_pool.ConnectionPool, created lazily for Postgres


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


def _apply_schema(conn) -> None:
    for stmt in _TABLES:
        conn.execute(stmt)
    for stmt in _MIGRATIONS:
        try:
            conn.execute(stmt)
            conn.commit()
        except Exception:
            # Column already present — expected on every run after the first.
            conn.rollback()
    conn.commit()


def _ensure_init() -> None:
    """Create the pool (Postgres) and schema once per process."""
    global _initialised, _pool
    if _initialised:
        return
    with _init_lock:
        if _initialised:
            return
        if _using_postgres():
            from psycopg_pool import ConnectionPool

            # Small ceiling: free-tier Postgres plans cap total connections and
            # this service runs a single web instance.
            _pool = ConnectionPool(
                get_settings().database_url,
                min_size=1,
                max_size=5,
                timeout=10.0,
                open=True,
            )
            with _pool.connection() as conn:
                _apply_schema(conn)
        else:
            path = _sqlite_path()
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path)
            try:
                _apply_schema(conn)
            finally:
                conn.close()
        _initialised = True


@contextmanager
def _conn():
    """Yield a pooled Postgres connection, or a short-lived SQLite one.

    SQLite connections are per-call by design: they're just a file handle, and
    sqlite3 objects are not safe to share across threads.
    """
    _ensure_init()
    if _using_postgres():
        with _pool.connection() as conn:
            yield conn
        return
    conn = sqlite3.connect(_sqlite_path())
    try:
        yield conn
    finally:
        conn.close()


def _as_utc(value) -> datetime | None:
    """Normalise an `updated` column to an aware UTC datetime.

    Postgres hands back a datetime; SQLite hands back a 'YYYY-MM-DD HH:MM:SS'
    string that CURRENT_TIMESTAMP always writes in UTC.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def save(profile: Profile, *, touch: bool = True) -> None:
    """Persist a profile.

    `touch=False` rewrites the row without advancing `updated`, so cheap edits
    (e.g. restyling a cached profile with a new theme) don't reset its cache age
    and let a caller regenerate for free by toggling a setting.
    """
    updated_clause = "CURRENT_TIMESTAMP" if touch else "profiles.updated"
    with _conn() as conn:
        conn.execute(
            _sql(
                "INSERT INTO profiles (username, data, updated) "
                "VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(username) DO UPDATE SET data = excluded.data, "
                f"updated = {updated_clause}"
            ),
            (profile.username.lower(), profile.model_dump_json()),
        )
        conn.commit()


def get(username: str) -> Profile | None:
    with _conn() as conn:
        row = conn.execute(
            _sql("SELECT data FROM profiles WHERE username = ?"), (username.lower(),)
        ).fetchone()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def get_age_hours(username: str) -> float | None:
    """Hours since this profile was last generated, or None if absent."""
    with _conn() as conn:
        row = conn.execute(
            _sql("SELECT updated FROM profiles WHERE username = ?"),
            (username.lower(),),
        ).fetchone()
    if not row:
        return None
    updated = _as_utc(row[0])
    if updated is None:
        # Unparseable timestamp — treat as stale rather than serving forever.
        return float("inf")
    return (datetime.now(timezone.utc) - updated).total_seconds() / 3600.0


def delete(username: str) -> bool:
    """Remove a profile and every share snapshot made from it.

    Returns True if a profile row was actually deleted.
    """
    handle = username.lower()
    with _conn() as conn:
        cur = conn.execute(_sql("DELETE FROM profiles WHERE username = ?"), (handle,))
        deleted = cur.rowcount > 0
        conn.execute(_sql("DELETE FROM shares WHERE username = ?"), (handle,))
        conn.commit()
    return deleted


def save_share(token: str, profile: Profile) -> None:
    with _conn() as conn:
        # Upsert (portable) instead of SQLite-only INSERT OR REPLACE; preserves
        # the views counter if a token were ever reused (tokens are unique, so
        # in practice this is always an insert).
        conn.execute(
            _sql(
                "INSERT INTO shares (token, data, username) VALUES (?, ?, ?) "
                "ON CONFLICT(token) DO UPDATE SET data = excluded.data, "
                "username = excluded.username"
            ),
            (token, profile.model_dump_json(), profile.username.lower()),
        )
        conn.commit()


def get_share(token: str) -> Profile | None:
    with _conn() as conn:
        row = conn.execute(
            _sql("SELECT data FROM shares WHERE token = ?"), (token,)
        ).fetchone()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def bump_share_view(token: str) -> int | None:
    """Increment and return the view count, or None if the token doesn't exist."""
    with _conn() as conn:
        cur = conn.execute(
            _sql("UPDATE shares SET views = views + 1 WHERE token = ?"), (token,)
        )
        if cur.rowcount == 0:
            conn.commit()
            return None
        row = conn.execute(
            _sql("SELECT views FROM shares WHERE token = ?"), (token,)
        ).fetchone()
        conn.commit()
    return row[0] if row else None


def share_views(token: str) -> int | None:
    with _conn() as conn:
        row = conn.execute(
            _sql("SELECT views FROM shares WHERE token = ?"), (token,)
        ).fetchone()
    return row[0] if row else None
