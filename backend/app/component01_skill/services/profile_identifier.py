"""Bounded profile discovery; untrusted links are never requested directly."""
import re
from urllib.parse import urlsplit

HOSTS = {'github': {'github.com', 'www.github.com'}, 'linkedin': {'linkedin.com', 'www.linkedin.com'}}
RESERVED = {'features', 'topics', 'collections', 'settings', 'login', 'signup', 'search', 'marketplace', 'orgs', 'organizations', 'about', 'pricing', 'explore', 'security', 'enterprise', 'sponsors', 'notifications', 'apps', 'pulls', 'issues', 'new'}


def normalize_identifier(platform, value):
    if platform not in HOSTS or not isinstance(value, str):
        return None
    value = value.strip().rstrip('.,;!)]}')
    if not value or len(value) > 2048 or re.search(r'[\s\\\x00-\x1f\x7f]', value):
        return None
    if '://' in value or re.match(r'(?:www\.)?(?:github|linkedin)\.com/', value, re.I):
        try:
            url = urlsplit(value if '://' in value else 'https://' + value)
            if url.scheme.lower() not in {'http', 'https'} or url.hostname not in HOSTS[platform] or url.username or url.password or url.port is not None:
                return None
        except ValueError:
            return None
        pieces = url.path.strip('/').split('/')
        if platform == 'linkedin':
            if len(pieces) != 2 or pieces[0].lower() != 'in':
                return None
            value = pieces[1]
        else:
            if len(pieces) != 1:
                return None
            value = pieces[0]
    value = value.removeprefix('@')
    pattern = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?' if platform == 'github' else r'[A-Za-z0-9][A-Za-z0-9_-]{1,99}'
    if not re.fullmatch(pattern, value) or (platform == 'github' and ('--' in value or value.casefold() in RESERVED)):
        return None
    return {'platform': platform, 'handle': value, 'url': f'https://github.com/{value}' if platform == 'github' else f'https://www.linkedin.com/in/{value}', 'ownership_verified': False}


def detect_identifiers(text, github_username=None, linkedin_username=None, links=()):
    results, warnings, seen = [], [], set()
    # Consume complete tokens, rather than accepting prefixes of malicious URLs.
    urls = re.findall(r'(?<![\w/@.])(?:https?://[^\s<>"\']+|(?:www\.)?(?:github|linkedin)\.com/[^\s<>"\']+)', text, re.I)
    for platform, supplied in [('github', github_username), ('linkedin', linkedin_username)]:
        label = r'git\s*hub' if platform == 'github' else r'linked\s*in'
        labeled = re.findall(rf'\b{label}(?:\s+(?:username|profile|handle))?\s*(?::|=|-)\s*([^\s<>]+)', text, re.I)
        candidates = ([supplied] if supplied else []) + labeled
        candidates += [url for url in [*urls, *links] if isinstance(url, str) and re.search(rf'{platform}\.com', url, re.I)]
        for value in candidates:
            profile = normalize_identifier(platform, value)
            if profile:
                key = (platform, profile['handle'].casefold())
                if key not in seen and len(results) < 20:
                    results.append(profile)
                    seen.add(key)
            elif f'Invalid {platform} identifier; CV-only assessment continues.' not in warnings:
                warnings.append(f'Invalid {platform} identifier; CV-only assessment continues.')
    return results, warnings
