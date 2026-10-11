"""Bounded public activity sampling and conservative GitHub proficiency rubric."""
from datetime import datetime
from functools import lru_cache
import re
import time
import httpx
from .profile_identifier import normalize_identifier

AUTO_FILES = re.compile(r'(^|/)(?:vendor|node_modules|dist|build|generated)/|(?:^|/)(?:package-lock\.json|yarn\.lock|poetry\.lock|pnpm-lock\.yaml)$|(?:\.lock|\.min\.js|\.svg|\.png|\.jpg)$', re.I)
CODE = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.cs', '.rb', '.php', '.sh', '.sql'}


def meaningful_files(files):
    result = []
    for file in files:
        if not isinstance(file, dict):
            continue
        name = file.get('filename', '')
        changes = file.get('changes', 0)
        if not isinstance(name, str) or not isinstance(changes, int) or changes < 5 or AUTO_FILES.search(name):
            continue
        suffix = '.' + name.rsplit('.', 1)[-1].lower()
        if suffix in CODE or suffix in {'.md', '.rst'} or name.startswith('.github/workflows/'):
            result.append(name)
    return result


def repo_path(value):
    if not isinstance(value, str) or value.count('/') != 1:
        return None
    owner, name = value.split('/')
    if normalize_identifier('github', owner) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name) and name not in {'.', '..'}:
        return value
    return None


@lru_cache(maxsize=128)
def collect_usage(handle, cache_window):
    deadline = time.monotonic() + 25
    records, warnings, seen = [], [], set()
    requests = 0
    with httpx.Client(timeout=4, follow_redirects=False, trust_env=False,
                      headers={'Accept': 'application/vnd.github+json'}) as client:
        def get(path, params=None):
            nonlocal requests
            if requests >= 24 or time.monotonic() >= deadline:
                raise ValueError('Activity sampling limit reached')
            requests += 1
            response = client.get('https://api.github.com' + path, params=params,
                                  timeout=max(.1, min(4, deadline - time.monotonic())))
            response.raise_for_status()
            return response.json()
        try:
            repos = get(f'/users/{handle}/repos', {'per_page': 30, 'sort': 'updated', 'type': 'owner'})
            if not isinstance(repos, list):
                raise ValueError('Invalid repositories')
            eligible = [r for r in repos if isinstance(r, dict) and not r.get('fork') and not r.get('archived') and
                        (r.get('owner') or {}).get('login', '').casefold() == handle.casefold() and repo_path(r.get('full_name'))][:3]
            for repo in eligible:
                path = repo['full_name']
                commits = get(f'/repos/{path}/commits', {'author': handle, 'per_page': 30})
                contributors = get(f'/repos/{path}/contributors', {'per_page': 30})
                collaborators = {c.get('login', '').casefold() for c in contributors if isinstance(c, dict) and c.get('type') == 'User'} if isinstance(contributors, list) else set()
                if not isinstance(commits, list):
                    raise ValueError('Invalid commits')
                authored = [c for c in commits if isinstance(c, dict) and (c.get('author') or {}).get('login', '').casefold() == handle.casefold()][:3]
                for commit in authored:
                    sha = commit.get('sha', '')
                    if not isinstance(sha, str) or not re.fullmatch(r'[a-fA-F0-9]{40}', sha) or sha in seen:
                        continue
                    detail = get(f'/repos/{path}/commits/{sha}')
                    if not isinstance(detail, dict) or (detail.get('author') or {}).get('login', '').casefold() != handle.casefold():
                        continue
                    message = (detail.get('commit') or {}).get('message', '')
                    if not isinstance(message, str) or re.search(r'^\s*(?:initial commit|merge |generated|automated|dependabot)', message, re.I):
                        continue
                    files = meaningful_files(detail.get('files') or [])
                    if not files:
                        continue
                    date = ((detail.get('commit') or {}).get('author') or {}).get('date', '')
                    try:
                        day = datetime.fromisoformat(date.replace('Z', '+00:00')).date().isoformat()
                    except (ValueError, AttributeError):
                        day = ''
                    seen.add(sha)
                    records.append({'skill': 'GitHub', 'source': 'github', 'section': 'external',
                                    'text': f'Account-authored commit modifies substantive files in {path}: ' + ', '.join(files[:5]),
                                    'url': f'https://github.com/{path}/commit/{sha}', 'match_method': 'github_activity_v1',
                                    'activity': 'commit', 'repository': path, 'day': day, 'files': files,
                                    'collaborative': len(collaborators - {handle.casefold()}) > 0})
            # Authored PR search includes contributions to repositories owned by others.
            search = get('/search/issues', {'q': f'author:{handle} is:pr is:public', 'per_page': 5, 'sort': 'updated'})
            if not isinstance(search, dict) or not isinstance(search.get('items'), list):
                raise ValueError('Invalid PR search')
            for item in search['items'][:2]:
                if not isinstance(item, dict):
                    continue
                api_url = item.get('repository_url', '')
                path = repo_path(api_url.removeprefix('https://api.github.com/repos/')) if isinstance(api_url, str) and api_url.startswith('https://api.github.com/repos/') else None
                number = item.get('number')
                if not path or type(number) is not int or number <= 0:
                    continue
                pr = get(f'/repos/{path}/pulls/{number}')
                if not isinstance(pr, dict) or (pr.get('user') or {}).get('login', '').casefold() != handle.casefold() or not pr.get('merged_at'):
                    continue
                files = meaningful_files(get(f'/repos/{path}/pulls/{number}/files', {'per_page': 30}))
                if not files:
                    continue
                reviews = get(f'/repos/{path}/pulls/{number}/reviews', {'per_page': 30})
                reviewed = isinstance(reviews, list) and any(isinstance(r, dict) and r.get('state') in {'APPROVED', 'CHANGES_REQUESTED'} and
                           (r.get('user') or {}).get('type') == 'User' and (r.get('user') or {}).get('login', '').casefold() not in {'', handle.casefold()} for r in reviews)
                records.append({'skill': 'GitHub', 'source': 'github', 'section': 'external',
                                'text': f'Account-authored merged pull request in {path} changes substantive files' + (' and received peer review.' if reviewed else '.'),
                                'url': f'https://github.com/{path}/pull/{number}', 'match_method': 'github_activity_v1',
                                'activity': 'pull_request', 'repository': path, 'reviewed': reviewed, 'files': files})
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            warnings.append('GitHub activity sampling incomplete; unavailable evidence was not inferred.')
    return records, warnings


def assess_github_usage(records):
    """Only activity evidence can produce a rating. No expert rating from a small sample."""
    activity = [r for r in records if r.get('skill') == 'GitHub' and r.get('match_method') == 'github_activity_v1']
    commits = {r['url']: r for r in activity if r.get('activity') == 'commit'}
    pulls = {r['url']: r for r in activity if r.get('activity') == 'pull_request'}
    if not commits and not pulls:
        return None
    files = {f for r in [*commits.values(), *pulls.values()] for f in r.get('files', [])}
    code = any('.' + f.rsplit('.', 1)[-1].lower() in CODE for f in files)
    level = 2 if code else 1
    reason = 'Account-attributed substantive changes demonstrate basic version-control usage.' if code else 'Account-attributed documentation changes demonstrate introductory version-control usage.'
    days = {r['day'] for r in commits.values() if r.get('day')}
    if code and len(commits) >= 2 and len(days) >= 2 and pulls:
        level = 3
        reason = 'Repeated substantive commits on separate days and a merged technical pull request demonstrate a development workflow.'
    projects = {r['repository'] for r in commits.values()}
    tests = any(re.search(r'(^|/)(?:tests?|__tests__)(/|\.)|(?:test|spec)\.', f, re.I) for f in files)
    automation = any(f.startswith('.github/workflows/') for f in files)
    if level == 3 and len(projects) >= 2 and any(r.get('reviewed') for r in pulls.values()) and any(r.get('collaborative') for r in commits.values()) and tests and automation:
        level = 4
        reason = 'Substantive multi-project changes, peer-reviewed collaboration, tests, and workflow automation support an advanced estimate; review required.'
    evidence = [{key: r[key] for key in ('source', 'section', 'text', 'url', 'match_method')} for r in [*commits.values(), *pulls.values()]]
    return {'name': 'GitHub', 'level': level, 'confidence': 'medium' if level >= 3 else 'low',
            'status': 'needs_review' if level == 4 else 'provisional', 'reason': reason, 'evidence': evidence}
