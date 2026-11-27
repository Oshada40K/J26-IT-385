"""Transparent 5-level + percentage proficiency estimation and XAI explanation generator."""
import re
from .skill_extractor import ACTION, get_skill_metadata

LEVEL_LABELS = {
    1: 'Familiarity',
    2: 'Basic',
    3: 'Intermediate',
    4: 'Advanced',
    5: 'Expert (Review Required)',
}

SCORE_DISCLAIMER = 'Estimated proficiency from available evidence, not verified ability.'


def _proficiency_percentage(level: int, records: list[dict], implemented: list[dict],
                            foundational: bool, complex_records: list[dict]) -> tuple[int, list[dict]]:
    """Compute a deterministic, factorized 0-100 estimated proficiency score with XAI factors."""
    factors = []
    sections = {e.get('section', 'other') for e in records}
    has_skills_decl = 'skills' in sections
    has_edu_cert = bool(sections & {'education', 'certifications'})
    has_external = any(e.get('section') == 'external' for e in records)

    if foundational:
        score = 22
        factors.append({'factor': 'Introductory / learning context', 'points': 22, 'detail': 'Mentioned in introductory or learning context.'})
    else:
        score = 34 if has_skills_decl else 28
        factors.append({
            'factor': 'Skill presence / claim',
            'points': score,
            'detail': 'Explicitly listed in Skills section.' if has_skills_decl else 'Referenced in CV text.',
        })

    if implemented:
        impl_points = 26
        factors.append({
            'factor': 'Practical implementation evidence',
            'points': impl_points,
            'detail': f'{len(implemented)} concrete project/experience implementation record(s) with action verbs.',
        })
        score += impl_points

        if len(implemented) >= 2:
            corrob_points = min(14, (len(implemented) - 1) * 7)
            factors.append({
                'factor': 'Repeated practical application',
                'points': corrob_points,
                'detail': 'Demonstrated across multiple distinct projects or work responsibilities.',
            })
            score += corrob_points

    if has_edu_cert and not foundational:
        edu_points = 6
        factors.append({
            'factor': 'Supporting education / certification',
            'points': edu_points,
            'detail': 'Corroborated by formal education or certifications.',
        })
        score += edu_points

    if complex_records:
        comp_points = 18
        factors.append({
            'factor': 'Production ownership & complexity',
            'points': comp_points,
            'detail': 'Skill named alongside architecture, leadership, production, or scale responsibilities.',
        })
        score += comp_points

    if has_external:
        ext_points = 4
        factors.append({
            'factor': 'External source corroboration',
            'points': ext_points,
            'detail': 'Supporting metadata found in external profile (capped to avoid inflating CV level).',
        })
        score += ext_points

    # Keep percentage strictly aligned with the 1-5 ordinal band.
    bands = {1: (10, 29), 2: (30, 49), 3: (50, 74), 4: (75, 92), 5: (93, 100)}
    low_b, high_b = bands[level]
    bounded = max(low_b, min(high_b, score))
    return bounded, factors


def _build_xai(name: str, level: int, percentage: int, confidence: str, records: list[dict],
               implemented: list[dict], factors: list[dict], meta: dict) -> dict:
    methods = sorted({e.get('match_method', 'explicit_taxonomy') for e in records})
    sections = sorted({e.get('section', 'other') for e in records})
    self_reported_only = not implemented and any(s in {'skills', 'other', 'summary'} for s in sections)
    evidence_types = []
    if 'skills' in sections:
        evidence_types.append('self_reported')
    if implemented:
        evidence_types.append('practical_evidence')
    if set(sections) & {'education', 'certifications'}:
        evidence_types.append('foundational_learning')
    if 'external' in sections:
        evidence_types.append('external_corroboration')
    if not evidence_types:
        evidence_types.append('self_reported')

    if 'nlp_discovered' in methods:
        why = f"Identified dynamically via NLP extraction as a newly discovered skill in {', '.join(sections)}."
    elif 'esco_api_dynamic' in methods:
        why = f"Matched dynamically against the official ESCO taxonomy from {', '.join(sections)}."
    elif 'semantic_similarity' in methods:
        sims = [e.get('semantic_similarity') for e in records if isinstance(e.get('semantic_similarity'), (int, float))]
        best_sim = max(sims) if sims else None
        why = f"Matched semantically (cosine similarity {best_sim:.2f}) to reference taxonomy from {', '.join(sections)}." if best_sim is not None else f"Matched semantically from {', '.join(sections)}."
    else:
        why = f"Identified explicitly against the {meta.get('source', 'taxonomy').upper()} reference taxonomy in {', '.join(sections)}."

    limitations = []
    if self_reported_only:
        limitations.append('Only self-reported presence was found; no project or work implementation evidence yet.')
    if confidence == 'low':
        limitations.append('Low evidence confidence; verify through technical screening or portfolio review.')
    if level < 5:
        limitations.append('Level 5 (Expert) requires independent human/expert review and is never assigned automatically.')

    return {
        'why_identified': why,
        'match_methods': methods,
        'evidence_types': evidence_types,
        'self_reported_only': self_reported_only,
        'practical_evidence_count': len(implemented),
        'score_factors': factors,
        'confidence': confidence,
        'evidence_limitations': limitations,
        'score_disclaimer': SCORE_DISCLAIMER,
    }


def assess_skills(extracted, detected_domain=None):
    primary_domain = (detected_domain or {}).get('primary_domain')
    career_field = (detected_domain or {}).get('career_field')
    primary_occ = (detected_domain or {}).get('primary_occupation')
    results = []

    for name in sorted(extracted, key=str.casefold):
        records = extracted[name]
        implemented = [e for e in records if e['section'] in {'projects', 'experience'} and ACTION.search(e['text'])]
        foundational = all(re.search(r'\b(?:basic|beginner|introductory|learning|introduction)\b', e['text'], re.I) for e in records)

        level = 1 if foundational else 2
        reason = 'Introductory evidence.' if foundational else 'Self-reported presence; insufficient implementation evidence.'
        confidence = 'low'

        if implemented:
            level = 3
            confidence = 'medium'
            reason = 'Named skill accompanies concrete implementation in project/work evidence.'

        complex_records = [
            e for e in implemented
            if e['section'] == 'experience'
            and re.search(r'\b(?:owned|led|architected|directed|spearheaded|managed)\b', e['text'], re.I)
            and re.search(r'\b(?:production|enterprise|hospital|financial|organization|organisation|company-wide|regulatory)\b', e['text'], re.I)
            and re.search(r'\b(?:distributed|scalable|architecture|performance|security|compliance|audit|clinical|strategy|budget)\b', e['text'], re.I)
        ]
        if len(implemented) >= 2 and complex_records:
            level = 4
            confidence = 'high'
            reason = 'Repeated implementation and explicit ownership with complex responsibilities; review required.'
        elif len(implemented) >= 3:
            confidence = 'high'

        meta = get_skill_metadata(name)
        category = records[0].get('category') or meta.get('category') or 'Domain-specific skills'
        is_discovered = bool(records[0].get('is_discovered', meta.get('is_discovered', False)))
        taxonomy_source = records[0].get('taxonomy_source') or meta.get('source') or 'taxonomy'
        occupations = meta.get('occupations', [])
        career_fields = meta.get('career_fields', [])

        percentage, factors = _proficiency_percentage(level, records, implemented, foundational, complex_records)
        xai = _build_xai(name, level, percentage, confidence, records, implemented, factors, meta)

        # Relevant if domain is undetermined, newly discovered, or matches occupation/career field.
        if not primary_domain and not primary_occ:
            relevant = True
        elif is_discovered:
            relevant = True
        else:
            relevant = bool(
                (primary_domain and primary_domain in career_fields)
                or (career_field and career_field in career_fields)
                or (primary_occ and primary_occ in occupations)
                or (primary_domain and any(primary_domain.casefold() in f.casefold() for f in career_fields))
            )

        results.append({
            'name': name,
            'level': level,
            'percentage': percentage,
            'proficiency_label': LEVEL_LABELS[level],
            'score_disclaimer': SCORE_DISCLAIMER,
            'category': category,
            'taxonomy_source': taxonomy_source,
            'is_discovered': is_discovered,
            'occupations': occupations[:10],
            'domains': career_fields,
            'relevant_to_domain': relevant,
            'confidence': confidence,
            'status': 'needs_review' if level == 4 else 'provisional',
            'reason': reason,
            'evidence': records,
            'xai': xai,
        })
    return results
