"""Contract regression tests against the supplied Component 1 assessment."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_new_assessment_does_not_use_other_candidates_soft_profile(self):
        self.data['/api/skill/profile'] = copy.deepcopy(ASSESSMENT)
        response = self.client.get('/api/career/best-job')
        self.assertEqual(response.status_code, 502)
        self.assertIn('matching candidate IDs', response.json()['detail'])

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


if __name__ == '__main__':
    unittest.main()
