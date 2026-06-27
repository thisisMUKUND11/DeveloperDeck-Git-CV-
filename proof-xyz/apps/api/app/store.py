"""Minimal profile persistence.

Stores generated profiles as JSON blobs keyed by username. Ships with a
SQLite backend for zero-config local runs; the production target is Postgres
(swap the DSN via DATABASE_URL and replace the connection layer — the
public surface, get/save, stays the same).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_settings
from .schemas import Profile

_DDL = """
CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    data     TEXT NOT NULL,
    updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS shares (
    token    TEXT PRIMARY KEY,
    data     TEXT NOT NULL,
    created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _sqlite_path() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    # Non-sqlite DSN: fall back to a local file for this slice.
    return "./proof.db"


def _connect() -> sqlite3.Connection:
    path = _sqlite_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)  # _DDL holds multiple CREATE statements
    return conn


def save(profile: Profile) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO profiles (username, data) VALUES (?, ?) "
            "ON CONFLICT(username) DO UPDATE SET data = excluded.data, "
            "updated = CURRENT_TIMESTAMP",
            (profile.username.lower(), profile.model_dump_json()),
        )
        conn.commit()
    finally:
        conn.close()


def get(username: str) -> Profile | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM profiles WHERE username = ?", (username.lower(),)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return Profile.model_validate_json(row[0])


def save_share(token: str, profile: Profile) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO shares (token, data) VALUES (?, ?)",
            (token, profile.model_dump_json()),
        )
        conn.commit()
    finally:
        conn.close()


def get_share(token: str) -> Profile | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM shares WHERE token = ?", (token,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return Profile.model_validate_json(row[0])
