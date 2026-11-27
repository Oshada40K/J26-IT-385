"""Cross-source skill comparison across CV, GitHub, and LinkedIn."""
from .skill_extractor import ACTION


def _has_practical_cv_evidence(evidence: list[dict]) -> bool:
    return any(
        ev.get('section') in {'projects', 'experience'} and ACTION.search(ev.get('text', ''))
        for ev in (evidence or [])
    )


def compare_sources(source_profiles: dict, combined_skills: list[dict]) -> dict:
    """Compare skills independently identified in CV, GitHub, and LinkedIn.

    Never treats missing evidence in an external source as proof that the candidate lacks a skill.
    """
    cv_map = {s['name']: s for s in (source_profiles.get('cv', {}).get('skills') or [])}
    gh_map = {s['name']: s for s in (source_profiles.get('github', {}).get('skills') or [])}
    li_map = {s['name']: s for s in (source_profiles.get('linkedin', {}).get('skills') or [])}
    combined_map = {s['name']: s for s in (combined_skills or [])}

    all_names = sorted(set(cv_map) | set(gh_map) | set(li_map), key=str.casefold)
    compared = []
    multi_source_skills = []
    single_source_skills = []
    claimed_without_practical = []

    for name in all_names:
        sources_present = []
        source_details = {}
        category = None

        for src_key, src_map in (('cv', cv_map), ('github', gh_map), ('linkedin', li_map)):
            item = src_map.get(name)
            if item:
                sources_present.append(src_key)
                category = category or item.get('category')
                if src_key == 'cv':
                    practical = _has_practical_cv_evidence(item.get('evidence', []))
                    ev_basis = 'practical' if practical else 'claimed_or_learning'
                elif src_key == 'github':
                    practical = any(
                        e.get('match_method') in {'github_activity_v1', 'repository_metadata'}
                        for e in item.get('evidence', [])
                    )
                    ev_basis = 'practical' if practical else 'metadata'
                else:
                    practical = _has_practical_cv_evidence(item.get('evidence', []))
                    ev_basis = 'practical' if practical else 'claimed'

                source_details[src_key] = {
                    'present': True,
                    'level': item.get('level'),
                    'percentage': item.get('percentage'),
                    'evidence_count': len(item.get('evidence', [])),
                    'evidence_basis': ev_basis,
                }
            else:
                source_details[src_key] = {'present': False}

        if not category and name in combined_map:
            category = combined_map[name].get('category')

        cv_practical = source_details['cv'].get('evidence_basis') == 'practical'
        gh_present = source_details['github']['present']
        li_practical = source_details['linkedin'].get('evidence_basis') == 'practical'
        has_any_practical = cv_practical or gh_present or li_practical

        if len(sources_present) >= 2 and has_any_practical:
            claim_status = 'corroborated_practical'
            note = f"Corroborated across {', '.join(s.upper() for s in sources_present)} with practical/repository evidence."
        elif len(sources_present) >= 2:
            claim_status = 'corroborated_claimed'
            note = f"Claimed across {', '.join(s.upper() for s in sources_present)}; no practical project/code evidence detected yet."
        elif sources_present == ['cv'] and cv_practical:
            claim_status = 'cv_practical_only'
            note = 'Demonstrated in CV projects/experience; not corroborated in external sources.'
        elif not sources_present == ['cv'] and sources_present in (['github'], ['linkedin']):
            claim_status = 'external_only'
            src_label = sources_present[0].upper()
            note = f'Observed in {src_label} only; not explicitly mentioned in CV.'
        else:
            claim_status = 'claimed_only'
            claimed_without_practical.append(name)
            note = f"Self-reported in {', '.join(s.upper() for s in sources_present)} without practical implementation evidence yet."

        if len(sources_present) >= 2:
            multi_source_skills.append(name)
        else:
            single_source_skills.append(name)

        compared.append({
            'name': name,
            'category': category or 'Domain-specific skills',
            'sources_present': sources_present,
            'source_count': len(sources_present),
            'multi_source': len(sources_present) >= 2,
            'single_source': len(sources_present) == 1,
            'source_details': source_details,
            'claim_vs_practice_status': claim_status,
            'discrepancy_note': note,
        })

    sources_available = {
        src: source_profiles.get(src, {}).get('status') == 'completed'
        for src in ('cv', 'github', 'linkedin')
    }

    return {
        'summary': {
            'total_compared_skills': len(compared),
            'multi_source_count': len(multi_source_skills),
            'single_source_count': len(single_source_skills),
            'claimed_vs_practical_gap_count': len(claimed_without_practical),
            'sources_available': sources_available,
            'note': 'Missing evidence in an unavailable or unprovided source is never treated as proof that the candidate lacks a skill.',
        },
        'multi_source_skills': multi_source_skills,
        'single_source_skills': single_source_skills,
        'claimed_without_practical_skills': claimed_without_practical,
        'skills': compared,
    }
