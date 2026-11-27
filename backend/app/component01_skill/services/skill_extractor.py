"""Dynamic database-backed skill extraction, NLP discovery, and semantic cosine matching."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
from ..config import MODEL_NAME
from ..repository import connection, ensure_taxonomy_bootstrapped
from ..taxonomy_repository import load_matchable_skills, norm_key, upsert_skill
from .category_classifier import classify_skill_category
from .cv_parser import evidence_units
from .esco_client import esco_api_enabled, lookup_and_cache_esco_skill
from .nlp_extractor import extract_nlp_candidates
from .semantic_matcher import SemanticMatcher

DATA = Path(__file__).parents[1] / 'data'
RUBRIC = json.loads((DATA / 'scoring_rubric.json').read_text(encoding='utf-8'))
MODEL_LOCK = Lock()

ACTION = re.compile(
    r'\b(?:built|developed|implemented|designed|created|deployed|automated|integrated|'
    r'maintained|optimized|tested|wrote|managed|configured|administered|monitored|'
    r'analyzed|analysed|visualized|visualised|modeled|modelled|secured|migrated|'
    r'provisioned|troubleshot|audited|trained|prototyped|researched|resolved|tuned|'
    r'prepared|conducted|executed|coordinated|audited|evaluated|treated|taught|led)\b',
    re.I,
)
NEGATIVE = re.compile(
    r'\b(?:no|not|without|never|lack(?:ing)?|want to learn|wish to learn|plan to learn|'
    r'planning to learn|interested in learning|hope to learn)\b',
    re.I,
)

# Short or ambiguous single tokens requiring explicit context or skills section.
CONTEXT_GUARDED_SKILLS = {'Go', 'R', 'C', 'React'}
# Skip profile platform names as explicit CV skills because GitHub/LinkedIn have dedicated analyzers.
EXCLUDED_CV_EXPLICIT = {'github', 'linkedin'}

_INDEX_CACHE = {}
_INDEX_LOCK = Lock()


@lru_cache(maxsize=1)
def semantic_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(
        os.getenv('SKILL_SBERT_MODEL_PATH', MODEL_NAME),
        local_files_only=True,
        trust_remote_code=False,
    )


def alias_pattern(alias: str, case_sensitive: bool = False):
    left = r'(?<![\w.])' if alias in {'JS', 'TS'} else r'(?<![\w])'
    right = r'(?![\w+#])' if alias in {'C', 'R'} else r'(?![\w])'
    flags = 0 if case_sensitive else re.I
    return re.compile(left + re.escape(alias) + right, flags)


def positive_context(text: str, position: int) -> bool:
    before = re.split(r'[.;!]|\bbut\b|\bhowever\b', text[:position], flags=re.I)[-1]
    return not NEGATIVE.search(before) and not re.match(
        r'.{0,25}\b(?:no experience|not experienced|not proficient|not familiar)\b',
        text[position:],
        re.I,
    )


def _get_taxonomy_index(db) -> dict:
    counts = db.execute('SELECT (SELECT count(*) FROM skills), (SELECT count(*) FROM skill_aliases)').fetchone()
    sbert_flag = os.getenv('SKILL_ENABLE_SBERT', 'false').lower()
    cache_key = (counts[0], counts[1], sbert_flag, id(semantic_model) if sbert_flag == 'true' else 0)

    with _INDEX_LOCK:
        cached = _INDEX_CACHE.get(cache_key)
        if cached is not None:
            return cached

    items = load_matchable_skills(db)
    by_name = {item['canonical_name']: item for item in items}
    by_norm = {item['normalized_name']: item for item in items}
    compiled = []
    for item in items:
        if not item['matchable']:
            continue
        if item['normalized_name'] in EXCLUDED_CV_EXPLICIT:
            continue
        patterns = [
            (alias, alias_pattern(alias, case_sensitive=cs))
            for alias, cs in item['aliases']
            if alias and len(alias) >= 1
        ]
        if patterns:
            compiled.append((item, patterns))

    # Build semantic index across ALL taxonomy skills (including non-explicit O*NET/ESCO concepts).
    sbert_loader = semantic_model if os.getenv('SKILL_ENABLE_SBERT', 'false').lower() == 'true' else None
    matcher = SemanticMatcher(items, sbert_loader=sbert_loader)

    bundle = {
        'items': items,
        'by_name': by_name,
        'by_norm': by_norm,
        'compiled': compiled,
        'matcher': matcher,
    }
    with _INDEX_LOCK:
        # Keep cache bounded to recent snapshots.
        if len(_INDEX_CACHE) > 8:
            _INDEX_CACHE.clear()
        _INDEX_CACHE[cache_key] = bundle
    return bundle


def canonical_skill_name(name: str) -> str | None:
    """Resolve a skill/language name against the DB taxonomy (skills & aliases)."""
    if not name or not isinstance(name, str):
        return None
    nk = norm_key(name)
    with connection() as db:
        ensure_taxonomy_bootstrapped(db)
        row = db.execute('SELECT canonical_name FROM skills WHERE normalized_name=?', (nk,)).fetchone()
        if row:
            return row['canonical_name']
        alias_row = db.execute(
            'SELECT s.canonical_name FROM skill_aliases a JOIN skills s ON s.id = a.skill_id WHERE a.normalized_alias=? LIMIT 1',
            (nk,),
        ).fetchone()
        return alias_row['canonical_name'] if alias_row else None


def get_skill_metadata(name: str) -> dict:
    """Lookup skill metadata (category, source, is_discovered, occupations) from DB."""
    if name == 'GitHub':
        return {
            'canonical_name': 'GitHub',
            'category': 'Tools and platforms',
            'source': 'github_activity_v1',
            'is_discovered': False,
            'reference_uri': None,
            'occupations': ['Software Developers', 'Cloud Engineers', 'Data Scientists'],
            'career_fields': ['IT & Computing', 'Data Science & Analytics'],
        }
    with connection() as db:
        ensure_taxonomy_bootstrapped(db)
        row = db.execute(
            'SELECT id, canonical_name, category, description, source, reference_uri, is_discovered FROM skills WHERE normalized_name=?',
            (norm_key(name),),
        ).fetchone()
        if not row:
            return {
                'canonical_name': name,
                'category': classify_skill_category(name),
                'source': 'discovered',
                'is_discovered': True,
                'reference_uri': None,
                'occupations': [],
                'career_fields': [],
            }
        occs = db.execute(
            """
            SELECT o.title, o.career_field
            FROM occupation_skills os
            JOIN occupations o ON o.id = os.occupation_id
            WHERE os.skill_id = ?
            ORDER BY os.weight DESC LIMIT 20
            """,
            (row['id'],),
        ).fetchall()
        fields = db.execute(
            """
            SELECT DISTINCT o.career_field
            FROM occupation_skills os
            JOIN occupations o ON o.id = os.occupation_id
            WHERE os.skill_id = ?
            """,
            (row['id'],),
        ).fetchall()
    return {
        'canonical_name': row['canonical_name'],
        'category': row['category'],
        'description': row['description'],
        'source': row['source'],
        'is_discovered': bool(row['is_discovered']),
        'reference_uri': row['reference_uri'],
        'occupations': [r['title'] for r in occs],
        'career_fields': sorted({r['career_field'] for r in fields}),
    }


def _passes_explicit_guard(item: dict, unit: dict, matches: list) -> bool:
    name = item['canonical_name']
    section = unit['section']
    text = unit['text']

    # Guard soft skills against vague summary prose like "good communication".
    if item['skill_type'] == 'soft' and section not in {'skills', 'certifications'}:
        # Require exact canonical multi-word skill name (e.g. "Critical Thinking") outside skills lists.
        if ' ' not in name or not re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I):
            return False

    if name in CONTEXT_GUARDED_SKILLS and section != 'skills':
        if name != 'React' and not re.search(
            r'\b(?:programming|language|code|compiler|backend|statistical|analysis|developed|built)\b',
            text,
            re.I,
        ):
            return False
        if name == 'React' and re.search(r'\breact\s+(?:to|with|quickly|calmly)\b', text, re.I):
            return False

    # O*NET-only single-word technology names outside skills/projects/experience require capitalized match.
    if item['source'] == 'onet' and item['skill_type'] == 'technology' and ' ' not in name and section not in {'skills', 'projects', 'experience'}:
        if all(m.group(0).islower() for m in matches):
            return False
    return True


def _add_evidence(skills: dict, name: str, evidence: dict):
    records = skills.setdefault(name, [])
    if not any(e['text'].casefold() == evidence['text'].casefold() for e in records):
        records.append(evidence)


def extract_skills(text: str):
    """Extract skills dynamically using DB taxonomy (ESCO+O*NET), NLP candidates, and semantic matching."""
    skills = {}
    units = evidence_units(text)
    warnings = []

    with connection() as db:
        ensure_taxonomy_bootstrapped(db)
        index = _get_taxonomy_index(db)
        matched_spans_by_unit = {}

        # 1. Explicit boundary-aware matching against DB skills & aliases (ESCO + O*NET + discovered).
        for unit in units:
            unit_key = (unit['section'], unit['start'])
            spans = matched_spans_by_unit.setdefault(unit_key, [])
            for item, patterns in index['compiled']:
                matches = [m for _alias, pattern in patterns for m in pattern.finditer(unit['text'])]
                matches = [m for m in matches if positive_context(unit['text'], m.start())]
                if not matches or not _passes_explicit_guard(item, unit, matches):
                    continue
                for m in matches:
                    spans.append(m.group(0).casefold())
                _add_evidence(
                    skills,
                    item['canonical_name'],
                    {
                        'source': 'cv_' + unit['section'],
                        'section': unit['section'],
                        'text': unit['text'],
                        'unit_start': unit['start'],
                        'match_start': min(m.start() for m in matches),
                        'match_method': 'explicit_taxonomy',
                        'taxonomy_source': item['source'],
                        'category': item['category'],
                        'is_discovered': item['is_discovered'],
                    },
                )

        # 2. Dynamic NLP candidate extraction for skills not captured by explicit matching.
        candidates = extract_nlp_candidates(units, positive_context)
        matcher: SemanticMatcher = index['matcher']
        use_esco = esco_api_enabled()

        for cand in candidates:
            phrase = cand['phrase']
            pnorm = norm_key(phrase)
            if pnorm in EXCLUDED_CV_EXPLICIT:
                continue
            unit_key = (cand['section'], cand['unit_start'])
            already_spans = matched_spans_by_unit.get(unit_key, [])
            # Skip if already captured explicitly in this same unit (exact or substring of matched alias).
            if pnorm in index['by_norm'] and index['by_norm'][pnorm]['canonical_name'] in skills:
                continue
            if any(pnorm == sp or (len(pnorm) >= 3 and pnorm in sp) for sp in already_spans):
                continue

            # 2a. Direct normalized match against full DB (including matchable=0 O*NET tools if named directly in skills/preposition).
            direct = index['by_norm'].get(pnorm)
            if direct and direct['normalized_name'] not in EXCLUDED_CV_EXPLICIT:
                _add_evidence(
                    skills,
                    direct['canonical_name'],
                    {
                        'source': 'cv_' + cand['section'],
                        'section': cand['section'],
                        'text': cand['text'],
                        'unit_start': cand['unit_start'],
                        'match_start': cand['match_start'],
                        'match_method': 'nlp_taxonomy_match',
                        'taxonomy_source': direct['source'],
                        'category': direct['category'],
                        'is_discovered': direct['is_discovered'],
                    },
                )
                continue

            # 2b. Semantic cosine similarity matching against DB taxonomy.
            matched_item, sim_score, sim_backend = matcher.match_phrase(phrase)
            if matched_item and matched_item['normalized_name'] not in EXCLUDED_CV_EXPLICIT:
                _add_evidence(
                    skills,
                    matched_item['canonical_name'],
                    {
                        'source': 'cv_' + cand['section'],
                        'section': cand['section'],
                        'text': cand['text'],
                        'unit_start': cand['unit_start'],
                        'match_start': cand['match_start'],
                        'match_method': 'semantic_similarity',
                        'semantic_similarity': sim_score,
                        'semantic_backend': sim_backend,
                        'taxonomy_source': matched_item['source'],
                        'category': matched_item['category'],
                        'is_discovered': matched_item['is_discovered'],
                    },
                )
                continue

            # 2c. Live ESCO REST API lookup & caching into SQLite (if enabled).
            if use_esco and cand['origin'] in {'structured_list', 'nlp_preposition'}:
                esco_hit = lookup_and_cache_esco_skill(db, phrase)
                if esco_hit:
                    _add_evidence(
                        skills,
                        esco_hit['canonical_name'],
                        {
                            'source': 'cv_' + cand['section'],
                            'section': cand['section'],
                            'text': cand['text'],
                            'unit_start': cand['unit_start'],
                            'match_start': cand['match_start'],
                            'match_method': 'esco_api_dynamic',
                            'taxonomy_source': 'esco',
                            'category': esco_hit['category'],
                            'is_discovered': False,
                        },
                    )
                    continue

            # 2d. Preserve newly discovered skill (not in ESCO or O*NET) instead of ignoring it!
            if cand['origin'] in {'structured_list', 'nlp_preposition'} and len(phrase) >= 2:
                category = classify_skill_category(phrase)
                upsert_skill(
                    db,
                    canonical_name=phrase,
                    category=category,
                    description=f'Dynamically discovered from CV {cand["section"]} section.',
                    source='discovered',
                    skill_type='skill',
                    is_discovered=True,
                    matchable=True,
                )
                _add_evidence(
                    skills,
                    phrase,
                    {
                        'source': 'cv_' + cand['section'],
                        'section': cand['section'],
                        'text': cand['text'],
                        'unit_start': cand['unit_start'],
                        'match_start': cand['match_start'],
                        'match_method': 'nlp_discovered',
                        'taxonomy_source': 'discovered',
                        'category': category,
                        'is_discovered': True,
                    },
                )

        # 3. Contextual semantic evidence scoring (SBERT when enabled, or cosine similarity).
        model_version = 'dynamic_nlp_taxonomy_v2'
        if os.getenv('SKILL_ENABLE_SBERT', 'false').lower() == 'true':
            try:
                with MODEL_LOCK:
                    model = semantic_model()
                    for name, records in skills.items():
                        contextual = [e for e in records if e['section'] in {'projects', 'experience'} and ACTION.search(e['text'])]
                        if not contextual:
                            continue
                        meta = index['by_norm'].get(norm_key(name))
                        desc = (meta or {}).get('description') or f'Practical application of {name}'
                        vectors = model.encode([desc] + [e['text'] for e in contextual], normalize_embeddings=True)
                        for idx, record in enumerate(contextual, 1):
                            score = float(vectors[0] @ vectors[idx])
                            record['semantic_similarity'] = round(score, 4)
                            record['semantic_supported'] = score >= RUBRIC['semantic_threshold']
                    model_version = MODEL_NAME
                    warnings.append('Semantic threshold is experimental and requires annotated CV calibration.')
            except Exception:
                warnings.append('SBERT unavailable locally; database taxonomy and cosine fallback were used.')
        else:
            # Compute lightweight cosine similarity for contextual records without loading PyTorch.
            for name, records in skills.items():
                contextual = [e for e in records if e['section'] in {'projects', 'experience'} and ACTION.search(e['text'])]
                if not contextual:
                    continue
                meta = index['by_norm'].get(norm_key(name))
                desc = (meta or {}).get('description') or name
                scores = matcher.score_texts(f'{name} {desc}', [e['text'] for e in contextual])
                for record, score in zip(contextual, scores):
                    record.setdefault('semantic_similarity', score)
            warnings.append('SBERT disabled; database taxonomy, NLP discovery, and cosine fallback were used.')

    return skills, model_version, warnings
