"""Import O*NET 30.0 occupations, skills, aliases, and relationships into SQLite."""
import json
import re
from pathlib import Path
from ..taxonomy_repository import _now, norm_key
from .category_classifier import classify_skill_category

ONET_CATALOG_PATH = (
    Path(__file__).parents[2]
    / 'component03_career'
    / 'job_matching_training_output'
    / 'preprocessing_catalogue.json'
)

SOC_CAREER_FIELDS = {
    '11': 'Business & Management',
    '13': 'Finance & Business Operations',
    '15': 'IT & Computing',
    '17': 'Engineering & Architecture',
    '19': 'Science & Research',
    '21': 'Community & Social Services',
    '23': 'Legal & Compliance',
    '25': 'Education & Training',
    '27': 'Design, Arts & Media',
    '29': 'Healthcare',
    '31': 'Healthcare Support',
    '33': 'Security & Protective Services',
    '35': 'Hospitality & Food Services',
    '37': 'Facilities & Maintenance',
    '39': 'Personal Care & Services',
    '41': 'Marketing & Sales',
    '43': 'Administration & Support',
    '45': 'Agriculture & Natural Resources',
    '47': 'Construction & Extraction',
    '49': 'Technical Installation & Repair',
    '51': 'Manufacturing & Production',
    '53': 'Logistics & Transportation',
}

GENERIC_ONET_SUFFIX = re.compile(
    r'\b(?:software|programs?|tools?|systems?|applications?|packages?)$', re.I
)
GENERIC_ONET_PREFIX = re.compile(
    r'^(?:web browser|email|office suite|word processing|spreadsheet|presentation|'
    r'accounting|database user interface|database reporting|desktop publishing|'
    r'electronic mail|graphic presentation|project management|customer relationship management|'
    r'enterprise resource planning|analytical or scientific|development environment|'
    r'operating system|internet browser|file versioning|calendar and scheduling)\b',
    re.I,
)


def soc_career_field(code: str, title: str = '') -> str:
    prefix = (code or '').split('-', 1)[0]
    field = SOC_CAREER_FIELDS.get(prefix, 'Other Professional Fields')
    t = title.casefold()
    if prefix == '15' and any(k in t for k in ('data scientist', 'statistician', 'mathematician', 'operations research')):
        return 'Data Science & Analytics'
    if prefix in {'11', '13'} and any(k in t for k in ('accountant', 'auditor', 'financial', 'budget', 'credit', 'tax', 'loan', 'treasurer', 'controller')):
        return 'Finance & Accounting'
    if prefix in {'11', '41'} and any(k in t for k in ('marketing', 'advertising', 'public relations', 'promotions', 'brand', 'sales')):
        return 'Marketing & Sales'
    if prefix == '27' and any(k in t for k in ('designer', 'graphic', 'ux', 'ui', 'multimedia', 'art')):
        return 'Design & Media'
    return field


AMBIGUOUS_SINGLE_WORDS = {
    'act', 'aim', 'access', 'app', 'apex', 'base', 'box', 'canvas', 'chef', 'compass', 'crystal',
    'dart', 'eclipse', 'email', 'express', 'flow', 'focus', 'github', 'go', 'google', 'hub',
    'ideas', 'image', 'impact', 'insight', 'java', 'link', 'looker', 'mail', 'make', 'match',
    'matrix', 'mint', 'notes', 'notion', 'office', 'oracle', 'outlook', 'page', 'palm', 'path',
    'peak', 'plan', 'plus', 'point', 'portal', 'prime', 'prism', 'project', 'pulse', 'puppet',
    'quick', 'rapid', 'reach', 'react', 'reason', 'rise', 'root', 'rust', 'sage', 'salt', 'scale',
    'scope', 'sense', 'share', 'shell', 'shift', 'sight', 'signal', 'sketch', 'slack', 'smart',
    'spark', 'spring', 'stage', 'star', 'stream', 'studio', 'swift', 'sync', 'target', 'teams',
    'track', 'unity', 'vector', 'view', 'vision', 'wave', 'web', 'word', 'work', 'zoom',
}


def _is_matchable_onet_tech(label: str) -> bool:
    s = (label or '').strip()
    if len(s) < 2 or len(s) > 70:
        return False
    # Generic descriptive categories like "Word processing software" should not fire as explicit CV matches.
    if GENERIC_ONET_PREFIX.search(s) and GENERIC_ONET_SUFFIX.search(s):
        return False
    if s.lower().endswith(' software') and len(s.split()) >= 3:
        return False
    # Skip single-word ambiguous names from auto-explicit matching (they remain searchable via qualified names or semantics).
    if ' ' not in s and s.casefold() in AMBIGUOUS_SINGLE_WORDS:
        return False
    # Never auto-match GitHub or LinkedIn as a CV explicit skill; they are profile platforms.
    if s.casefold() in {'github', 'linkedin'}:
        return False
    return True


def import_onet_catalogue(db, catalog_path: Path = ONET_CATALOG_PATH) -> dict:
    """Bulk-import O*NET occupations, tech skills, soft skills, aliases, and links in one transaction."""
    if not catalog_path.exists():
        return {'imported': False, 'reason': 'O*NET catalogue file not found'}

    already = db.execute("SELECT value FROM taxonomy_meta WHERE key='onet_version_imported'").fetchone()
    data = json.loads(catalog_path.read_text(encoding='utf-8'))
    version = str(data.get('onet_version', '30.0'))
    if already and already['value'] == version:
        return {'imported': False, 'reason': 'already_imported', 'version': version}

    now = _now()
    soft_names = data.get('soft_names', [])
    soft_aliases = data.get('soft_aliases', {})
    tech_aliases = data.get('tech_aliases', {})
    jobs = data.get('jobs', [])

    existing_skills = {
        row['normalized_name']: row['id']
        for row in db.execute('SELECT id, normalized_name FROM skills').fetchall()
    }
    existing_occs = {
        row['normalized_title']: row['id']
        for row in db.execute('SELECT id, normalized_title FROM occupations').fetchall()
    }

    def ensure_skill(canonical: str, category: str, desc: str, source: str, skill_type: str, matchable: bool) -> int:
        nk = norm_key(canonical)
        if nk in existing_skills:
            return existing_skills[nk]
        cur = db.execute(
            'INSERT INTO skills (canonical_name, normalized_name, category, description, source, reference_uri, skill_type, is_discovered, matchable, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)',
            (canonical.strip(), nk, category, desc, source, None, skill_type, 1 if matchable else 0, now),
        )
        sid = cur.lastrowid
        existing_skills[nk] = sid
        if matchable:
            db.execute(
                'INSERT OR IGNORE INTO skill_aliases (skill_id, alias, normalized_alias, case_sensitive, source) VALUES (?, ?, ?, 0, ?)',
                (sid, canonical.strip(), nk, source),
            )
        return sid

    # 1. Import 18 O*NET Soft Skills & aliases (store as soft skills; matchable in Skills/explicit contexts)
    soft_ids = []
    for sname in soft_names:
        sid = ensure_skill(
            sname,
            'Soft skills',
            f'Workplace soft skill and competency: {sname} (O*NET {version})',
            'onet',
            'soft',
            True,
        )
        soft_ids.append(sid)
    for alias, target in soft_aliases.items():
        sid = existing_skills.get(norm_key(target))
        if sid and norm_key(alias) and len(alias.split()) >= 2:
            db.execute(
                'INSERT OR IGNORE INTO skill_aliases (skill_id, alias, normalized_alias, case_sensitive, source) VALUES (?, ?, ?, 0, ?)',
                (sid, alias, norm_key(alias), 'onet'),
            )

    # 2. Import Occupations and Technology Skills + Occupation-Skill links
    occ_links = []
    for job in jobs:
        title = (job.get('title') or '').strip()
        if not title:
            continue
        ntitle = norm_key(title)
        code = job.get('code', '')
        field = soc_career_field(code, title)
        desc = (job.get('description') or '').strip()
        if ntitle in existing_occs:
            occ_id = existing_occs[ntitle]
        else:
            cur = db.execute(
                'INSERT INTO occupations (code, title, normalized_title, source, career_field, description, reference_uri, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (code, title, ntitle, 'onet', field, desc, f'onet:{code}', now),
            )
            occ_id = cur.lastrowid
            existing_occs[ntitle] = occ_id

        # Link top soft skills for this occupation (importance >= 0.65)
        soft_imp = job.get('soft_importance') or []
        for idx, sid in enumerate(soft_ids):
            if idx < len(soft_imp) and soft_imp[idx] >= 0.65:
                occ_links.append((occ_id, sid, 'essential' if soft_imp[idx] >= 0.78 else 'optional', round(float(soft_imp[idx]), 3), 'onet'))

        # Link O*NET tech skills
        for tech_key, tech_meta in (job.get('tech') or {}).items():
            label = (tech_meta.get('label') or tech_key).strip()
            cats = tech_meta.get('categories') or []
            in_demand = bool(tech_meta.get('in_demand'))
            matchable = _is_matchable_onet_tech(label)
            cat = classify_skill_category(label, ', '.join(cats), o_net_categories=cats, skill_type='technology')
            sid = ensure_skill(
                label,
                cat,
                f"{label} ({'; '.join(cats[:2])})" if cats else f'O*NET technology skill: {label}',
                'onet',
                'technology',
                matchable,
            )
            occ_links.append((occ_id, sid, 'in_demand' if in_demand else 'associated', 1.25 if in_demand else 0.9, 'onet'))

    # 3. Import O*NET tech_aliases (skip overly short/generic aliases)
    for alias, target_key in tech_aliases.items():
        sid = existing_skills.get(norm_key(target_key))
        na = norm_key(alias)
        if sid and na and len(na) >= 2 and na not in AMBIGUOUS_SINGLE_WORDS:
            db.execute(
                'INSERT OR IGNORE INTO skill_aliases (skill_id, alias, normalized_alias, case_sensitive, source) VALUES (?, ?, ?, 0, ?)',
                (sid, alias, na, 'onet'),
            )

    db.executemany(
        """
        INSERT INTO occupation_skills (occupation_id, skill_id, relation_type, weight, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(occupation_id, skill_id) DO UPDATE SET
            weight = MAX(occupation_skills.weight, excluded.weight)
        """,
        occ_links,
    )
    db.execute("INSERT OR REPLACE INTO taxonomy_meta (key, value) VALUES ('onet_version_imported', ?)", (version,))
    return {
        'imported': True,
        'version': version,
        'occupations': len(jobs),
        'links_processed': len(occ_links),
    }
