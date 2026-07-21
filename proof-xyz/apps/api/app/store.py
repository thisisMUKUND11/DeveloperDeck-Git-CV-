"""Profile + share persistence.

Stores generated profiles and share snapshots as JSON blobs. Two backends,
selected automatically from DATABASE_URL:

  - SQLite  (sqlite:///...)      — zero-config local dev, single file.
  - Postgres (postgres[ql]://...) — durable production storage (Neon/Supabase),
    so shared résumé links survive restarts and redeploys.

The public surface (save/get/save_share/get_share/bump_share_view/share_views)
is identical for both.
"""

from __future__ import annotations

import sqlite3
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


def _connect():
    """Open a connection to the configured backend, ensuring the schema exists.

    Returns a DB-API connection (sqlite3 or psycopg); both expose the
    execute/commit/close and cursor fetchone/rowcount methods used below.
    """
    if _using_postgres():
        import psycopg  # imported lazily so local SQLite runs need no driver

        conn = psycopg.connect(get_settings().database_url)
        for stmt in _TABLES:
            conn.execute(stmt)
        # Backfill the views column on shares tables created before it existed.
        conn.execute(
            "ALTER TABLE shares ADD COLUMN IF NOT EXISTS views INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        return conn

    path = _sqlite_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    for stmt in _TABLES:
        conn.execute(stmt)
    # SQLite has no ADD COLUMN IF NOT EXISTS; try and ignore if already present.
    try:
        conn.execute("ALTER TABLE shares ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def save(profile: Profile) -> None:
    conn = _connect()
    try:
        conn.execute(
            _sql(
                "INSERT INTO profiles (username, data) VALUES (?, ?) "
                "ON CONFLICT(username) DO UPDATE SET data = excluded.data, "
                "updated = CURRENT_TIMESTAMP"
            ),
            (profile.username.lower(), profile.model_dump_json()),
        )
        conn.commit()
    finally:
        conn.close()


def get(username: str) -> Profile | None:
    conn = _connect()
    try:
        row = conn.execute(
            _sql("SELECT data FROM profiles WHERE username = ?"), (username.lower(),)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def save_share(token: str, profile: Profile) -> None:
    conn = _connect()
    try:
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
        conn.commit()
    finally:
        conn.close()


def get_share(token: str) -> Profile | None:
    conn = _connect()
    try:
        row = conn.execute(
            _sql("SELECT data FROM shares WHERE token = ?"), (token,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def bump_share_view(token: str) -> int | None:
    """Increment and return the view count, or None if the token doesn't exist."""
    conn = _connect()
    try:
        cur = conn.execute(
            _sql("UPDATE shares SET views = views + 1 WHERE token = ?"), (token,)
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            _sql("SELECT views FROM shares WHERE token = ?"), (token,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def share_views(token: str) -> int | None:
    conn = _connect()
    try:
        row = conn.execute(
            _sql("SELECT views FROM shares WHERE token = ?"), (token,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None
