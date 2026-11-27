"""Official ESCO REST API client and SQLite persistence adapter."""
from functools import lru_cache
import os
import re
import httpx
from ..taxonomy_repository import link_occupation_skill, norm_key, upsert_occupation, upsert_skill
from .category_classifier import classify_skill_category

ESCO_API_BASE = 'https://ec.europa.eu/esco/api'
ALLOWED_ESCO_URI = re.compile(r'^http://data\.europa\.eu/esco/(?:skill|occupation)/[A-Za-z0-9-]+$')

DEFAULT_ESCO_OCCUPATION_SEEDS = (
    'software developer',
    'data analyst',
    'financial analyst',
    'registered nurse',
    'marketing manager',
    'secondary school teacher',
    'civil engineer',
    'graphic designer',
    'cybersecurity specialist',
    'human resources officer',
    'project manager',
    'accountant',
)


def esco_api_enabled() -> bool:
    return os.getenv('SKILL_ENABLE_ESCO_API', 'true').lower() == 'true'


def _clean_esco_text(value) -> str:
    if isinstance(value, dict):
        en = value.get('en')
        if isinstance(en, dict):
            return str(en.get('literal', '')).strip()
        if isinstance(en, str):
            return en.strip()
    if isinstance(value, str):
        return value.strip()
    return ''


def _clean_esco_aliases(value) -> list[str]:
    if isinstance(value, dict):
        en = value.get('en')
        if isinstance(en, list):
            return [str(v).strip() for v in en if isinstance(v, str) and 2 <= len(v.strip()) <= 80][:15]
    if isinstance(value, list):
        return [str(v).strip() for v in value if isinstance(v, str) and 2 <= len(v.strip()) <= 80][:15]
    return []


@lru_cache(maxsize=256)
def _fetch_esco_search(query: str, entity_type: str, limit: int) -> tuple[dict, ...]:
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        resp = client.get(
            f'{ESCO_API_BASE}/search',
            params={'text': query, 'type': entity_type, 'language': 'en', 'limit': limit, 'full': 'true'},
        )
        resp.raise_for_status()
        payload = resp.json()
    results = ((payload.get('_embedded') or {}).get('results')) or []
    return tuple(results[:limit])


@lru_cache(maxsize=128)
def _fetch_esco_resource(uri: str, kind: str) -> dict:
    if not ALLOWED_ESCO_URI.match(uri or ''):
        raise ValueError('Invalid ESCO resource URI')
    with httpx.Client(timeout=6, follow_redirects=False, trust_env=False) as client:
        resp = client.get(
            f'{ESCO_API_BASE}/resource/{kind}',
            params={'uri': uri, 'language': 'en'},
        )
        resp.raise_for_status()
        return resp.json()


def lookup_and_cache_esco_skill(db, phrase: str, limit: int = 3) -> dict | None:
    """Query ESCO API for an unknown phrase and persist matching skill + aliases into SQLite."""
    cleaned = re.sub(r'\s+', ' ', (phrase or '').strip())
    if not cleaned or len(cleaned) < 2 or len(cleaned) > 80 or not esco_api_enabled():
        return None
    try:
        results = _fetch_esco_search(cleaned, 'skill', limit)
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None

    target_norm = norm_key(cleaned)
    for item in results:
        title = (item.get('title') or '').strip()
        uri = item.get('uri', '')
        aliases = _clean_esco_aliases(item.get('alternativeLabel'))
        desc = _clean_esco_text(item.get('description'))
        if not title or not ALLOWED_ESCO_URI.match(uri):
            continue
        # Require exact title/alias match or strong token overlap so unrelated ESCO hits aren't forced.
        candidate_forms = [title, *aliases]
        matched_exact = any(norm_key(form) == target_norm for form in candidate_forms)
        q_tokens = set(re.findall(r'[a-z0-9]+', target_norm))
        t_tokens = set(re.findall(r'[a-z0-9]+', norm_key(title)))
        overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens | t_tokens))
        if not matched_exact and overlap < 0.65:
            continue

        skill_type_uri = ''
        links = item.get('_links') or {}
        if isinstance(links.get('hasSkillType'), list) and links['hasSkillType']:
            skill_type_uri = links['hasSkillType'][0].get('uri', '')
        stype = 'knowledge' if 'knowledge' in skill_type_uri else 'skill'
        category = classify_skill_category(title, desc, skill_type=stype)
        sid = upsert_skill(
            db,
            canonical_name=title,
            category=category,
            description=desc,
            source='esco',
            reference_uri=uri,
            skill_type=stype,
            is_discovered=False,
            matchable=True,
            aliases=[*aliases, cleaned] if matched_exact else aliases,
        )
        return {
            'id': sid,
            'canonical_name': title,
            'category': category,
            'description': desc,
            'source': 'esco',
            'reference_uri': uri,
            'aliases': aliases,
        }
    return None


def sync_esco_occupation(db, query: str, max_skills: int = 25) -> dict | None:
    """Fetch an ESCO occupation and its essential/optional skills into SQLite."""
    cleaned = re.sub(r'\s+', ' ', (query or '').strip())
    if not cleaned or not esco_api_enabled():
        return None
    try:
        results = _fetch_esco_search(cleaned, 'occupation', 1)
        if not results:
            return None
        occ_summary = results[0]
        uri = occ_summary.get('uri', '')
        if not ALLOWED_ESCO_URI.match(uri):
            return None
        detail = _fetch_esco_resource(uri, 'occupation')
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None

    title = (detail.get('title') or occ_summary.get('title') or '').strip()
    if not title:
        return None
    code = str(detail.get('code') or occ_summary.get('code') or '')
    desc = _clean_esco_text(detail.get('description'))
    career_field = infer_esco_career_field(code, title, desc)

    occ_id = upsert_occupation(
        db,
        code=code,
        title=title.title() if title.islower() else title,
        source='esco',
        career_field=career_field,
        description=desc,
        reference_uri=uri,
    )

    links = detail.get('_links') or {}
    imported_skills = 0
    for rel_key, rel_type, weight in (
        ('hasEssentialSkill', 'essential', 1.5),
        ('hasOptionalSkill', 'optional', 0.9),
    ):
        for sk in (links.get(rel_key) or [])[:max_skills]:
            sk_title = (sk.get('title') or '').strip()
            sk_uri = sk.get('uri', '')
            if not sk_title:
                continue
            sk_type = 'knowledge' if 'knowledge' in str(sk.get('skillType', '')) else 'skill'
            cat = classify_skill_category(sk_title, skill_type=sk_type)
            sid = upsert_skill(
                db,
                canonical_name=sk_title,
                category=cat,
                description=f'ESCO {rel_type} {sk_type} for {title}',
                source='esco',
                reference_uri=sk_uri if ALLOWED_ESCO_URI.match(sk_uri) else None,
                skill_type=sk_type,
                is_discovered=False,
                matchable=True,
            )
            link_occupation_skill(db, occupation_id=occ_id, skill_id=sid, relation_type=rel_type, weight=weight, source='esco')
            imported_skills += 1

    return {'occupation_id': occ_id, 'title': title, 'code': code, 'career_field': career_field, 'skills_linked': imported_skills, 'uri': uri}


def infer_esco_career_field(isco_code: str, title: str, description: str = '') -> str:
    text = f'{title} {description}'.casefold()
    if any(k in text for k in ('software', 'developer', 'cybersecurity', 'network', 'cloud', 'database', 'web', 'it ')):
        return 'IT & Computing'
    if any(k in text for k in ('data analyst', 'data scientist', 'machine learning', 'artificial intelligence', 'statistic')):
        return 'Data Science & Analytics'
    if any(k in text for k in ('nurse', 'medical', 'clinical', 'doctor', 'pharmac', 'health', 'patient', 'therap')):
        return 'Healthcare'
    if any(k in text for k in ('financ', 'account', 'audit', 'tax', 'banking', 'investment', 'budget')):
        return 'Finance & Accounting'
    if any(k in text for k in ('teacher', 'lecturer', 'education', 'curriculum', 'professor', 'tutor', 'instructor')):
        return 'Education & Training'
    if any(k in text for k in ('marketing', 'advertising', 'seo', 'brand', 'sales', 'public relations')):
        return 'Marketing & Sales'
    if any(k in text for k in ('designer', 'ux', 'ui', 'graphic', 'architect', 'multimedia', 'creative')):
        return 'Design, Arts & Media'
    if any(k in text for k in ('engineer', 'mechanical', 'civil', 'electrical', 'manufacturing', 'structural')):
        return 'Engineering & Architecture'
    if any(k in text for k in ('human resources', 'project manager', 'business', 'operations', 'management', 'executive')):
        return 'Business & Management'
    if any(k in text for k in ('legal', 'lawyer', 'attorney', 'compliance', 'paralegal')):
        return 'Legal & Compliance'
    return 'Other Professional Fields'
