import sqlite3
from contextlib import contextmanager

from .config import database_path


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS auth_users (
                id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES auth_users(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_resets (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES auth_users(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_attempts (
                key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires_at INTEGER NOT NULL
            );
        ''')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
