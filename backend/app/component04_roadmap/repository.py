# Owner: Dewmi - Component 04.
# Component-local SQLite store for Career Readiness Assessments (same pattern as Component 01;
# the shared PostgreSQL database is not configured yet).
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path():
    default = Path(__file__).parents[2] / ".data" / "component04.sqlite3"
    return Path(os.getenv("C4_DATABASE_PATH", str(default)))


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS c4_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id TEXT UNIQUE NOT NULL,
            candidate_id TEXT,
            career_id TEXT NOT NULL,
            career_name TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            previous_assessment_id TEXT,
            c1_assessment_id TEXT,
            readiness_score REAL,
            form_json TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS c4_assessments_candidate ON c4_assessments (candidate_id, id)")
        yield db
        db.commit()
    finally:
        db.close()


def _record(row):
    if not row:
        return None
    record = dict(row)
    record["form"] = json.loads(record.pop("form_json"))
    record.pop("id", None)
    return record


def save(record):
    with connection() as db:
        db.execute(
            "INSERT INTO c4_assessments (assessment_id, candidate_id, career_id, career_name, submitted_at, "
            "previous_assessment_id, c1_assessment_id, readiness_score, form_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (record["assessment_id"], record["candidate_id"], record["career_id"], record["career_name"],
             record["submitted_at"], record.get("previous_assessment_id"), record.get("c1_assessment_id"),
             record.get("readiness_score"), json.dumps(record["form"])))
    return record


def get(assessment_id):
    with connection() as db:
        return _record(db.execute("SELECT * FROM c4_assessments WHERE assessment_id=?", (assessment_id,)).fetchone())


def latest_for(candidate_id):
    with connection() as db:
        return _record(db.execute("SELECT * FROM c4_assessments WHERE candidate_id=? ORDER BY id DESC LIMIT 1",
                                  (candidate_id,)).fetchone())


def history(candidate_id, limit=10):
    if not candidate_id:
        return []
    with connection() as db:
        rows = db.execute("SELECT assessment_id, career_name, submitted_at, readiness_score FROM c4_assessments "
                          "WHERE candidate_id=? ORDER BY id DESC LIMIT ?", (candidate_id, limit)).fetchall()
    return [dict(row) for row in rows]
