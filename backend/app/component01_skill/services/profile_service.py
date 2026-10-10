from .. import repository
from ..config import METHOD_VERSION
from .cv_parser import parse_cv_document
from .github_analyzer import analyze_github as analyze_github_profile
from .linkedin_evidence import analyze_linkedin
from .profile_evidence import combine_evidence
from .profile_identifier import detect_identifiers
from .skill_assessor import assess_skills
from .skill_extractor import extract_skills


def process_cv(candidate_id, filename, content, github_username=None, linkedin_username=None, analyze_github=False):
    text, links = parse_cv_document(filename, content)
    extracted, model_version, warnings = extract_skills(text)
    profiles, identifier_warnings = detect_identifiers(text, github_username, linkedin_username, links)
    warnings.extend(identifier_warnings)
    profile_records = []
    for profile in profiles:
        profile['consent_status'] = 'requested' if analyze_github and profile['platform'] == 'github' else 'not_requested'
        profile['enrichment_status'] = 'not_performed'
        if profile['platform'] == 'github' and analyze_github:
            records, status, messages = analyze_github_profile(profile)
        elif profile['platform'] == 'linkedin':
            records, status, messages = analyze_linkedin(candidate_id, profile)
        else:
            continue
        profile['enrichment_status'] = status
        profile_records.extend(records)
        warnings.extend(messages)
    skills = combine_evidence(assess_skills(extracted), profile_records)
    details = {'assessment_method': METHOD_VERSION, 'model_version': model_version, 'skills': skills, 'external_profiles': profiles, 'warnings': warnings, 'limitations': 'Estimated levels from CV evidence, not verified competency. Missing external profiles do not reduce levels.'}
    return repository.save_assessment(candidate_id, content, details)
