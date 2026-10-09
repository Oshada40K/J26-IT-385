"""Check readiness and all component APIs using only the Python standard library."""
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def get(base_url, path):
    with urlopen(base_url.rstrip('/') + path, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f'{path}: HTTP {response.status}')
        return json.load(response)


def verify(base_url):
    deadline = time.monotonic() + 180
    while True:
        try:
            if get(base_url, '/health') == {'status': 'healthy'}:
                break
        except (URLError, TimeoutError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Backend did not become healthy within 180 seconds')
        time.sleep(3)

    assert get(base_url, '/')['status'] == 'running'
    technical = get(base_url, '/api/skill/profile')
    soft = get(base_url, '/api/personality/profile')
    assert technical['candidate_id'] == soft['candidate_id']
    assert technical['schema_version'] == soft['schema_version'] == '1.0'
    best = get(base_url, '/api/career/best-job')
    top = get(base_url, '/api/career/top-jobs')
    explanation = get(base_url, '/api/career/explanation')
    assert best['candidate_id'] == top['candidate_id'] == explanation['candidate_id'] == technical['candidate_id']
    assert len(top['jobs']) == 5
    assert [job['ranking'] for job in top['jobs']] == [1, 2, 3, 4, 5]
    assert best['best_job'] == top['jobs'][0]['job']
    assert all(set(job) == {'ranking', 'job', 'score'} for job in top['jobs'])
    assert all(0 <= job['score'] <= 100 for job in top['jobs'])
    assert [job['score'] for job in top['jobs']] == sorted((job['score'] for job in top['jobs']), reverse=True)
    assert set(explanation) == {'candidate_id', 'onet_version', 'model_type', 'score_meaning', 'eligible_occupations', 'explanation'}
    assert isinstance(explanation['explanation'], str) and explanation['explanation']
    assert get(base_url, '/api/roadmap/test')['status'] == 'working'
    schema = get(base_url, '/openapi.json')
    assert '/api/career/top-jobs' in schema['paths']
    print('PASS: health, fixtures, career inference, rankings, explanation, roadmap and OpenAPI')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python scripts/smoke_test.py <backend-base-url>')
    verify(sys.argv[1])
