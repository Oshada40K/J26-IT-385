"""Contract regression tests against the supplied Component 1 assessment."""
import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.component03_career import service
from app.component03_career.profile_adapter import adapt_technical_profile
from tests import test_career_integration as career_tests


ASSESSMENT = json.loads((Path(__file__).parent / 'fixtures' / 'component01_assessment.json').read_text(encoding='utf-8-sig'))


class AssessmentIntegrationTests(career_tests.CareerIntegrationTests):
    def assessment_inputs(self, path='/api/skill/profile'):
        self.data[path] = copy.deepcopy(ASSESSMENT)
        # Synthetic soft profile only for integration testing, not a candidate
        # assessment. No real Component 2 results were provided with the fixture.
        self.data['/api/personality/profile']['candidate_id'] = ASSESSMENT['candidate_id']

    def test_supplied_assessment_matches_legacy_model_inputs(self):
        self.assessment_inputs()
        normalized = adapt_technical_profile(ASSESSMENT)
        self.assertEqual(normalized['technical_skills'], [
            {'name': s['name'], 'level': s['level']} for s in ASSESSMENT['skills']])
        for endpoint in ['best-job', 'top-jobs', 'explanation']:
            response = self.client.get('/api/career/' + endpoint)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['candidate_id'], ASSESSMENT['candidate_id'])
            self.data['/api/skill/profile'] = normalized
            expected = self.client.get('/api/career/' + endpoint)
            self.assertEqual(response.json(), expected.json())
            self.data['/api/skill/profile'] = copy.deepcopy(ASSESSMENT)

    def test_invalid_assessment_is_rejected(self):
        changes = [('status', 'pending'), ('assessment_method', 'unknown')]
        for key, value in changes:
            with self.subTest(key=key):
                self.assessment_inputs()
                self.data['/api/skill/profile'][key] = value
                self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)
        for value in [-1, 0, 6, True, '3', None]:
            with self.subTest(level=value):
                self.assessment_inputs()
                self.data['/api/skill/profile']['skills'][0]['level'] = value
                self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)

    def test_new_assessment_without_query_uses_fixed_component2_profile(self):
        self.data['/api/skill/profile'] = copy.deepcopy(ASSESSMENT)
        for endpoint in ['best-job', 'top-jobs', 'explanation']:
            response = self.client.get('/api/career/' + endpoint)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['candidate_id'], ASSESSMENT['candidate_id'])

    def test_duplicate_alias_is_rejected_after_adaptation(self):
        self.assessment_inputs()
        duplicate = copy.deepcopy(next(s for s in ASSESSMENT['skills'] if s['name'] == 'JavaScript'))
        duplicate['name'] = 'Java Script'
        self.data['/api/skill/profile']['skills'].append(duplicate)
        self.assertEqual(self.client.get('/api/career/best-job').status_code, 502)

    def test_live_candidate_route_forwards_token_per_request(self):
        path = '/api/component01/skills/' + ASSESSMENT['candidate_id'] + '/details'
        self.assessment_inputs(path)
        received = []
        original_get = self.client.app.state.career_client.get

        async def capture(*args, **kwargs):
            received.append(kwargs.get('headers'))
            return await original_get(*args, **kwargs)

        with patch.object(self.client.app.state.career_client, 'get', side_effect=capture):
            response = self.client.get('/api/career/top-jobs',
                params={'candidate_id': ASSESSMENT['candidate_id']},
                headers={'Authorization': 'Bearer test-candidate-token'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn(path, self.seen)
            self.assertEqual(received, [{'Authorization': 'Bearer test-candidate-token'}] * 2)
            received.clear()
            self.client.get('/api/career/top-jobs', params={'candidate_id': ASSESSMENT['candidate_id']})
            self.assertEqual(received, [{}, {}])

    def test_configured_profile_paths_and_requested_identity(self):
        self.assessment_inputs('/custom/' + ASSESSMENT['candidate_id'])
        with patch.dict('os.environ', {'CAREER_TECHNICAL_PROFILE_PATH': '/custom/{candidate_id}'}):
            self.assertEqual(self.client.get('/api/career/best-job').status_code, 422)
            response = self.client.get('/api/career/best-job', params={'candidate_id': ASSESSMENT['candidate_id']})
            self.assertEqual(response.status_code, 200, response.text)
        self.assessment_inputs()
        with patch.dict('os.environ', {'CAREER_TECHNICAL_PROFILE_PATH': '/api/skill/profile'}):
            response = self.client.get('/api/career/best-job', params={'candidate_id': 'different'})
            self.assertEqual(response.status_code, 502)

    def test_all_career_routes_honor_candidate_query(self):
        schema = self.client.get('/openapi.json').json()
        for endpoint in ['best-job', 'top-jobs', 'explanation']:
            path = '/api/career/' + endpoint
            parameters = schema['paths'][path]['get']['parameters']
            self.assertTrue(any(p['name'] == 'candidate_id' and p['in'] == 'query' for p in parameters))
            # Even a configured legacy upstream must not return a successful
            # sample recommendation for a different requested candidate.
            with patch.dict('os.environ', {'CAREER_TECHNICAL_PROFILE_PATH': '/api/skill/profile'}):
                response = self.client.get(path, params={'candidate_id': 'another-candidate'})
                self.assertEqual(response.status_code, 502, response.text)

    def test_sample_candidate_uses_live_skills_and_unchanged_fixed_soft_profile(self):
        candidate_id = 'candidate_093495d9a2e7460785f1618c623faf50'
        self.assertEqual(ASSESSMENT['candidate_id'], candidate_id)
        path = '/api/component01/skills/' + candidate_id + '/details'
        self.data[path] = copy.deepcopy(ASSESSMENT)
        fixed_soft = copy.deepcopy(self.data['/api/personality/profile'])
        model_soft = {**fixed_soft, 'candidate_id': candidate_id}
        expected = service._predict(model_soft, adapt_technical_profile(ASSESSMENT))
        results = {}
        for endpoint in ['best-job', 'top-jobs', 'explanation']:
            response = self.client.get('/api/career/' + endpoint,
                params={'candidate_id': candidate_id},
                headers={'Authorization': 'Bearer test-candidate-token'})
            self.assertEqual(response.status_code, 200, response.text)
            results[endpoint] = response.json()
            self.assertEqual(response.json()['candidate_id'], candidate_id)
        self.assertEqual(results['best-job']['best_job'], expected['best_job']['job_title'])
        self.assertEqual(results['explanation']['explanation'], expected['best_job']['explanation'])
        self.assertEqual(results['top-jobs']['jobs'], [
            {'ranking': job['rank'], 'job': job['job_title'], 'score': job['match_score_0_to_100']}
            for job in [expected['best_job'], *expected['alternative_jobs']]])
        self.assertEqual(self.seen.count(path), 3)
        self.assertNotIn('/api/skill/profile', self.seen)
        self.assertEqual(self.seen.count('/api/personality/profile'), 3)
        self.assertEqual(self.data['/api/personality/profile'], fixed_soft)
        for job in [expected['best_job'], *expected['alternative_jobs']]:
            reconstructed = job['shap_baseline'] + sum(f['shap_score_points'] for f in job['all_shap_factors'])
            self.assertAlmostEqual(reconstructed, job['raw_model_score'], delta=0.001)

    def test_live_integration_rejects_missing_invalid_and_wrong_candidate_data(self):
        candidate_id = ASSESSMENT['candidate_id']
        path = '/api/component01/skills/' + candidate_id + '/details'
        cases = [
            (path, None), (path, {}), (path, {**ASSESSMENT, 'skills': []}),
            (path, {**ASSESSMENT, 'candidate_id': 'another-candidate'}),
            ('/api/personality/profile', None),
            ('/api/personality/profile', {**self.profiles['/api/personality/profile'], 'soft_skills': []}),
        ]
        for upstream_path, payload in cases:
            with self.subTest(path=upstream_path, payload=payload):
                self.data = copy.deepcopy(self.profiles)
                self.data[path] = copy.deepcopy(ASSESSMENT)
                self.data[upstream_path] = payload
                response = self.client.get('/api/career/top-jobs', params={'candidate_id': candidate_id})
                self.assertEqual(response.status_code, 502, response.text)

    def test_fixed_component2_identity_and_url_variants_do_not_block_prediction(self):
        candidate_id = ASSESSMENT['candidate_id']
        technical_path = '/api/component01/skills/' + candidate_id + '/details'
        self.data[technical_path] = copy.deepcopy(ASSESSMENT)
        for configured_path in ['/api/personality/profile', '/api/personality/profile/',
                                'http://upstream.test/api/personality/profile']:
            with self.subTest(path=configured_path):
                request_path = '/api/personality/profile/' if configured_path.endswith('/') else '/api/personality/profile'
                fixed_soft = {**self.profiles['/api/personality/profile'], 'candidate_id': 'fixed_personality_fixture'}
                self.data[request_path] = copy.deepcopy(fixed_soft)
                with patch.dict('os.environ', {'CAREER_SOFT_PROFILE_PATH': configured_path}):
                    for endpoint in ['best-job', 'top-jobs', 'explanation']:
                        response = self.client.get('/api/career/' + endpoint, params={'candidate_id': candidate_id})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['candidate_id'], candidate_id)
                self.assertEqual(self.data[request_path], fixed_soft)

    def test_custom_soft_endpoint_cannot_be_rebound_as_fixed_component2_data(self):
        candidate_id = ASSESSMENT['candidate_id']
        self.data['/api/component01/skills/' + candidate_id + '/details'] = copy.deepcopy(ASSESSMENT)
        self.data['/custom/soft'] = copy.deepcopy(self.profiles['/api/personality/profile'])
        with patch.dict('os.environ', {'CAREER_SOFT_PROFILE_PATH': '/custom/soft'}):
            response = self.client.get('/api/career/best-job', params={'candidate_id': candidate_id})
            self.assertEqual(response.status_code, 502, response.text)

    def test_different_cv_ids_are_bound_independently_for_all_career_apis(self):
        fixed_soft = copy.deepcopy(self.data['/api/personality/profile'])
        candidates = {
            'candidate_cv_python': [{'name': 'Python', 'level': 2}],
            'candidate_cv_javascript': [{'name': 'JavaScript', 'level': 3}],
        }
        for candidate_id, skills in candidates.items():
            path = '/api/component01/skills/' + candidate_id + '/details'
            assessment = copy.deepcopy(ASSESSMENT)
            assessment['candidate_id'] = candidate_id
            assessment['skills'] = [
                {**next(s for s in ASSESSMENT['skills'] if s['name'] == skill['name']), **skill}
                for skill in skills
            ]
            self.data[path] = assessment
        with patch.object(service, '_predict', wraps=service._predict) as predict:
            # Return to the first CV after the second to catch leaked IDs.
            for candidate_id in ['candidate_cv_python', 'candidate_cv_javascript', 'candidate_cv_python']:
                for endpoint in ['best-job', 'top-jobs', 'explanation']:
                    response = self.client.get('/api/career/' + endpoint,
                        params={'candidate_id': candidate_id})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['candidate_id'], candidate_id)
                    soft_input, technical_input = predict.call_args.args
                    self.assertEqual(soft_input, {**fixed_soft, 'candidate_id': candidate_id})
                    self.assertEqual(technical_input['candidate_id'], candidate_id)
                    self.assertEqual(technical_input['technical_skills'], candidates[candidate_id])
        self.assertEqual(self.data['/api/personality/profile'], fixed_soft)

    def test_simultaneous_cv_predictions_keep_their_own_candidate_ids(self):
        fixed_soft = copy.deepcopy(self.data['/api/personality/profile'])
        candidate_ids = ['candidate_parallel_one', 'candidate_parallel_two']
        for candidate_id in candidate_ids:
            assessment = {**copy.deepcopy(ASSESSMENT), 'candidate_id': candidate_id}
            self.data['/api/component01/skills/' + candidate_id + '/details'] = assessment

        def predict_candidate(candidate_id):
            response = self.client.get('/api/career/top-jobs', params={'candidate_id': candidate_id})
            return candidate_id, response

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(predict_candidate, candidate_ids))
        for candidate_id, response in results:
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['candidate_id'], candidate_id)
            self.assertEqual(len(response.json()['jobs']), 5)
        self.assertEqual(self.data['/api/personality/profile'], fixed_soft)


if __name__ == '__main__':
    unittest.main()
