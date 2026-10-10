"""Public GitHub metadata supports CV claims; it does not prove authorship."""
from functools import lru_cache
import re
import time
import httpx
from .profile_identifier import normalize_identifier
from .skill_extractor import TAXONOMY


@lru_cache(maxsize=128)
def _public_metadata(handle, cache_window):
    # Fixed API origin, bounded requests, no redirects or user-controlled hosts.
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False,
                      headers={'Accept': 'application/vnd.github+json'}) as client:
        user = client.get(f'https://api.github.com/users/{handle}')
        user.raise_for_status()
        data = user.json()
        if data.get('type') != 'User' or data.get('login', '').casefold() != handle.casefold():
            raise ValueError('Not a personal profile')
        response = client.get(f'https://api.github.com/users/{handle}/repos',
                              params={'per_page': 30, 'sort': 'updated', 'type': 'owner'})
        response.raise_for_status()
        repos = response.json()
        if not isinstance(repos, list):
            raise ValueError('Invalid repository response')
    evidence = []
    for repo in repos[:30]:
        if repo.get('fork') or repo.get('archived') or repo.get('owner', {}).get('login', '').casefold() != handle.casefold():
            continue
        language = repo.get('language')
        name = repo.get('name', '')
        if language not in TAXONOMY or not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name):
            continue
        evidence.append({'skill': language, 'source': 'github', 'section': 'external',
                         'text': f'Public repository {name} reports {language} as its primary language; contribution and proficiency are unverified.',
                         'url': f'https://github.com/{handle}/{name}', 'match_method': 'repository_metadata'})
        evidence[-1]['project_name'] = name
    return evidence


def analyze_github(profile):
    valid = normalize_identifier('github', profile.get('url'))
    if not valid:
        return [], 'invalid', ['Invalid GitHub profile; CV-only assessment continues.']
    try:
        evidence = _public_metadata(valid['handle'], int(time.time() // 300))
        return [dict(record) for record in evidence], 'completed', ['GitHub metadata supports CV claims only; candidate ownership and contributions are unverified.']
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        return [], 'unavailable', ['GitHub profile is inaccessible, rate-limited, or invalid; CV-only assessment continues.']
