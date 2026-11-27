"""Orchestration service for CV, GitHub, and LinkedIn independent & combined assessments."""
from .. import repository
from ..config import METHOD_VERSION
from .category_classifier import classify_skill_category
from .cross_source_comparator import compare_sources
from .cv_parser import parse_cv_document
from .domain_detector import detect_domain
from .github_analyzer import analyze_github as analyze_github_profile
from .github_usage import assess_github_usage
from .linkedin_evidence import analyze_linkedin
from .profile_evidence import combine_evidence
from .profile_identifier import detect_identifiers
from .recommendation_engine import build_recommendations
from .skill_assessor import LEVEL_LABELS, SCORE_DISCLAIMER, assess_skills
from .skill_extractor import extract_skills, get_skill_metadata


def _independent_external_skills(records: list[dict], source_name: str, detected_domain: dict) -> list[dict]:
    """Build an independent skill profile from external source records without altering CV levels."""
    grouped = {}
    for rec in records:
        if not isinstance(rec, dict) or not rec.get('skill'):
            continue
        if rec.get('skill') == 'GitHub' and rec.get('match_method') == 'github_activity_v1':
            continue
        grouped.setdefault(rec['skill'], []).append(rec)

    items = []
    for name in sorted(grouped, key=str.casefold):
        recs = grouped[name]
        meta = get_skill_metadata(name)
        level = 2
        percentage = 38 if len(recs) == 1 else min(48, 38 + (len(recs) - 1) * 5)
        items.append({
            'name': name,
            'level': level,
            'percentage': percentage,
            'proficiency_label': LEVEL_LABELS[level],
            'score_disclaimer': SCORE_DISCLAIMER,
            'category': meta.get('category') or classify_skill_category(name),
            'taxonomy_source': meta.get('source', source_name),
            'is_discovered': bool(meta.get('is_discovered', False)),
            'occupations': meta.get('occupations', [])[:10],
            'domains': meta.get('career_fields', []),
            'relevant_to_domain': True,
            'confidence': 'low',
            'status': 'provisional',
            'reason': f'Observed in {source_name.capitalize()} profile metadata; independent source estimate.',
            'evidence': recs,
            'xai': {
                'why_identified': f'Identified independently from {source_name.capitalize()} profile evidence.',
                'match_methods': sorted({r.get('match_method', source_name) for r in recs}),
                'evidence_types': ['external_corroboration'],
                'self_reported_only': False,
                'practical_evidence_count': len(recs),
                'score_factors': [{'factor': f'{source_name.capitalize()} metadata', 'points': percentage, 'detail': f'{len(recs)} record(s) found.'}],
                'confidence': 'low',
                'evidence_limitations': ['External metadata alone cannot verify individual code authorship or mastery.'],
                'score_disclaimer': SCORE_DISCLAIMER,
            },
        })
    return items


def process_cv(candidate_id, filename, content, github_username=None, linkedin_username=None, analyze_github=False, linkedin_text=None):
    text, links = parse_cv_document(filename, content)
    extracted, model_version, warnings = extract_skills(text)
    detected_domain = detect_domain(text, extracted)

    # Independent Source 1: CV skill profile
    cv_skills = assess_skills(extracted, detected_domain=detected_domain)

    profiles, identifier_warnings = detect_identifiers(text, github_username, linkedin_username, links)
    warnings.extend(identifier_warnings)
    profile_records = []
    github_records = []
    linkedin_records = []
    github_assessments = []
    github_status = 'not_provided'
    linkedin_status = 'not_provided'

    for profile in profiles:
        profile['consent_status'] = 'requested' if analyze_github and profile['platform'] == 'github' else 'not_requested'
        profile['enrichment_status'] = 'not_performed'
        if profile['platform'] == 'github':
            records, status, messages = analyze_github_profile(profile)
            github_status = status
            github_records.extend(records)
        elif profile['platform'] == 'linkedin':
            records, status, messages = analyze_linkedin(candidate_id, profile, candidate_text=linkedin_text) if linkedin_text else analyze_linkedin(candidate_id, profile)
            linkedin_status = status
            linkedin_records.extend(records)
        else:
            continue
        profile['enrichment_status'] = status
        profile_records.extend(records)
        warnings.extend(messages)
        if profile['platform'] == 'github':
            assessed = assess_github_usage(records, detected_domain=detected_domain)
            if assessed:
                github_assessments.append(assessed)
            elif status == 'completed':
                warnings.append('Insufficient attributable GitHub activity for a proficiency estimate; no GitHub rating was added.')

    # Handle candidate-provided LinkedIn text even if no LinkedIn handle/URL was supplied.
    if isinstance(linkedin_text, str) and linkedin_text.strip() and linkedin_status == 'not_provided':
        li_recs, li_status, li_msgs = analyze_linkedin(candidate_id, None, candidate_text=linkedin_text)
        linkedin_status = li_status
        linkedin_records.extend(li_recs)
        profile_records.extend(li_recs)
        warnings.extend(li_msgs)

    # Independent Source 2 & 3: GitHub and LinkedIn profiles
    github_only_skills = _independent_external_skills(github_records, 'github', detected_domain)
    github_skill = max(github_assessments, key=lambda skill: skill['level'], default=None)
    if github_skill:
        github_only_skills = [s for s in github_only_skills if s['name'] != 'GitHub'] + [github_skill]
        github_only_skills.sort(key=lambda s: s['name'].casefold())

    linkedin_only_skills = _independent_external_skills(linkedin_records, 'linkedin', detected_domain)

    source_profiles = {
        'cv': {
            'status': 'completed',
            'skill_count': len(cv_skills),
            'skills': cv_skills,
        },
        'github': {
            'status': github_status,
            'skill_count': len(github_only_skills),
            'skills': github_only_skills,
        },
        'linkedin': {
            'status': linkedin_status,
            'skill_count': len(linkedin_only_skills),
            'skills': linkedin_only_skills,
        },
    }

    # Combined profile preserves CV-derived levels while attaching external corroboration.
    skills = combine_evidence([dict(s, evidence=list(s['evidence'])) for s in cv_skills], profile_records)
    if github_skill:
        skills = [skill for skill in skills if skill['name'] != 'GitHub'] + [github_skill]
        skills.sort(key=lambda skill: skill['name'].casefold())

    cross_source_comparison = compare_sources(source_profiles, skills)
    recommendations = build_recommendations(skills, detected_domain)

    details = {
        'assessment_method': METHOD_VERSION,
        'model_version': model_version,
        'detected_domain': detected_domain,
        'skills': skills,
        'source_profiles': source_profiles,
        'cross_source_comparison': cross_source_comparison,
        'recommendations': recommendations,
        'external_profiles': profiles,
        'warnings': warnings,
        'limitations': 'Estimated levels and percentages from available evidence, not verified competency. Missing external profiles do not reduce levels.',
    }
    return repository.save_assessment(candidate_id, content, details)
