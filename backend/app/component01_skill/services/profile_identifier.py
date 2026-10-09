"""Detect labeled handles only; no scraping and no ownership assumptions."""
import re
from urllib.parse import urlparse


def normalize_identifier(platform, value):
    value = (value or '').strip().rstrip('/')
    if not value:
        return None
    if '://' in value or value.startswith(('github.com/', 'www.github.com/', 'linkedin.com/', 'www.linkedin.com/')):
        url = urlparse(value if '://' in value else 'https://' + value)
        if url.hostname not in ({'github.com', 'www.github.com'} if platform == 'github' else {'linkedin.com', 'www.linkedin.com'}):
            return None
        pieces = url.path.strip('/').split('/')
        if platform == 'linkedin':
            if len(pieces) != 2 or pieces[0] != 'in':
                return None
            value = pieces[1]
        else:
            if len(pieces) != 1:
                return None
            value = pieces[0]
    pattern = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?' if platform == 'github' else r'[A-Za-z0-9][A-Za-z0-9_-]{1,99}'
    if not re.fullmatch(pattern, value) or (platform == 'github' and '--' in value):
        return None
    return {'platform': platform, 'handle': value, 'url': f'https://github.com/{value}' if platform == 'github' else f'https://www.linkedin.com/in/{value}', 'ownership_verified': False}


def detect_identifiers(text, github_username=None, linkedin_username=None):
    results = []
    warnings = []
    for platform, supplied in [('github', github_username), ('linkedin', linkedin_username)]:
        match = re.search(rf'\b{platform}\s*:\s*(\S+)', text, re.I)
        value = supplied or (match.group(1) if match else None)
        if not value:
            match = re.search(r'https?://(?:www\.)?' + ('github.com/[A-Za-z0-9-]+' if platform == 'github' else 'linkedin.com/in/[A-Za-z0-9_-]+'), text, re.I)
            value = match.group(0) if match else None
        if value:
            result = normalize_identifier(platform, value)
            if result:
                results.append(result)
            else:
                warnings.append(f'Invalid {platform} identifier; CV-only assessment continues.')
    return results, warnings
