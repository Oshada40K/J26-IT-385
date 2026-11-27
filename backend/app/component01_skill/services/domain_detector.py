"""Flexible database-backed occupation & career-field detection across all professions."""
import json
import math
import re
from pathlib import Path
from ..repository import connection, ensure_taxonomy_bootstrapped
from ..taxonomy_repository import norm_key
from .cv_parser import evidence_units
from .skill_extractor import positive_context

DATA = Path(__file__).parents[1] / 'data'
DOMAINS = json.loads((DATA / 'domains.json').read_text(encoding='utf-8')) if (DATA / 'domains.json').exists() else {}
SUPPORTED_DOMAINS = list(DOMAINS.keys())


def _phrase_pattern(phrase):
    is_short_acronym = len(phrase) <= 5 and phrase.isupper()
    flags = 0 if is_short_acronym else re.I
    return re.compile(r'(?<![\w])' + re.escape(phrase) + r'(?![\w])', flags)


ROLE_PATTERNS = {
    domain: [(kw, _phrase_pattern(kw)) for kw in meta.get('role_keywords', [])]
    for domain, meta in DOMAINS.items()
}
CONTEXT_PATTERNS = {
    domain: [(kw, _phrase_pattern(kw)) for kw in meta.get('context_keywords', [])]
    for domain, meta in DOMAINS.items()
}

UNKNOWN_ROLE_HINT = re.compile(
    r'^(?:junior|senior|lead|associate|assistant|certified|registered|principal|staff)?\s*'
    r'([A-Z][A-Za-z/&\- ]{2,45}(?:Engineer|Developer|Analyst|Scientist|Designer|Manager|Nurse|Doctor|'
    r'Accountant|Auditor|Teacher|Lecturer|Specialist|Technician|Administrator|Consultant|Architect|'
    r'Coordinator|Director|Officer|Therapist|Pharmacist|Lawyer|Researcher))$'
)


def _detect_it_subdomain(units: list[dict], extracted: dict, skill_meta: dict) -> dict | None:
    """Preserve fine-grained 10-domain IT classification when CV strongly aligns with an IT discipline."""
    if not DOMAINS:
        return None
    raw_scores = {domain: 0.0 for domain in SUPPORTED_DOMAINS}
    matched_skills = {domain: [] for domain in SUPPORTED_DOMAINS}
    role_hits = {domain: [] for domain in SUPPORTED_DOMAINS}
    context_hits = {domain: [] for domain in SUPPORTED_DOMAINS}

    for unit in units:
        section = unit.get('section', 'other')
        unit_text = unit.get('text', '')
        role_weight = 4.0 if section in {'other', 'summary', 'experience'} else 2.5
        ctx_weight = 1.5 if section in {'projects', 'experience', 'summary'} else 1.0
        for domain in SUPPORTED_DOMAINS:
            for kw, pattern in ROLE_PATTERNS[domain]:
                match = pattern.search(unit_text)
                if match and positive_context(unit_text, match.start()) and kw not in role_hits[domain]:
                    role_hits[domain].append(kw)
                    raw_scores[domain] += role_weight
            for kw, pattern in CONTEXT_PATTERNS[domain]:
                match = pattern.search(unit_text)
                if match and positive_context(unit_text, match.start()) and kw not in context_hits[domain]:
                    context_hits[domain].append(kw)
                    if len(context_hits[domain]) <= 8:
                        raw_scores[domain] += ctx_weight

    for skill_name, records in extracted.items():
        occ_fields = skill_meta.get(norm_key(skill_name), {}).get('seed_domains', [])
        if not occ_fields:
            continue
        specificity = 1.0 / (len(occ_fields) ** 0.65)
        has_practical = any(r.get('section') in {'projects', 'experience'} for r in records)
        contribution = round(2.2 * specificity * (1.5 if has_practical else 1.0), 4)
        for domain in occ_fields:
            if domain in raw_scores:
                raw_scores[domain] += contribution
                if skill_name not in matched_skills[domain]:
                    matched_skills[domain].append(skill_name)

    total = sum(raw_scores.values())
    ranked = sorted(SUPPORTED_DOMAINS, key=lambda d: (-raw_scores[d], -len(role_hits[d]), -len(matched_skills[d]), d))
    top = ranked[0] if ranked else None
    if not top or raw_scores[top] < 2.5 or (not role_hits[top] and not matched_skills[top]):
        return None
    domain_scores = [
        {
            'domain': d,
            'score': round(raw_scores[d], 2),
            'share_percent': round((raw_scores[d] / total) * 100, 1) if total > 0 else 0.0,
            'matched_skills': sorted(matched_skills[d], key=str.casefold),
            'signals': (
                (['Role/title signals: ' + ', '.join(role_hits[d][:3])] if role_hits[d] else [])
                + ([f'{len(matched_skills[d])} aligned skill(s)'] if matched_skills[d] else [])
                + (['Domain context: ' + ', '.join(context_hits[d][:4])] if context_hits[d] else [])
            ),
        }
        for d in ranked if raw_scores[d] > 0
    ]
    return {
        'top': top,
        'top_score': raw_scores[top],
        'domain_scores': domain_scores,
        'secondary': [e['domain'] for e in domain_scores[1:4] if e['score'] >= max(3.0, raw_scores[top] * 0.45)],
    }


def detect_domain(text: str, extracted: dict | None = None, units: list[dict] | None = None) -> dict:
    """Detect candidate occupation, career field, and multi-occupation matches from DB taxonomy.

    Handles any professional category (IT, Finance, Healthcare, Education, Engineering,
    Marketing, Design, Business, etc.) as well as unknown occupations and newly discovered skills.
    """
    extracted = extracted or {}
    units = units if units is not None else evidence_units(text)

    with connection() as db:
        ensure_taxonomy_bootstrapped(db)

        # Load occupations & degree stats from SQLite for IDF-like specificity weighting.
        occ_rows = db.execute(
            'SELECT id, code, title, normalized_title, source, career_field, description FROM occupations'
        ).fetchall()
        occ_by_id = {r['id']: dict(r) for r in occ_rows}

        skill_rows = db.execute('SELECT id, canonical_name, normalized_name FROM skills').fetchall()
        skill_id_by_norm = {r['normalized_name']: r['id'] for r in skill_rows}

        # Map extracted skills to DB occupation_skills (many-to-many).
        matched_skill_ids = {}
        seed_domains_by_norm = {}
        for sname in extracted:
            nk = norm_key(sname)
            sid = skill_id_by_norm.get(nk)
            if sid:
                matched_skill_ids[sid] = sname

        occ_scores = {}  # occ_id -> {'score': float, 'skills': list, 'title_hit': bool, 'signals': list}
        if matched_skill_ids:
            placeholders = ','.join('?' for _ in matched_skill_ids)
            links = db.execute(
                f"""
                SELECT os.occupation_id, os.skill_id, os.relation_type, os.weight,
                       (SELECT count(*) FROM occupation_skills os2 WHERE os2.skill_id = os.skill_id) AS deg
                FROM occupation_skills os
                WHERE os.skill_id IN ({placeholders})
                """,
                tuple(matched_skill_ids.keys()),
            ).fetchall()
            for link in links:
                oid = link['occupation_id']
                occ = occ_by_id.get(oid)
                if not occ:
                    continue
                sname = matched_skill_ids[link['skill_id']]
                if occ['source'] == 'taxonomy_seed' and occ['title'] in DOMAINS:
                    seed_domains_by_norm.setdefault(norm_key(sname), {}).setdefault('seed_domains', []).append(occ['title'])
                    continue
                deg = max(1, link['deg'] or 1)
                idf = 1.0 / math.log2(deg + 1.5)
                has_practical = any(r.get('section') in {'projects', 'experience'} for r in extracted.get(sname, []))
                contrib = float(link['weight'] or 1.0) * idf * (1.35 if has_practical else 1.0)
                bucket = occ_scores.setdefault(oid, {'score': 0.0, 'skills': [], 'title_hit': False, 'signals': []})
                bucket['score'] += contrib
                if sname not in bucket['skills']:
                    bucket['skills'].append(sname)

        # Title/Role matching in CV header, summary, and experience sections against ESCO/O*NET occupations.
        header_and_role_units = [u for u in units if u.get('section') in {'other', 'summary', 'experience'}]
        header_text = ' \n '.join(u.get('text', '') for u in header_and_role_units)
        header_low = header_text.casefold()
        for oid, occ in occ_by_id.items():
            if occ['source'] == 'taxonomy_seed':
                continue
            title = occ['title']
            tlow = occ['normalized_title']
            # Match base O*NET/ESCO title (strip trailing ", Except ..." / "(...)" qualifiers) and singular stem.
            base_title = re.split(r'\s*[,(]\s*', tlow, maxsplit=1)[0].strip()
            forms = []
            for candidate_form in (tlow, base_title):
                if candidate_form and len(candidate_form) >= 4:
                    forms.append(candidate_form)
                    if candidate_form.endswith('s') and len(candidate_form) > 5:
                        forms.append(candidate_form[:-1])
            found_pos = -1
            for form in dict.fromkeys(forms):
                m = re.search(r'(?<!\w)' + re.escape(form) + r'(?!\w)', header_low)
                if m and positive_context(header_text, m.start()):
                    found_pos = m.start()
                    break
            if found_pos >= 0:
                bucket = occ_scores.setdefault(oid, {'score': 0.0, 'skills': [], 'title_hit': False, 'signals': []})
                bucket['score'] += 5.0
                bucket['title_hit'] = True
                bucket['signals'].append(f'Role title match: {title}')

    # Rank flexible occupation matches.
    ranked_occs = sorted(
        occ_scores.items(),
        key=lambda kv: (-kv[1]['score'], -len(kv[1]['skills']), occ_by_id[kv[0]]['title']),
    )

    related_occupations = []
    field_scores = {}
    for oid, info in ranked_occs[:8]:
        occ = occ_by_id[oid]
        signals = list(info['signals'])
        if info['skills']:
            signals.append(f"{len(info['skills'])} aligned skill(s): {', '.join(info['skills'][:5])}")
        related_occupations.append({
            'title': occ['title'],
            'code': occ['code'],
            'career_field': occ['career_field'],
            'source': occ['source'],
            'score': round(info['score'], 2),
            'matched_skills': sorted(info['skills'], key=str.casefold),
            'signals': signals,
        })
        field_scores[occ['career_field']] = field_scores.get(occ['career_field'], 0.0) + info['score']

    # Check if an IT sub-domain (10 IT disciplines) is strongly indicated for Phase 1 compatibility.
    it_sub = _detect_it_subdomain(units, extracted, seed_domains_by_norm)

    # Extract an inferred role title from CV header/summary for unknown-occupation fallback.
    inferred_role = None
    for unit in header_and_role_units[:6]:
        for seg in re.split(r'[|\n•]', unit.get('text', '')):
            seg_clean = seg.strip()
            if UNKNOWN_ROLE_HINT.match(seg_clean) and positive_context(unit['text'], max(0, unit['text'].find(seg_clean))):
                inferred_role = seg_clean
                break
        if inferred_role:
            break

    top_occ = related_occupations[0] if related_occupations else None
    has_strong_occ = bool(top_occ and (top_occ['score'] >= 1.8 or (top_occ['matched_skills'] and top_occ['score'] >= 0.8)))

    if not has_strong_occ and not it_sub:
        return {
            'primary_domain': None,
            'primary_occupation': inferred_role,
            'career_field': 'Unknown / Emerging' if (inferred_role or extracted) else None,
            'is_unknown_occupation': bool(inferred_role or extracted),
            'confidence': 'low',
            'status': 'unknown_occupation' if (inferred_role or extracted) else 'undetermined',
            'secondary_domains': [],
            'related_occupations': related_occupations[:5],
            'supported_domains': SUPPORTED_DOMAINS,
            'domain_scores': [],
            'signals': (
                [f'Unmapped or emerging occupation profile ({inferred_role}); preserved {len(extracted)} extracted skill(s).' if inferred_role else f'Unmapped career profile; preserved {len(extracted)} extracted skill(s).']
                if (inferred_role or extracted)
                else ['Insufficient domain-specific skills or role context in CV text.']
            ),
        }

    # Decide whether primary_domain should show a specific IT discipline or the broad career field.
    top_has_role_hit = bool(ranked_occs and ranked_occs[0][1].get('title_hit'))
    top_field = (
        top_occ['career_field']
        if (top_occ and top_has_role_hit)
        else (max(field_scores.items(), key=lambda kv: kv[1])[0] if field_scores else None)
    )
    it_has_role_hit = bool(it_sub and any('Role/title signals:' in s for s in (it_sub['domain_scores'][0].get('signals') or [])))
    is_it_field = top_field in {'IT & Computing', 'Data Science & Analytics', 'Design & Media', 'Design, Arts & Media', None}
    if it_sub and (not top_occ or (it_has_role_hit and not top_has_role_hit) or (is_it_field and not top_has_role_hit) or (is_it_field and it_sub['top_score'] >= top_occ['score'])):
        primary_domain = it_sub['top']
        secondary_domains = it_sub['secondary']
        domain_scores = it_sub['domain_scores']
        signals = list(dict.fromkeys((it_sub['domain_scores'][0]['signals'] if it_sub['domain_scores'] else []) + (top_occ['signals'] if top_occ else [])))
        top_score = max(it_sub['top_score'], top_occ['score'] if top_occ else 0.0)
    else:
        primary_domain = top_field or (top_occ['career_field'] if top_occ else None)
        other_fields = [f for f, _ in sorted(field_scores.items(), key=lambda kv: -kv[1]) if f != primary_domain]
        secondary_domains = other_fields[:3]
        total_f = sum(field_scores.values()) or 1.0
        domain_scores = [
            {
                'domain': f,
                'score': round(sc, 2),
                'share_percent': round((sc / total_f) * 100, 1),
                'matched_skills': sorted({sk for ro in related_occupations if ro['career_field'] == f for sk in ro['matched_skills']}, key=str.casefold),
                'signals': [f"Matched occupation(s): {', '.join(ro['title'] for ro in related_occupations if ro['career_field'] == f)[:120]}"],
            }
            for f, sc in sorted(field_scores.items(), key=lambda kv: -kv[1])[:5]
        ]
        signals = top_occ['signals'] if top_occ else []
        top_score = top_occ['score'] if top_occ else 0.0

    confidence = 'high' if top_score >= 6.5 else ('medium' if top_score >= 2.8 else 'low')

    return {
        'primary_domain': primary_domain,
        'primary_occupation': top_occ['title'] if top_occ else inferred_role,
        'career_field': top_field or primary_domain,
        'is_unknown_occupation': False,
        'confidence': confidence,
        'status': 'detected',
        'secondary_domains': secondary_domains,
        'related_occupations': related_occupations[:5],
        'supported_domains': SUPPORTED_DOMAINS,
        'domain_scores': domain_scores[:5],
        'signals': signals,
    }


detect_occupation = detect_domain
