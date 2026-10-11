"""Adapt Component 1's completed CV assessment to the saved matcher contract."""
from .schemas import TechnicalAssessment, TechnicalProfile


def adapt_technical_profile(payload):
    if isinstance(payload, dict) and 'skills' in payload:
        if 'technical_skills' in payload:
            raise ValueError('Ambiguous technical profile: provide skills or technical_skills, not both')
        assessment = TechnicalAssessment.model_validate(payload)
        # Confidence describes evidence certainty, not proficiency. Preserve levels
        # and names exactly; the exported matcher handles canonical aliases.
        payload = {
            'schema_version': '1.0',
            'candidate_id': assessment.candidate_id,
            'technical_skills': [
                {'name': skill.name, 'level': skill.level}
                for skill in assessment.skills
            ],
        }
    profile = TechnicalProfile.model_validate(payload)
    # Retain the legacy evidence field when present; assessment evidence is not
    # a matcher feature and must never be converted into additional skills.
    return profile.model_dump(exclude_none=True)
