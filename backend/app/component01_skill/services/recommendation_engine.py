"""Evidence-gap and occupation-gap recommendation generator tailored to career stage and field."""
from ..repository import connection, ensure_taxonomy_bootstrapped
from ..taxonomy_repository import norm_key


def _action_for_tier(skill_name: str, tier: str, stage: str, field: str) -> str:
    is_health = 'health' in (field or '').casefold()
    is_it = any(k in (field or '').casefold() for k in ('it', 'software', 'data', 'cloud', 'cyber', 'ai'))

    if tier == 'observational':
        if is_health or stage == 'student_trainee':
            return f'Document supervised hands-on practice or clinical case logs applying {skill_name} beyond observation.'
        return f'Transition {skill_name} from assisted/observational exposure to an independently executed task or project.'
    if tier == 'training_certification':
        if is_it:
            return f'Apply {skill_name} in a concrete project or code repository to back up training/coursework.'
        return f'Add a practical project, placement, or case example demonstrating {skill_name} in action.'
    # self_reported
    if is_health:
        return f'Link {skill_name} to specific clinical rotations, patient-care tasks, or community health activities.'
    if is_it:
        return f'Provide concrete project, internship, or repository evidence showing how you built or tested with {skill_name}.'
    return f'Add specific work, internship, or project examples demonstrating how you applied {skill_name}.'


def build_recommendations(skills: list[dict], detected_domain: dict) -> dict:
    """Generate actionable, non-generic recommendations from actual evidence and occupation gaps."""
    stage = (detected_domain.get('career_stage') or {}).get('stage', 'mid_level')
    stage_label = (detected_domain.get('career_stage') or {}).get('label', 'Practitioner')
    field = detected_domain.get('career_field') or detected_domain.get('primary_domain') or 'General'
    related_occs = detected_domain.get('related_occupations') or []

    # 1. Evidence-gap recommendations for skills lacking independent practical implementation.
    weak_or_unproven = [
        s for s in skills
        if s.get('evidence_tier') != 'practical_implementation' or s.get('level', 0) <= 2
    ]
    weak_or_unproven.sort(key=lambda s: (s.get('percentage', 0), s.get('name', '').casefold()))

    evidence_recommendations = [
        {
            'skill': s['name'],
            'current_tier': s.get('evidence_tier', 'self_reported'),
            'current_percentage': s.get('percentage', s['level'] * 20),
            'recommendation': _action_for_tier(s['name'], s.get('evidence_tier', 'self_reported'), stage, field),
        }
        for s in weak_or_unproven[:5]
    ]

    # 2. Occupation skill-gap recommendations from DB occupation_skills (essential / in_demand).
    missing_occupation_skills = []
    if related_occs:
        top_occ_title = related_occs[0].get('title')
        present_norms = {norm_key(s['name']) for s in skills}
        if top_occ_title:
            with connection() as db:
                ensure_taxonomy_bootstrapped(db)
                rows = db.execute(
                    """
                    SELECT s.canonical_name, s.category, os.relation_type, os.weight
                    FROM occupation_skills os
                    JOIN occupations o ON o.id = os.occupation_id
                    JOIN skills s ON s.id = os.skill_id
                    WHERE o.normalized_title = ? AND os.relation_type IN ('essential', 'in_demand')
                    ORDER BY os.weight DESC, s.canonical_name ASC
                    LIMIT 25
                    """,
                    (norm_key(top_occ_title),),
                ).fetchall()
                for row in rows:
                    if norm_key(row['canonical_name']) not in present_norms:
                        missing_occupation_skills.append({
                            'skill': row['canonical_name'],
                            'category': row['category'],
                            'relation_type': row['relation_type'],
                            'target_occupation': top_occ_title,
                        })
                    if len(missing_occupation_skills) >= 5:
                        break

    return {
        'career_stage': stage_label,
        'career_field': field,
        'evidence_gaps': evidence_recommendations,
        'missing_occupation_skills': missing_occupation_skills,
    }
