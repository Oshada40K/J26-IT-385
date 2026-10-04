"""Integration checks using the real exported model and profile API responses."""
import copy
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.component03_career import service


class CareerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.load_patch = patch.object(service.inference, 'load_saved_matcher', wraps=service.inference.load_saved_matcher)
        cls.loader = cls.load_patch.start()
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        cls.profiles = {
            '/api/skill/profile': cls.client.get('/api/skill/profile').json(),
            '/api/personality/profile': cls.client.get('/api/personality/profile').json(),
        }
        cls.original = app.state.career_client

    @classmethod
    def tearDownClass(cls):
        app.state.career_client = cls.original
        cls.context.__exit__(None, None, None)
        cls.load_patch.stop()

    def setUp(self):
        self.data = copy.deepcopy(self.profiles)
        self.seen = []
        self.mode = None

        def transport(request):
            self.seen.append(request.url.path)
            if self.mode == 'timeout':
                raise httpx.ReadTimeout('test timeout', request=request)
            if self.mode == 'unreachable':
                raise httpx.ConnectError('test connection failure', request=request)
            if self.mode == 'http':
                return httpx.Response(503)
            if self.mode == 'json':
                return httpx.Response(200, text='invalid json')
            return httpx.Response(200, json=self.data[request.url.path])

        app.state.career_client = httpx.AsyncClient(base_url='http://upstream.test', transport=httpx.MockTransport(transport))

    def tearDown(self):
        self.client.portal.call(app.state.career_client.aclose)
        app.state.career_client = self.original

    def test_complete_inference_and_consistency(self):
        responses = [self.client.get('/api/career/' + name) for name in ['best-job', 'top-jobs', 'explanation']]
        for response in responses:
            self.assertEqual(response.status_code, 200, response.text)
        best, top, explanation = [r.json() for r in responses]
        self.assertEqual(len(top['jobs']), 5)
        self.assertEqual([j['ranking'] for j in top['jobs']], [1, 2, 3, 4, 5])
        self.assertEqual(best['best_job'], top['jobs'][0]['job'])
        self.assertEqual(set(best), {'candidate_id', 'onet_version', 'model_type', 'score_meaning', 'eligible_occupations', 'unrecognised_skills', 'best_job'})
        raw = service._predict(self.profiles['/api/personality/profile'], self.profiles['/api/skill/profile'])
        self.assertEqual(raw['best_job']['explanation'], explanation['explanation'])
        self.assertEqual(set(top), {'candidate_id', 'onet_version', 'model_type', 'score_meaning', 'eligible_occupations', 'unrecognised_skills', 'jobs'})
        for compact, original in zip(top['jobs'], [raw['best_job'], *raw['alternative_jobs']]):
            self.assertEqual(compact, {'ranking': original['rank'], 'job': original['job_title'], 'score': original['match_score_0_to_100']})
        self.assertEqual(set(explanation), {'candidate_id', 'onet_version', 'model_type', 'score_meaning', 'eligible_occupations', 'explanation'})
        for key in set(explanation) - {'explanation'}:
            self.assertEqual(explanation[key], best[key])
        for job in [raw['best_job'], *raw['alternative_jobs']]:
            reconstructed = job['shap_baseline'] + sum(f['shap_score_points'] for f in job['all_shap_factors'])
            self.assertAlmostEqual(reconstructed, job['raw_model_score'], delta=0.001)
        self.assertEqual(self.seen.count('/api/skill/profile'), 3)
        self.assertEqual(self.seen.count('/api/personality/profile'), 3)
        self.assertEqual(self.loader.call_count, 1)
        self.assertEqual(self.client.get('/api/roadmap/test').status_code, 200)
        schema = self.client.get('/openapi.json').json()
        for name in ['best-job', 'top-jobs', 'explanation']:
            self.assertIn('schema', schema['paths']['/api/career/' + name]['get']['responses']['200']['content']['application/json'])

    def test_invalid_profiles(self):
        path = '/api/skill/profile'
        for value in [-1, 6, True, '4', None]:
            with self.subTest(level=value):
                self.data = copy.deepcopy(self.profiles)
                self.data[path]['technical_skills'][0]['level'] = value
                self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)
        self.data = copy.deepcopy(self.profiles)
        self.data[path]['schema_version'] = '2.0'
        self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)
        self.data = copy.deepcopy(self.profiles)
        self.data[path]['candidate_id'] = 'different'
        self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)

    def test_upstream_errors(self):
        for mode, status in [('timeout', 504), ('unreachable', 502), ('http', 502), ('json', 502)]:
            with self.subTest(mode=mode):
                self.mode = mode
                response = self.client.get('/api/career/best-job')
                self.assertEqual(response.status_code, status)
                self.assertTrue(response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
