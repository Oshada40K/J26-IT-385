"""Local prototype persistence, isolated from the unconfigured shared DB."""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
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
        db.execute('CREATE TABLE IF NOT EXISTS skill_candidates (candidate_id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS skill_assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id TEXT UNIQUE NOT NULL, candidate_id TEXT NOT NULL REFERENCES skill_candidates(candidate_id), created_at TEXT NOT NULL, source_cv_hash TEXT NOT NULL, details_json TEXT NOT NULL)')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_candidate():
    candidate_id = 'candidate_' + uuid4().hex
    token = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute('INSERT INTO skill_candidates VALUES (?, ?)', (candidate_id, token_hash(token)))
    return {'candidate_id': candidate_id, 'access_token': token, 'token_type': 'bearer'}


def candidate_for_token(token):
    with connection() as db:
        row = db.execute('SELECT candidate_id FROM skill_candidates WHERE token_hash=?', (token_hash(token),)).fetchone()
    return row['candidate_id'] if row else None


def save_assessment(candidate_id, content, details):
    assessment_id = 'assessment_' + uuid4().hex
    details = {**details, 'assessment_id': assessment_id, 'candidate_id': candidate_id, 'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'completed', 'source_cv_hash': hashlib.sha256(content).hexdigest()}
    with connection() as db:
        db.execute('INSERT INTO skill_assessments (assessment_id,candidate_id,created_at,source_cv_hash,details_json) VALUES (?,?,?,?,?)', (assessment_id, candidate_id, details['created_at'], details['source_cv_hash'], json.dumps(details)))
    return details


def latest_assessment(candidate_id):
    with connection() as db:
        row = db.execute('SELECT details_json FROM skill_assessments WHERE candidate_id=? ORDER BY id DESC LIMIT 1', (candidate_id,)).fetchone()
    return json.loads(row['details_json']) if row else None
