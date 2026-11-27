"""Normalized SQLite taxonomy and assessment persistence for Component 01."""
import json
import re
from datetime import datetime, timezone

CAREER_CATEGORIES = (
    'Technical skills',
    'Programming languages',
    'Frameworks and libraries',
    'Tools and platforms',
    'Databases',
    'Domain-specific skills',
    'Soft skills',
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def norm_key(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip()).casefold()


def ensure_taxonomy_schema(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS occupations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            normalized_title TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            career_field TEXT NOT NULL DEFAULT 'General',
            description TEXT NOT NULL DEFAULT '',
            reference_uri TEXT,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            normalized_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL DEFAULT 'Domain-specific skills',
            description TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'esco',
            reference_uri TEXT,
            skill_type TEXT NOT NULL DEFAULT 'skill',
            is_discovered INTEGER NOT NULL DEFAULT 0,
            matchable INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS skill_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            alias TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            case_sensitive INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'taxonomy',
            UNIQUE(skill_id, normalized_alias, case_sensitive)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS occupation_skills (
            occupation_id INTEGER NOT NULL REFERENCES occupations(id) ON DELETE CASCADE,
            skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL DEFAULT 'associated',
            weight REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL DEFAULT 'taxonomy',
            PRIMARY KEY (occupation_id, skill_id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS skill_assessment_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id TEXT NOT NULL REFERENCES skill_assessments(assessment_id) ON DELETE CASCADE,
            skill_id INTEGER REFERENCES skills(id) ON DELETE SET NULL,
            skill_name TEXT NOT NULL,
            category TEXT NOT NULL,
            source_channel TEXT NOT NULL DEFAULT 'combined',
            level INTEGER NOT NULL,
            percentage INTEGER NOT NULL,
            confidence TEXT NOT NULL,
            status TEXT NOT NULL,
            is_discovered INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL,
            xai_json TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS skill_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_item_id INTEGER NOT NULL REFERENCES skill_assessment_items(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            section TEXT NOT NULL,
            excerpt TEXT NOT NULL,
            match_method TEXT NOT NULL,
            similarity_score REAL,
            url TEXT
        )
    """)
    db.execute('CREATE TABLE IF NOT EXISTS taxonomy_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_skill_aliases_norm ON skill_aliases(normalized_alias)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_occ_skills_skill ON occupation_skills(skill_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_occ_field ON occupations(career_field)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_assess_items_aid ON skill_assessment_items(assessment_id)')


def upsert_occupation(db, *, code: str, title: str, source: str, career_field: str = 'General',
                      description: str = '', reference_uri: str | None = None) -> int:
    ntitle = norm_key(title)
    row = db.execute('SELECT id, source, description, reference_uri FROM occupations WHERE normalized_title=?', (ntitle,)).fetchone()
    if row:
        new_desc = description if len(description) > len(row['description'] or '') else row['description']
        new_uri = reference_uri or row['reference_uri']
        db.execute(
            'UPDATE occupations SET description=?, reference_uri=?, career_field=CASE WHEN career_field="General" THEN ? ELSE career_field END WHERE id=?',
            (new_desc, new_uri, career_field, row['id']),
        )
        return row['id']
    cur = db.execute(
        'INSERT INTO occupations (code, title, normalized_title, source, career_field, description, reference_uri, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (code, title.strip(), ntitle, source, career_field, description, reference_uri, _now()),
    )
    return cur.lastrowid


def upsert_skill(db, *, canonical_name: str, category: str = 'Domain-specific skills', description: str = '',
                 source: str = 'esco', reference_uri: str | None = None, skill_type: str = 'skill',
                 is_discovered: bool = False, matchable: bool = True, aliases: list[str] | None = None,
                 case_sensitive_aliases: list[str] | None = None) -> int:
    nname = norm_key(canonical_name)
    if not nname:
        raise ValueError('Skill canonical_name cannot be empty')
    row = db.execute('SELECT id, source, description, reference_uri, is_discovered, matchable FROM skills WHERE normalized_name=?', (nname,)).fetchone()
    if row:
        skill_id = row['id']
        # Upgrade discovered -> taxonomy if ESCO/O*NET provides an authoritative definition.
        upgrade_source = source if (row['is_discovered'] and not is_discovered) else row['source']
        new_discovered = 0 if (row['is_discovered'] and not is_discovered) else row['is_discovered']
        new_desc = description if len(description) > len(row['description'] or '') else row['description']
        new_uri = reference_uri or row['reference_uri']
        new_matchable = 1 if (matchable or row['matchable']) else 0
        db.execute(
            'UPDATE skills SET source=?, is_discovered=?, description=?, reference_uri=?, matchable=? WHERE id=?',
            (upgrade_source, new_discovered, new_desc, new_uri, new_matchable, skill_id),
        )
    else:
        cur = db.execute(
            'INSERT INTO skills (canonical_name, normalized_name, category, description, source, reference_uri, skill_type, is_discovered, matchable, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (canonical_name.strip(), nname, category, description, source, reference_uri, skill_type, 1 if is_discovered else 0, 1 if matchable else 0, _now()),
        )
        skill_id = cur.lastrowid

    all_aliases = list(aliases or [])
    if canonical_name.strip() not in all_aliases and not (case_sensitive_aliases and canonical_name.strip() in case_sensitive_aliases):
        all_aliases.append(canonical_name.strip())
    for alias in all_aliases:
        na = norm_key(alias)
        if na:
            db.execute(
                'INSERT OR IGNORE INTO skill_aliases (skill_id, alias, normalized_alias, case_sensitive, source) VALUES (?, ?, ?, 0, ?)',
                (skill_id, alias.strip(), na, source),
            )
    for alias in (case_sensitive_aliases or []):
        na = norm_key(alias)
        if na:
            db.execute(
                'INSERT OR IGNORE INTO skill_aliases (skill_id, alias, normalized_alias, case_sensitive, source) VALUES (?, ?, ?, 1, ?)',
                (skill_id, alias.strip(), na, source),
            )
    return skill_id


def link_occupation_skill(db, *, occupation_id: int, skill_id: int, relation_type: str = 'associated',
                          weight: float = 1.0, source: str = 'taxonomy'):
    db.execute(
        """
        INSERT INTO occupation_skills (occupation_id, skill_id, relation_type, weight, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(occupation_id, skill_id) DO UPDATE SET
            weight = MAX(occupation_skills.weight, excluded.weight),
            relation_type = CASE
                WHEN excluded.relation_type = 'essential' THEN 'essential'
                WHEN excluded.relation_type = 'in_demand' AND occupation_skills.relation_type != 'essential' THEN 'in_demand'
                ELSE occupation_skills.relation_type
            END
        """,
        (occupation_id, skill_id, relation_type, weight, source),
    )


def save_structured_assessment_items(db, assessment_id: str, details: dict):
    """Persist structured skill items, discovered skills, and evidence rows in DB."""
    skill_id_by_name = {
        row['normalized_name']: row['id']
        for row in db.execute('SELECT id, normalized_name FROM skills').fetchall()
    }

    def persist_channel(channel_name: str, items: list[dict]):
        for item in items:
            nname = norm_key(item['name'])
            sid = skill_id_by_name.get(nname)
            if sid is None and item.get('is_discovered'):
                sid = upsert_skill(
                    db,
                    canonical_name=item['name'],
                    category=item.get('category', 'Domain-specific skills'),
                    description=item.get('reason', ''),
                    source='discovered',
                    is_discovered=True,
                    matchable=True,
                )
                skill_id_by_name[nname] = sid
            cur = db.execute(
                """
                INSERT INTO skill_assessment_items
                (assessment_id, skill_id, skill_name, category, source_channel, level, percentage, confidence, status, is_discovered, reason, xai_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    sid,
                    item['name'],
                    item.get('category', 'Domain-specific skills'),
                    channel_name,
                    int(item['level']),
                    int(item.get('percentage', item['level'] * 20)),
                    item.get('confidence', 'low'),
                    item.get('status', 'provisional'),
                    1 if item.get('is_discovered') else 0,
                    item.get('reason', ''),
                    json.dumps(item.get('xai', {})),
                ),
            )
            item_id = cur.lastrowid
            for ev in item.get('evidence', []):
                db.execute(
                    """
                    INSERT INTO skill_evidence
                    (assessment_item_id, source_type, section, excerpt, match_method, similarity_score, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        ev.get('source', 'cv_other'),
                        ev.get('section', 'other'),
                        ev.get('text', ''),
                        ev.get('match_method', 'explicit'),
                        ev.get('semantic_similarity'),
                        ev.get('url'),
                    ),
                )

    persist_channel('combined', details.get('skills', []))
    for src_name, src_payload in (details.get('source_profiles') or {}).items():
        if isinstance(src_payload, dict) and src_payload.get('skills'):
            persist_channel(src_name, src_payload['skills'])


def load_matchable_skills(db) -> list[dict]:
    """Load matchable skills and aliases from DB for explicit + semantic matching."""
    skills_rows = db.execute(
        'SELECT id, canonical_name, normalized_name, category, description, source, reference_uri, skill_type, is_discovered, matchable FROM skills ORDER BY id'
    ).fetchall()
    alias_rows = db.execute('SELECT skill_id, alias, case_sensitive FROM skill_aliases').fetchall()
    aliases_by_skill = {}
    for row in alias_rows:
        aliases_by_skill.setdefault(row['skill_id'], []).append((row['alias'], bool(row['case_sensitive'])))
    occ_rows = db.execute(
        """
        SELECT os.skill_id, o.title, o.career_field
        FROM occupation_skills os
        JOIN occupations o ON o.id = os.occupation_id
        """
    ).fetchall()
    occs_by_skill = {}
    fields_by_skill = {}
    for row in occ_rows:
        occs_by_skill.setdefault(row['skill_id'], []).append(row['title'])
        fields_by_skill.setdefault(row['skill_id'], set()).add(row['career_field'])

    result = []
    for row in skills_rows:
        sid = row['id']
        result.append({
            'id': sid,
            'canonical_name': row['canonical_name'],
            'normalized_name': row['normalized_name'],
            'category': row['category'],
            'description': row['description'],
            'source': row['source'],
            'reference_uri': row['reference_uri'],
            'skill_type': row['skill_type'],
            'is_discovered': bool(row['is_discovered']),
            'matchable': bool(row['matchable']),
            'aliases': aliases_by_skill.get(sid, [(row['canonical_name'], False)]),
            'occupations': occs_by_skill.get(sid, []),
            'career_fields': sorted(fields_by_skill.get(sid, set())),
        })
    return result


def search_skills(db, query: str = '', category: str | None = None, source: str | None = None, limit: int = 50) -> list[dict]:
    sql = 'SELECT id, canonical_name, category, description, source, reference_uri, is_discovered, matchable FROM skills WHERE 1=1'
    params = []
    if query:
        sql += ' AND (normalized_name LIKE ? OR LOWER(description) LIKE ?)'
        q = f'%{norm_key(query)}%'
        params.extend([q, q])
    if category:
        sql += ' AND category = ?'
        params.append(category)
    if source:
        sql += ' AND source = ?'
        params.append(source)
    sql += ' ORDER BY is_discovered ASC, canonical_name COLLATE NOCASE ASC LIMIT ?'
    params.append(max(1, min(limit, 200)))
    rows = db.execute(sql, params).fetchall()
    results = []
    for row in rows:
        occs = [
            {'title': r['title'], 'career_field': r['career_field'], 'relation_type': r['relation_type']}
            for r in db.execute(
                """
                SELECT o.title, o.career_field, os.relation_type
                FROM occupation_skills os
                JOIN occupations o ON o.id = os.occupation_id
                WHERE os.skill_id = ?
                ORDER BY os.weight DESC LIMIT 12
                """,
                (row['id'],),
            ).fetchall()
        ]
        results.append({
            'id': row['id'],
            'name': row['canonical_name'],
            'category': row['category'],
            'description': row['description'],
            'source': row['source'],
            'reference_uri': row['reference_uri'],
            'is_discovered': bool(row['is_discovered']),
            'occupations': occs,
        })
    return results


def search_occupations(db, query: str = '', career_field: str | None = None, limit: int = 50) -> list[dict]:
    sql = 'SELECT id, code, title, source, career_field, description, reference_uri FROM occupations WHERE 1=1'
    params = []
    if query:
        sql += ' AND (normalized_title LIKE ? OR LOWER(description) LIKE ?)'
        q = f'%{norm_key(query)}%'
        params.extend([q, q])
    if career_field:
        sql += ' AND career_field = ?'
        params.append(career_field)
    sql += ' ORDER BY title COLLATE NOCASE ASC LIMIT ?'
    params.append(max(1, min(limit, 200)))
    rows = db.execute(sql, params).fetchall()
    results = []
    for row in rows:
        skills = [
            {'name': r['canonical_name'], 'category': r['category'], 'relation_type': r['relation_type'], 'weight': r['weight']}
            for r in db.execute(
                """
                SELECT s.canonical_name, s.category, os.relation_type, os.weight
                FROM occupation_skills os
                JOIN skills s ON s.id = os.skill_id
                WHERE os.occupation_id = ?
                ORDER BY os.weight DESC, s.canonical_name ASC LIMIT 25
                """,
                (row['id'],),
            ).fetchall()
        ]
        results.append({
            'id': row['id'],
            'code': row['code'],
            'title': row['title'],
            'source': row['source'],
            'career_field': row['career_field'],
            'description': row['description'],
            'reference_uri': row['reference_uri'],
            'skills': skills,
        })
    return results


def taxonomy_stats(db) -> dict:
    return {
        'occupations': db.execute('SELECT count(*) FROM occupations').fetchone()[0],
        'skills': db.execute('SELECT count(*) FROM skills').fetchone()[0],
        'discovered_skills': db.execute('SELECT count(*) FROM skills WHERE is_discovered=1').fetchone()[0],
        'aliases': db.execute('SELECT count(*) FROM skill_aliases').fetchone()[0],
        'occupation_skill_links': db.execute('SELECT count(*) FROM occupation_skills').fetchone()[0],
    }
