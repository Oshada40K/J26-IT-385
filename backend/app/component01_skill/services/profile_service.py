from .. import repository
from ..config import METHOD_VERSION
from .cv_parser import parse_cv
from .profile_identifier import detect_identifiers
from .skill_assessor import assess_skills
from .skill_extractor import extract_skills


def process_cv(candidate_id, filename, content, github_username=None, linkedin_username=None, analyze_github=False):
    text = parse_cv(filename, content)
    extracted, model_version, warnings = extract_skills(text)
    profiles, identifier_warnings = detect_identifiers(text, github_username, linkedin_username)
    warnings.extend(identifier_warnings)
    if analyze_github:
        warnings.append('GitHub enrichment is not enabled; profile ownership needs verification. CV-only assessment completed.')
    for profile in profiles:
        profile['consent_status'] = 'requested' if analyze_github and profile['platform'] == 'github' else 'not_requested'
        profile['enrichment_status'] = 'not_performed'
    details = {'assessment_method': METHOD_VERSION, 'model_version': model_version, 'skills': assess_skills(extracted), 'external_profiles': profiles, 'warnings': warnings, 'limitations': 'Estimated levels from CV evidence, not verified competency. Missing external profiles do not reduce levels.'}
    return repository.save_assessment(candidate_id, content, details)
