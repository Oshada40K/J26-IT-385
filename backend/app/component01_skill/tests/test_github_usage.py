from unittest.mock import patch
import httpx
import pytest
from app.component01_skill.services.github_usage import collect_usage, assess_github_usage
from app.component01_skill.services import profile_service


def commit(n=1, repo='Example/project', files=None):
    return {'skill': 'GitHub', 'source': 'github', 'section': 'external', 'match_method': 'github_activity_v1',
            'activity': 'commit', 'url': f'https://github.com/{repo}/commit/{n}', 'repository': repo,
            'text': 'Substantive changes', 'files': files or ['src/app.py'], 'day': f'2026-01-{n:02}', 'collaborative': True}


def pull(reviewed=False):
    return dict(commit(), activity='pull_request', url='https://github.com/Example/project/pull/1', reviewed=reviewed)


def test_empty_and_metadata_only_profiles_have_no_rating():
    assert assess_github_usage([]) is None
    assert assess_github_usage([{'skill': 'Python', 'text': 'Many repositories'}]) is None


@pytest.mark.parametrize('records, level', [
    ([commit(files=['README.md'])], 1), ([commit()], 2),
    ([commit(), commit(2), pull()], 3),
    ([commit(files=['tests/test_app.py', '.github/workflows/ci.yml']), commit(2, 'Example/other'), pull(True)], 4),
    ([commit(), commit(), pull()], 2),
])
def test_evidence_rubric(records, level):
    result = assess_github_usage(records)
    assert result['name'] == 'GitHub' and result['level'] == level
    assert len(result['evidence']) == len({r['url'] for r in records})


def test_api_authorship_files_external_contributions_and_cache():
    collect_usage.cache_clear()
    requests = []
    sha = 'a' * 40
    def handler(req):
        requests.append(req)
        path = req.url.path
        assert req.url.host == 'api.github.com'
        if path == '/users/Example/repos':
            data = [{'full_name': 'Example/project', 'owner': {'login': 'Example'}},
                    {'full_name': 'Example/copied', 'owner': {'login': 'Example'}, 'fork': True}]
        elif path.endswith('/contributors'):
            data = [{'login': 'Example', 'type': 'User'}, {'login': 'Peer', 'type': 'User'}]
        elif path.endswith('/commits'):
            data = [{'sha': sha, 'author': {'login': 'Example'}}, {'sha': 'b' * 40, 'author': {'login': 'Other'}}]
        elif path.endswith('/commits/' + sha):
            data = {'author': {'login': 'Example'}, 'commit': {'message': 'Fix app', 'author': {'date': '2026-01-01T12:00:00Z'}},
                    'files': [{'filename': 'src/app.py', 'changes': 12}, {'filename': 'package-lock.json', 'changes': 999}]}
        elif path == '/search/issues':
            data = {'items': [{'repository_url': 'https://api.github.com/repos/Community/project', 'number': 4}]}
        elif path.endswith('/pulls/4'):
            data = {'user': {'login': 'Example'}, 'merged_at': '2026-01-03'}
        elif path.endswith('/files'):
            data = [{'filename': 'src/fix.py', 'changes': 10}]
        elif path.endswith('/reviews'):
            data = [{'user': {'login': 'Peer', 'type': 'User'}, 'state': 'APPROVED'}]
        else:
            raise AssertionError(path)
        return httpx.Response(200, json=data)
    real_client = httpx.Client
    with patch('httpx.Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
        records, warnings = collect_usage('Example', 1)
        assert collect_usage('Example', 1)[0] == records
    assert not warnings and len(records) == 2 and len(requests) == 8
    assert records[0]['files'] == ['src/app.py']
    assert records[1]['reviewed'] and records[1]['repository'] == 'Community/project'
    collect_usage.cache_clear()


@pytest.mark.parametrize('status', [301, 403, 404, 429])
def test_inaccessible_activity_does_not_invent_evidence(status):
    collect_usage.cache_clear()
    real_client = httpx.Client
    with patch('httpx.Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(lambda req: httpx.Response(status)), **kw)):
        records, warnings = collect_usage('Example', 1)
    assert records == [] and warnings


@pytest.mark.parametrize('links, records, expected', [
    ([], [], [('Python', 2)]),
    (['https://github.com/Example'], [], [('Python', 2)]),
    (['https://github.com/Example'], [commit(), commit(2), pull()], [('GitHub', 3), ('Python', 2)]),
])
def test_automatic_upload_preserves_cv_and_adds_only_supported_github(links, records, expected, monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    with patch.object(profile_service, 'parse_cv_document', return_value=('SKILLS\nPython', links)), \
         patch.object(profile_service, 'analyze_github_profile', return_value=(records, 'completed', [])) as analyzer, \
         patch.object(profile_service.repository, 'save_assessment', side_effect=lambda cid, content, details: details):
        result = profile_service.process_cv('candidate', 'cv.pdf', b'cv')
    assert analyzer.call_count == len(links)
    assert [(s['name'], s['level']) for s in result['skills']] == expected
    assert all(set(s) == {'name', 'level', 'confidence', 'status', 'reason', 'evidence'} for s in result['skills'])
    if not links:
        assert 'github' not in str(result).lower()
