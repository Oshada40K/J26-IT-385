# Owner: Dewmi - Component 04.
# Component-local SQLite store for Career Readiness Assessments (same pattern as Component 01;
# the shared PostgreSQL database is not configured yet).
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Columns added after the first evidence release (created on existing databases automatically).
EVIDENCE_EXTRA_COLUMNS = {"proof_type": "TEXT", "file_path": "TEXT", "file_name": "TEXT", "description": "TEXT",
                          "provisional_level": "REAL", "verified_level": "REAL", "check_details": "TEXT",
                          "created_at": "TEXT"}


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
        # Optional proof for claimed skills: pending | provisional | verified | rejected.
        db.execute("""CREATE TABLE IF NOT EXISTS c4_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT UNIQUE NOT NULL,
            candidate_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            type TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            cv_level_at_submission REAL NOT NULL,
            verified_at TEXT,
            verified_by_c1_assessment_id TEXT)""")
        db.execute("CREATE INDEX IF NOT EXISTS c4_evidence_candidate ON c4_evidence (candidate_id, skill_id, id)")
        existing = {row["name"] for row in db.execute("PRAGMA table_info(c4_evidence)")}
        for column, kind in EVIDENCE_EXTRA_COLUMNS.items():          # add columns to older databases
            if column not in existing:
                db.execute(f"ALTER TABLE c4_evidence ADD COLUMN {column} {kind}")
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


EVIDENCE_FIELDS = ("evidence_id", "candidate_id", "skill_id", "type", "url", "status", "submitted_at",
                   "cv_level_at_submission", "verified_at", "verified_by_c1_assessment_id") + tuple(EVIDENCE_EXTRA_COLUMNS)


def save_evidence(record):
    with connection() as db:
        db.execute(f"INSERT INTO c4_evidence ({', '.join(EVIDENCE_FIELDS)}) VALUES ({', '.join('?' * len(EVIDENCE_FIELDS))})",
                   tuple(record.get(f) for f in EVIDENCE_FIELDS))
    return record


def evidence_for(candidate_id):
    """Latest evidence per skill for a candidate: {skill_id: record}. A verified record is kept even if
    more proof is submitted later."""
    if not candidate_id:
        return {}
    with connection() as db:
        rows = db.execute("SELECT * FROM c4_evidence WHERE candidate_id=? ORDER BY id", (candidate_id,)).fetchall()
    latest = {}
    for row in rows:
        if latest.get(row["skill_id"], {}).get("status") != "verified":
            latest[row["skill_id"]] = {f: row[f] for f in EVIDENCE_FIELDS}
    return latest


def set_evidence_status(evidence_id, status, verified_at=None, c1_assessment_id=None):
    with connection() as db:
        db.execute("UPDATE c4_evidence SET status=?, verified_at=?, verified_by_c1_assessment_id=? WHERE evidence_id=?",
                   (status, verified_at, c1_assessment_id, evidence_id))


def evidence_dir():
    """Private folder for uploaded certificate files (never served as static files)."""
    default = Path(__file__).parents[2] / ".data" / "component04_evidence"
    return Path(os.getenv("C4_EVIDENCE_DIR", str(default)))


def evidence_list(candidate_id):
    """All evidence for a candidate, oldest first."""
    if not candidate_id:
        return []
    with connection() as db:
        rows = db.execute("SELECT * FROM c4_evidence WHERE candidate_id=? ORDER BY id", (candidate_id,)).fetchall()
    return [{f: row[f] for f in EVIDENCE_FIELDS} for row in rows]


def get_evidence(evidence_id):
    with connection() as db:
        row = db.execute("SELECT * FROM c4_evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
    return {f: row[f] for f in EVIDENCE_FIELDS} if row else None


def update_evidence(evidence_id, **fields):
    fields = {k: v for k, v in fields.items() if k in EVIDENCE_FIELDS and k != "evidence_id"}
    if fields:
        with connection() as db:
            db.execute(f"UPDATE c4_evidence SET {', '.join(f'{k}=?' for k in fields)} WHERE evidence_id=?",
                       (*fields.values(), evidence_id))


def delete_evidence(evidence_id):
    """Deletes the row and its private file (if any)."""
    record = get_evidence(evidence_id)
    if not record:
        return None
    with connection() as db:
        db.execute("DELETE FROM c4_evidence WHERE evidence_id=?", (evidence_id,))
    if record.get("file_path"):
        path = evidence_dir() / Path(record["file_path"]).name        # only ever inside the private folder
        path.unlink(missing_ok=True)
    return record
