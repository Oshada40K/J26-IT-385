"""Evidence-tiered proficiency scoring (1-5 + percentage) and XAI generator."""
import re
from .skill_extractor import ACTION, get_skill_metadata

LEVEL_LABELS = {
    1: 'Familiarity',
    2: 'Basic',
    3: 'Intermediate',
    4: 'Advanced',
    5: 'Expert (Review Required)',
}

EVIDENCE_TIER_LABELS = {
    'practical_implementation': 'Practical implementation',
    'observational': 'Observational / supervised exposure',
    'training_certification': 'Training & certification',
    'self_reported': 'Self-reported claim',
}

SCORE_DISCLAIMER = 'Estimated proficiency from CV evidence, not verified competency.'

OBSERVATIONAL_PATTERN = re.compile(
    r'\b(?:observed|observation|shadowed|assisted|under\s+supervision|under\s+the\s+supervision|'
    r'under\s+guidance|practice\s+on\s+manikins|familiarity|within\s+student\s+scope)\b',
    re.I,
)
TRAINING_PATTERN = re.compile(
    r'\b(?:training|workshop|course|coursework|certificate|certification|module|bootcamp)\b',
    re.I,
)


def classify_evidence_tier(record: dict) -> str:
    """Differentiate practical implementation, observational exposure, training/certs, and self-reported claims."""
    section = record.get('section', 'other')
    text = record.get('text', '')
    if section in {'education', 'certifications'}:
        return 'training_certification'
    if OBSERVATIONAL_PATTERN.search(text):
        return 'observational'
    if section in {'projects', 'experience'} and ACTION.search(text):
        return 'practical_implementation'
    if TRAINING_PATTERN.search(text):
        return 'training_certification'
    return 'self_reported'


def _proficiency_score(level: int, primary_tier: str, practical: list[dict], observational: list[dict],
                       training: list[dict], complex_records: list[dict], records: list[dict]) -> tuple[int, list[dict]]:
    """Compute a consistent, factorized 0-100 score aligned with evidence tiers and 1-5 levels."""
    factors = []
    has_external = any(e.get('section') == 'external' for e in records)

    if level == 1:
        score = 22
        factors.append({'factor': 'Introductory / foundational mention', 'points': 22, 'detail': 'Mentioned as basic or introductory learning.'})
    elif primary_tier == 'practical_implementation':
        base = 34
        factors.append({'factor': 'Skill presence / baseline', 'points': base, 'detail': 'Skill identified in CV.'})
        impl_pts = 24
        factors.append({
            'factor': 'Practical implementation',
            'points': impl_pts,
            'detail': f'{len(practical)} hands-on record(s) in experience, clinical rotations, internships, or projects.',
        })
        score = base + impl_pts
        if len(practical) >= 2:
            rep_pts = min(12, (len(practical) - 1) * 6)
            factors.append({'factor': 'Repeated application', 'points': rep_pts, 'detail': 'Demonstrated across multiple distinct activities.'})
            score += rep_pts
        if training:
            tr_pts = 5
            factors.append({'factor': 'Training / certification support', 'points': tr_pts, 'detail': 'Backed by formal training, education, or certification.'})
            score += tr_pts
        if complex_records:
            comp_pts = 18
            factors.append({'factor': 'Ownership & complexity', 'points': comp_pts, 'detail': 'Named with production, architectural, or leadership scope.'})
            score += comp_pts
    elif primary_tier == 'observational':
        score = 44 if len(observational) >= 2 else 42
        factors.append({'factor': 'Observational / supervised exposure', 'points': score, 'detail': 'Assisted or observed under supervision; capped below independent proficiency.'})
    elif primary_tier == 'training_certification':
        score = 40 if len(training) >= 2 else 38
        factors.append({'factor': 'Training & certification', 'points': score, 'detail': 'Supported by coursework, workshop, or certification without independent work proof.'})
    else:
        score = 34
        factors.append({'factor': 'Self-reported claim', 'points': score, 'detail': 'Listed in skills/summary without supporting practical implementation.'})

    if has_external and level >= 2:
        ext_pts = 4
        factors.append({'factor': 'External profile corroboration', 'points': ext_pts, 'detail': 'Corroborated in linked external profile metadata.'})
        score += ext_pts

    bands = {1: (10, 29), 2: (30, 49), 3: (50, 74), 4: (75, 92), 5: (93, 100)}
    low_b, high_b = bands[level]
    bounded = max(low_b, min(high_b, score))
    return bounded, factors


def assess_skills(extracted, detected_domain=None):
    primary_domain = (detected_domain or {}).get('primary_domain')
    career_field = (detected_domain or {}).get('career_field')
    primary_occ = (detected_domain or {}).get('primary_occupation')
    is_student = (detected_domain or {}).get('career_stage', {}).get('stage') == 'student_trainee'
    results = []

    for name in sorted(extracted, key=str.casefold):
        records = []
        for raw_rec in extracted[name]:
            rec = dict(raw_rec)
            rec['evidence_tier'] = classify_evidence_tier(rec)
            records.append(rec)

        practical = [e for e in records if e['evidence_tier'] == 'practical_implementation']
        observational = [e for e in records if e['evidence_tier'] == 'observational']
        training = [e for e in records if e['evidence_tier'] == 'training_certification']
        foundational = all(
            re.search(r'\b(?:basic\s+(?:knowledge|understanding|familiarity|skills?|level|exposure)|beginner|introductory|learning|introduction)\b', e['text'], re.I)
            for e in records
        )

        complex_records = [
            e for e in practical
            if not is_student
            and e['section'] == 'experience'
            and re.search(r'\b(?:owned|led|architected|directed|spearheaded|managed)\b', e['text'], re.I)
            and re.search(r'\b(?:production|enterprise|hospital|financial|organization|organisation|company-wide|regulatory)\b', e['text'], re.I)
            and re.search(r'\b(?:distributed|scalable|architecture|performance|security|compliance|audit|clinical|strategy|budget)\b', e['text'], re.I)
        ]

        if foundational and not practical and not observational:
            level = 1
            primary_tier = 'training_certification' if training else 'self_reported'
            confidence = 'low'
            reason = 'Introductory or foundational mention only.'
        elif len(practical) >= 2 and complex_records:
            level = 4
            primary_tier = 'practical_implementation'
            confidence = 'high'
            reason = 'Repeated practical implementation with ownership and complex responsibilities; review required.'
        elif practical:
            level = 3
            primary_tier = 'practical_implementation'
            confidence = 'high' if len(practical) >= 3 else 'medium'
            reason = 'Supported by practical implementation in work experience, rotations, internships, or projects.'
        elif observational:
            level = 2
            primary_tier = 'observational'
            confidence = 'low'
            reason = 'Observational or supervised exposure; independent implementation not yet evidenced.'
        elif training:
            level = 2
            primary_tier = 'training_certification'
            confidence = 'low'
            reason = 'Training or certification evidence; practical implementation not yet demonstrated.'
        else:
            level = 2
            primary_tier = 'self_reported'
            confidence = 'low'
            reason = 'Self-reported in CV without supporting practical implementation evidence.'

        meta = get_skill_metadata(name)
        category = records[0].get('category') or meta.get('category') or 'Domain-specific skills'
        is_discovered = bool(records[0].get('is_discovered', meta.get('is_discovered', False)))
        taxonomy_source = records[0].get('taxonomy_source') or meta.get('source') or 'taxonomy'
        occupations = meta.get('occupations', [])
        career_fields = meta.get('career_fields', [])

        percentage, factors = _proficiency_score(level, primary_tier, practical, observational, training, complex_records, records)
        methods = sorted({e.get('match_method', 'explicit_taxonomy') for e in records})
        sections = sorted({e.get('section', 'other') for e in records})
        evidence_types = sorted({e['evidence_tier'] for e in records})

        if 'nlp_discovered' in methods:
            why = f"Identified dynamically via NLP extraction as a newly discovered skill in {', '.join(sections)}."
        elif 'esco_api_dynamic' in methods:
            why = f"Matched dynamically against the official ESCO taxonomy from {', '.join(sections)}."
        elif 'semantic_similarity' in methods:
            sims = [e.get('semantic_similarity') for e in records if isinstance(e.get('semantic_similarity'), (int, float))]
            best_sim = max(sims) if sims else None
            why = f"Matched semantically (cosine similarity {best_sim:.2f}) to reference taxonomy from {', '.join(sections)}." if best_sim is not None else f"Matched semantically from {', '.join(sections)}."
        else:
            why = f"Identified against the {taxonomy_source.upper()} reference taxonomy in {', '.join(sections)}."

        limitations = []
        if primary_tier != 'practical_implementation':
            limitations.append(f"No independent practical implementation evidence found ({EVIDENCE_TIER_LABELS[primary_tier].lower()} only).")
        if confidence == 'low':
            limitations.append('Low evidence confidence; verify through portfolio, practical assessment, or supervisor feedback.')
        if level < 5:
            limitations.append('Level 5 (Expert) requires independent human review and is never assigned automatically.')

        xai = {
            'why_identified': why,
            'match_methods': methods,
            'evidence_types': evidence_types,
            'primary_evidence_tier': primary_tier,
            'primary_evidence_label': EVIDENCE_TIER_LABELS[primary_tier],
            'self_reported_only': primary_tier == 'self_reported',
            'practical_evidence_count': len(practical),
            'score_factors': factors,
            'confidence': confidence,
            'evidence_limitations': limitations,
            'score_disclaimer': SCORE_DISCLAIMER,
        }

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
            'evidence_tier': primary_tier,
            'reason': reason,
            'evidence': records,
            'xai': xai,
        })
    return results
