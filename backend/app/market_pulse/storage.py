"""Storage for Career Market Pulse.

Uses the shared PostgreSQL database when DATABASE_URL is configured, otherwise a local SQLite file
(the same fallback pattern as the other modules, so the API also runs without PostgreSQL).
The three market_* tables are created on first use; no existing table is read or changed.
SQL is written once with `?` placeholders and runs on both engines.
"""
import sqlite3
import threading
from contextlib import contextmanager

from . import config

SCHEMA = (
    # One row per distinct job listing ever collected (deduplicated across sources).
    """CREATE TABLE IF NOT EXISTS market_listings (
        listing_key TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        career TEXT,
        skills TEXT NOT NULL,
        is_remote INTEGER NOT NULL,
        is_sri_lanka INTEGER NOT NULL,
        salary_usd DOUBLE PRECISION,
        posted_date TEXT NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS market_listings_last_seen ON market_listings (last_seen)",
    "CREATE INDEX IF NOT EXISTS market_listings_posted ON market_listings (posted_date)",
    # Daily snapshot per market: kind is total | meta | career | skill.
    # active_count is NULL on days that were filled in from posting dates only.
    """CREATE TABLE IF NOT EXISTS market_daily_stats (
        snapshot_date TEXT NOT NULL,
        market TEXT NOT NULL,
        kind TEXT NOT NULL,
        stat_key TEXT NOT NULL,
        active_count INTEGER,
        new_count INTEGER NOT NULL DEFAULT 0,
        salary_median DOUBLE PRECISION,
        salary_p25 DOUBLE PRECISION,
        salary_p75 DOUBLE PRECISION,
        salary_count INTEGER,
        PRIMARY KEY (snapshot_date, market, kind, stat_key))""",
    # One row per collection run, with the per-source outcome as JSON.
    """CREATE TABLE IF NOT EXISTS market_refresh_runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        listings INTEGER NOT NULL DEFAULT 0,
        duplicates INTEGER NOT NULL DEFAULT 0,
        sources TEXT NOT NULL DEFAULT '[]',
        error TEXT)""",
)

_ready = set()
_ready_lock = threading.Lock()


class StorageError(RuntimeError):
    """The market database is unreachable or misconfigured."""


class Database:
    def __init__(self, raw, engine):
        self.raw, self.engine = raw, engine

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.engine == "postgresql" else sql

    def execute(self, sql, params=()):
        cursor = self.raw.cursor()
        cursor.execute(self._sql(sql), tuple(params))
        return cursor

    def query(self, sql, params=()):
        """Rows as dicts."""
        cursor = self.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def insert_many(self, sql, rows):
        """Bulk insert/upsert. `sql` contains a single VALUES {values} marker."""
        rows = [tuple(row) for row in rows]
        if not rows:
            return
        cursor = self.raw.cursor()
        if self.engine == "postgresql":
            from psycopg2.extras import execute_values
            execute_values(cursor, sql.format(values="%s"), rows, page_size=500)
        else:
            cursor.executemany(sql.format(values="(" + ",".join("?" * len(rows[0])) + ")"), rows)


def engine():
    return "postgresql" if config.database_url() else "sqlite"


def _connect():
    url = config.database_url()
    if url:
        try:
            import psycopg2
        except ImportError as exc:
            raise StorageError("DATABASE_URL is set but psycopg2 is not installed. Run: pip install -r requirements.txt") from exc
        try:
            return psycopg2.connect(url, connect_timeout=8), "postgresql", url
        except psycopg2.Error as exc:
            raise StorageError(f"Could not connect to PostgreSQL. Check DATABASE_URL. ({str(exc).strip().splitlines()[0]})") from exc
    path = config.sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=30), "sqlite", str(path)


@contextmanager
def connection():
    raw, kind, target = _connect()
    db = Database(raw, kind)
    try:
        with _ready_lock:
            if target not in _ready:
                for statement in SCHEMA:
                    db.execute(statement)
                raw.commit()
                _ready.add(target)
        yield db
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
