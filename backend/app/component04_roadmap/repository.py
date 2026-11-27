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
                          "created_at": "TEXT", "status_reason": "TEXT", "reviewed_at": "TEXT", "review_note": "TEXT"}


# Target career taken from Component 03 (c3_link.py). Rows saved before this have NULL in both and are reported
# as career_source "student_selected_legacy" (the student chose the career then); they are never rewritten.
ASSESSMENT_EXTRA_COLUMNS = {"career_source": "TEXT", "c3_snapshot_json": "TEXT"}
LEGACY_CAREER_SOURCE = "student_selected_legacy"


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
        existing = {row["name"] for row in db.execute("PRAGMA table_info(c4_assessments)")}
        for column, kind in ASSESSMENT_EXTRA_COLUMNS.items():        # nullable; older rows stay untouched
            if column not in existing:
                db.execute(f"ALTER TABLE c4_assessments ADD COLUMN {column} {kind}")
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
        _create_learning_tables(db)
        yield db
        db.commit()
    finally:
        db.close()


def _record(row):
    if not row:
        return None
    record = dict(row)
    record["form"] = json.loads(record.pop("form_json"))
    snapshot = record.pop("c3_snapshot_json", None)
    record["c3_snapshot"] = json.loads(snapshot) if snapshot else None
    record["career_source"] = record.get("career_source") or LEGACY_CAREER_SOURCE
    record.pop("id", None)
    return record


def save(record):
    snapshot = record.get("c3_snapshot")
    with connection() as db:
        db.execute(
            "INSERT INTO c4_assessments (assessment_id, candidate_id, career_id, career_name, submitted_at, "
            "previous_assessment_id, c1_assessment_id, readiness_score, form_json, career_source, c3_snapshot_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (record["assessment_id"], record["candidate_id"], record["career_id"], record["career_name"],
             record["submitted_at"], record.get("previous_assessment_id"), record.get("c1_assessment_id"),
             record.get("readiness_score"), json.dumps(record["form"]), record.get("career_source"),
             json.dumps(snapshot) if snapshot is not None else None))
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
        rows = db.execute("SELECT assessment_id, career_name, submitted_at, readiness_score, career_source "
                          "FROM c4_assessments WHERE candidate_id=? ORDER BY id DESC LIMIT ?",
                          (candidate_id, limit)).fetchall()
    return [{**dict(row), "career_source": row["career_source"] or LEGACY_CAREER_SOURCE} for row in rows]


EVIDENCE_FIELDS = ("evidence_id", "candidate_id", "skill_id", "type", "url", "status", "submitted_at",
                   "cv_level_at_submission", "verified_at", "verified_by_c1_assessment_id") + tuple(EVIDENCE_EXTRA_COLUMNS)


def _encode(field, value):
    """check_details is a list of {check, result, detail}; stored as JSON text."""
    return json.dumps(value) if field == "check_details" and value is not None and not isinstance(value, str) else value


def _evidence(row):
    record = {f: row[f] for f in EVIDENCE_FIELDS}
    details = record["check_details"]
    try:
        parsed = json.loads(details) if details else None
    except ValueError:
        parsed = None
    if details and not isinstance(parsed, list):         # plain text from the first evidence release
        record["status_reason"] = record["status_reason"] or details
        parsed = [{"check": "Result", "result": "not_checked", "detail": details}]
    record["check_details"] = parsed or []
    return record


def save_evidence(record):
    with connection() as db:
        db.execute(f"INSERT INTO c4_evidence ({', '.join(EVIDENCE_FIELDS)}) VALUES ({', '.join('?' * len(EVIDENCE_FIELDS))})",
                   tuple(_encode(f, record.get(f)) for f in EVIDENCE_FIELDS))
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
            latest[row["skill_id"]] = _evidence(row)
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
    return [_evidence(row) for row in rows]


def get_evidence(evidence_id):
    with connection() as db:
        row = db.execute("SELECT * FROM c4_evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
    return _evidence(row) if row else None


def update_evidence(evidence_id, **fields):
    fields = {k: _encode(k, v) for k, v in fields.items() if k in EVIDENCE_FIELDS and k != "evidence_id"}
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


# ---------------------------------------------------------------------------------------------- adaptive tutor
# Learning progress is stored per candidate and skill (not per assessment), so it survives a new assessment or a
# career change. All tables are created with IF NOT EXISTS, so older databases upgrade automatically.
def _create_learning_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS c4_topic_progress (
        candidate_id TEXT NOT NULL,
        skill_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        state TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        low_attempts INTEGER NOT NULL DEFAULT 0,
        best_score REAL,
        last_score REAL,
        missed_json TEXT NOT NULL DEFAULT '{}',
        source TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (candidate_id, skill_id, topic_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS c4_skill_learning (
        candidate_id TEXT NOT NULL,
        skill_id TEXT NOT NULL,
        checkpoint TEXT,
        placed_stage TEXT,
        mismatch TEXT,
        demonstrated_level REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (candidate_id, skill_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS c4_learning_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id TEXT UNIQUE NOT NULL,
        candidate_id TEXT NOT NULL,
        assessment_id TEXT,
        skill_id TEXT NOT NULL,
        topic_id TEXT,
        kind TEXT NOT NULL,
        score REAL,
        answers_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS c4_attempts_candidate ON c4_learning_attempts (candidate_id, id)")
    db.execute("""CREATE TABLE IF NOT EXISTS c4_learning_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT NOT NULL,
        skill_id TEXT,
        kind TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS c4_events_candidate ON c4_learning_events (candidate_id, id)")
    db.execute("""CREATE TABLE IF NOT EXISTS c4_generated_curricula (
        skill_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        model TEXT,
        content_json TEXT NOT NULL,
        created_at TEXT NOT NULL)""")


def _progress_row(row):
    out = dict(row)
    out["missed"] = json.loads(out.pop("missed_json") or "{}")
    return out


def topic_progress(candidate_id, skill_id=None):
    """{skill_id: {topic_id: row}} (or {topic_id: row} for one skill)."""
    with connection() as db:
        if skill_id:
            rows = db.execute("SELECT * FROM c4_topic_progress WHERE candidate_id=? AND skill_id=?", (candidate_id, skill_id)).fetchall()
            return {r["topic_id"]: _progress_row(r) for r in rows}
        rows = db.execute("SELECT * FROM c4_topic_progress WHERE candidate_id=?", (candidate_id,)).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["skill_id"], {})[r["topic_id"]] = _progress_row(r)
    return out


def save_topic_progress(candidate_id, skill_id, topic_id, now, state, attempts=0, low_attempts=0, best_score=None,
                        last_score=None, missed=None, source=None):
    with connection() as db:
        db.execute("""INSERT INTO c4_topic_progress (candidate_id, skill_id, topic_id, state, attempts, low_attempts, best_score,
                      last_score, missed_json, source, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                      ON CONFLICT(candidate_id, skill_id, topic_id) DO UPDATE SET state=excluded.state,
                      attempts=excluded.attempts, low_attempts=excluded.low_attempts, best_score=excluded.best_score,
                      last_score=excluded.last_score, missed_json=excluded.missed_json, source=excluded.source,
                      updated_at=excluded.updated_at""",
                   (candidate_id, skill_id, topic_id, state, attempts, low_attempts, best_score, last_score,
                    json.dumps(missed or {}), source, now))


def skill_learning(candidate_id):
    """{skill_id: row} for the candidate."""
    with connection() as db:
        rows = db.execute("SELECT * FROM c4_skill_learning WHERE candidate_id=?", (candidate_id,)).fetchall()
    return {r["skill_id"]: dict(r) for r in rows}


def save_skill_learning(candidate_id, skill_id, now, **fields):
    allowed = {k: v for k, v in fields.items() if k in ("checkpoint", "placed_stage", "mismatch", "demonstrated_level")}
    current = skill_learning(candidate_id).get(skill_id) or {}
    row = {**{"checkpoint": None, "placed_stage": None, "mismatch": None, "demonstrated_level": 0}, **current, **allowed}
    with connection() as db:
        db.execute("""INSERT INTO c4_skill_learning (candidate_id, skill_id, checkpoint, placed_stage, mismatch, demonstrated_level,
                      updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(candidate_id, skill_id) DO UPDATE SET
                      checkpoint=excluded.checkpoint, placed_stage=excluded.placed_stage, mismatch=excluded.mismatch,
                      demonstrated_level=excluded.demonstrated_level, updated_at=excluded.updated_at""",
                   (candidate_id, skill_id, row["checkpoint"], row["placed_stage"], row["mismatch"],
                    row["demonstrated_level"], now))


def save_attempt(record):
    with connection() as db:
        db.execute("""INSERT INTO c4_learning_attempts (attempt_id, candidate_id, assessment_id, skill_id, topic_id, kind, score,
                      answers_json, result_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (record["attempt_id"], record["candidate_id"], record.get("assessment_id"), record["skill_id"],
                    record.get("topic_id"), record["kind"], record.get("score"), json.dumps(record.get("answers") or {}),
                    json.dumps(record.get("result") or {}), record["created_at"]))


def attempts_for(candidate_id, limit=50, kind=None, exclude_kind=None, topic_id=None):
    """Newest first. kind / exclude_kind / topic_id filter the rows; limit=None returns them all.
    Interactive exercise checks are stored with kind 'exercise' (practice only)."""
    sql, args = "SELECT * FROM c4_learning_attempts WHERE candidate_id=?", [candidate_id]
    for column, op, value in (("kind", "=", kind), ("kind", "<>", exclude_kind), ("topic_id", "=", topic_id)):
        if value is not None:
            sql += f" AND {column} {op} ?"
            args.append(value)
    sql += " ORDER BY id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        args.append(limit)
    with connection() as db:
        rows = db.execute(sql, args).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item.pop("id", None)
        item["answers"] = json.loads(item.pop("answers_json") or "{}")
        item["result"] = json.loads(item.pop("result_json") or "{}")
        out.append(item)
    return out


def add_learning_event(candidate_id, skill_id, kind, message, now):
    with connection() as db:
        db.execute("INSERT INTO c4_learning_events (candidate_id, skill_id, kind, message, created_at) VALUES (?,?,?,?,?)",
                   (candidate_id, skill_id, kind, message, now))


def learning_events(candidate_id, limit=20):
    with connection() as db:
        rows = db.execute("SELECT skill_id, kind, message, created_at FROM c4_learning_events WHERE candidate_id=? "
                          "ORDER BY id DESC LIMIT ?", (candidate_id, limit)).fetchall()
    return [dict(r) for r in rows]


def generated_curriculum(skill_id):
    with connection() as db:
        row = db.execute("SELECT * FROM c4_generated_curricula WHERE skill_id=?", (skill_id,)).fetchone()
    if not row:
        return None
    return {**dict(row), "topics": json.loads(row["content_json"])}


def save_generated_curriculum(skill_id, provider, model, topics, now):
    with connection() as db:
        db.execute("""INSERT INTO c4_generated_curricula (skill_id, provider, model, content_json, created_at) VALUES (?,?,?,?,?)
                      ON CONFLICT(skill_id) DO UPDATE SET provider=excluded.provider, model=excluded.model,
                      content_json=excluded.content_json, created_at=excluded.created_at""",
                   (skill_id, provider, model, json.dumps(topics), now))
