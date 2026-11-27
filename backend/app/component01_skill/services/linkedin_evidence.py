"""Adapter for authorized LinkedIn evidence provider or candidate-submitted LinkedIn text; no scraping.

The application may register a callable(candidate_id, canonical_profile_url).
Alternatively, candidates may supply exported LinkedIn profile text directly with consent.
"""
from .profile_identifier import normalize_identifier

_authorized_provider = None


def register_authorized_provider(provider):
    global _authorized_provider
    if provider is not None and not callable(provider):
        raise TypeError('LinkedIn provider must be callable')
    _authorized_provider = provider


def analyze_linkedin(candidate_id, profile, candidate_text: str | None = None):
    valid = normalize_identifier('linkedin', profile.get('url')) if profile else None
    if profile and not valid:
        return [], 'invalid', ['Invalid LinkedIn profile; CV-only assessment continues.']

    # Candidate-submitted authorized LinkedIn export text (no scraping).
    if isinstance(candidate_text, str) and candidate_text.strip():
        from .skill_extractor import extract_skills
        extracted, _, _ = extract_skills(candidate_text.strip()[:20000])
        records = []
        url = valid['url'] if valid else ''
        for skill_name, ev_list in extracted.items():
            for ev in ev_list:
                rec = {
                    'skill': skill_name,
                    'source': 'linkedin',
                    'section': ev.get('section', 'skills'),
                    'text': ev.get('text', ''),
                    'match_method': 'linkedin_user_provided',
                }
                if url:
                    rec['url'] = url
                records.append(rec)
        return records[:150], 'completed', []

    if not valid:
        return [], 'not_provided', []
    if _authorized_provider is None:
        return [], 'not_performed', ['LinkedIn evidence unavailable: no authorized provider is configured.']
    try:
        records = _authorized_provider(candidate_id, valid['url'])
        if not isinstance(records, list):
            raise ValueError('Invalid LinkedIn evidence')
        return records[:100], 'completed', []
    except Exception:
        return [], 'unavailable', ['Authorized LinkedIn evidence unavailable; CV-only assessment continues.']
