"""SQLite persistence for Component 01 assessments, candidates, and dynamic taxonomy."""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import database_path
from .taxonomy_repository import (
    ensure_taxonomy_schema,
    link_occupation_skill,
    norm_key,
    save_structured_assessment_items,
    upsert_occupation,
    upsert_skill,
)

DATA_DIR = Path(__file__).with_name('data')


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE IF NOT EXISTS skill_candidates (candidate_id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS skill_assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id TEXT UNIQUE NOT NULL, candidate_id TEXT NOT NULL REFERENCES skill_candidates(candidate_id), created_at TEXT NOT NULL, source_cv_hash TEXT NOT NULL, details_json TEXT NOT NULL)')
        ensure_taxonomy_schema(db)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_taxonomy_bootstrapped(db):
    """Seed SQLite taxonomy once from baseline aliases, O*NET catalogue, and core cross-domain occupations."""
    booted = db.execute("SELECT value FROM taxonomy_meta WHERE key='bootstrap_version'").fetchone()
    if booted and booted['value'] == 'dynamic_v1':
        return

    # 1. Seed baseline technical aliases & descriptions into DB first (so canonical forms + short aliases exist in DB).
    from .services.category_classifier import classify_skill_category
    seed_file = DATA_DIR / 'technical_skills.json'
    if seed_file.exists():
        seed_data = json.loads(seed_file.read_text(encoding='utf-8'))
        for name, meta in seed_data.items():
            cat = classify_skill_category(name, meta.get('description', ''))
            upsert_skill(
                db,
                canonical_name=name,
                category=cat,
                description=meta.get('description', ''),
                source='taxonomy_seed',
                skill_type='skill',
                is_discovered=False,
                matchable=True,
                aliases=meta.get('aliases', []),
                case_sensitive_aliases=meta.get('case_sensitive_aliases', []),
            )

    # 2. Seed baseline occupations across domains if not already populated.
    domains_file = DATA_DIR / 'domains.json'
    if domains_file.exists() and seed_file.exists():
        domains_data = json.loads(domains_file.read_text(encoding='utf-8'))
        seed_data = json.loads(seed_file.read_text(encoding='utf-8'))
        skill_ids = {r['normalized_name']: r['id'] for r in db.execute('SELECT id, normalized_name FROM skills').fetchall()}
        for domain_name, dmeta in domains_data.items():
            occ_id = upsert_occupation(
                db,
                code='field:' + norm_key(domain_name).replace(' ', '_'),
                title=domain_name,
                source='taxonomy_seed',
                career_field=domain_name,
                description=dmeta.get('description', ''),
            )
            for sname, smeta in seed_data.items():
                if domain_name in (smeta.get('domains') or []):
                    sid = skill_ids.get(norm_key(sname))
                    if sid:
                        link_occupation_skill(db, occupation_id=occ_id, skill_id=sid, relation_type='associated', weight=1.0, source='taxonomy_seed')

    # 3. Import full O*NET 30.0 catalogue (889 occupations across ALL job categories + tech/soft skills + aliases).
    from .services.onet_importer import import_onet_catalogue
    import_onet_catalogue(db)

    db.execute("INSERT OR REPLACE INTO taxonomy_meta (key, value) VALUES ('bootstrap_version', 'dynamic_v1')")


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
    details = {
        **details,
        'assessment_id': assessment_id,
        'candidate_id': candidate_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'completed',
        'source_cv_hash': hashlib.sha256(content).hexdigest(),
    }
    with connection() as db:
        ensure_taxonomy_bootstrapped(db)
        db.execute(
            'INSERT INTO skill_assessments (assessment_id,candidate_id,created_at,source_cv_hash,details_json) VALUES (?,?,?,?,?)',
            (assessment_id, candidate_id, details['created_at'], details['source_cv_hash'], json.dumps(details)),
        )
        save_structured_assessment_items(db, assessment_id, details)
    return details


def latest_assessment(candidate_id):
    with connection() as db:
        row = db.execute('SELECT details_json FROM skill_assessments WHERE candidate_id=? ORDER BY id DESC LIMIT 1', (candidate_id,)).fetchone()
    return json.loads(row['details_json']) if row else None
