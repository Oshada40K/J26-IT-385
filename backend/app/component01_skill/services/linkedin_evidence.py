"""Adapter for an application-authorized LinkedIn evidence provider; no scraping.

The application may register a callable(candidate_id, canonical_profile_url).
It must enforce candidate-specific authorization and return evidence dictionaries
with skill, source, section, text, and optional url. No provider is installed here.
"""
from .profile_identifier import normalize_identifier

_authorized_provider = None


def register_authorized_provider(provider):
    global _authorized_provider
    if provider is not None and not callable(provider):
        raise TypeError('LinkedIn provider must be callable')
    _authorized_provider = provider


def analyze_linkedin(candidate_id, profile):
    valid = normalize_identifier('linkedin', profile.get('url'))
    if not valid:
        return [], 'invalid', ['Invalid LinkedIn profile; CV-only assessment continues.']
    if _authorized_provider is None:
        return [], 'not_performed', ['LinkedIn evidence unavailable: no authorized provider is configured.']
    try:
        records = _authorized_provider(candidate_id, valid['url'])
        if not isinstance(records, list):
            raise ValueError('Invalid LinkedIn evidence')
        return records[:100], 'completed', []
    except Exception:
        return [], 'unavailable', ['Authorized LinkedIn evidence unavailable; CV-only assessment continues.']
