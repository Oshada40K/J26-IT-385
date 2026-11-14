"""Insights API: counterfactuals, confidence-aware uncertainty and explanation stability.

Uses the real saved model and the supplied Component 1 assessment fixture. The
three core career endpoints are covered by the sibling test modules and must stay
unchanged; this file only exercises the additional /api/career/insights route.
"""
import copy
import json
from pathlib import Path

import numpy as np

from app.component03_career import insights, service
from app.component03_career.job_matching_training_output import inference
from app.component03_career.profile_adapter import adapt_technical_profile
from tests import test_career_integration as career_tests


ASSESSMENT = json.loads((Path(__file__).parent / 'fixtures' / 'component01_assessment.json').read_text(encoding='utf-8-sig'))
CANDIDATE = ASSESSMENT['candidate_id']
DETAILS = '/api/component01/skills/' + CANDIDATE + '/details'


class InsightsTests(career_tests.CareerIntegrationTests):
    def live_inputs(self):
        self.data[DETAILS] = copy.deepcopy(ASSESSMENT)
        return {'params': {'candidate_id': CANDIDATE}, 'headers': {'Authorization': 'Bearer test-candidate-token'}}

    def model_inputs(self):
        soft = {**self.profiles['/api/personality/profile'], 'candidate_id': CANDIDATE}
        return soft, adapt_technical_profile(ASSESSMENT)

    def test_fast_scorer_reproduces_exporter_features_and_scores(self):
        soft, tech = self.model_inputs()
        session = insights._Session(soft, tech)
        variants = {
            'baseline': tech,
            'learn': insights.apply_action(tech, {'action': 'learn', 'key': 'docker', 'technology': 'Docker', 'to_level': 3}),
            'improve': insights.apply_action(tech, {'action': 'improve', 'key': 'structured query language sql',
                                                    'technology': 'SQL', 'to_level': 3}),
        }
        for name, variant in variants.items():
            with self.subTest(variant=name):
                candidate, _ = inference.parse_candidate(soft, variant)
                expected = inference.candidate_matrix(candidate)
                fast = session.fast.matrix(session.soft_block, session.fast.vector({k: v * 5 for k, v in candidate['tech'].items()}))
                np.testing.assert_allclose(fast.to_numpy(), expected.to_numpy(), atol=1e-6)
                self.assertEqual(list(fast.columns), list(expected.columns))
                np.testing.assert_allclose(inference.model.predict(fast), inference.model.predict(expected), atol=1e-4)

    def test_insights_contract_and_consistency_with_core_apis(self):
        options = self.live_inputs()
        response = self.client.get('/api/career/insights', **options)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        top = self.client.get('/api/career/top-jobs', **options).json()
        self.assertEqual(set(body), {'candidate_id', 'onet_version', 'model_type', 'score_meaning', 'eligible_occupations',
                                     'best_job', 'counterfactuals', 'uncertainty', 'explanation_stability', 'insight_meaning'})
        self.assertEqual(body['candidate_id'], CANDIDATE)
        self.assertEqual(body['best_job'], top['jobs'][0]['job'])

        cf = body['counterfactuals']
        self.assertEqual(cf['target'], body['best_job'])
        self.assertEqual(cf['baseline_score'], top['jobs'][0]['score'])
        gains = [a['score_gain'] for a in cf['actions']]
        self.assertTrue(cf['actions'], 'the fixture is missing in-demand tools, so actions must exist')
        self.assertEqual(gains, sorted(gains, reverse=True))
        for action in cf['actions']:
            self.assertIn(action['action'], {'learn', 'improve'})
            self.assertGreaterEqual(action['new_rank'], 1)
            self.assertAlmostEqual(action['new_score'] - cf['baseline_score'], action['score_gain'], places=2)
            self.assertEqual(action['becomes_best'], action['new_rank'] == 1)
        self.assertEqual([a['job'] for a in cf['alternatives']], [j['job'] for j in top['jobs'][1:]])
        self.assertEqual(cf['path_to_runner_up']['job'], top['jobs'][1]['job'])

        unc = body['uncertainty']
        self.assertEqual([j['job'] for j in unc['jobs']], [j['job'] for j in top['jobs']])
        self.assertEqual(unc['confidence_source'], 'component01')
        recognised = len(ASSESSMENT['skills']) - len(top['unrecognised_skills'])
        self.assertEqual(sum(unc['confidence_counts'].values()), recognised)
        self.assertEqual(unc['confidence_counts'], {'high': 0, 'medium': 7, 'low': 10})
        for job in unc['jobs']:
            self.assertLessEqual(job['low'], job['mean'])
            self.assertLessEqual(job['mean'], job['high'])
            for key in ['top1_probability', 'top5_probability']:
                self.assertGreaterEqual(job[key], 0)
                self.assertLessEqual(job[key], 1)
        self.assertAlmostEqual(sum(j['top1_probability'] for j in unc['jobs']), 1, delta=1 + 1e-9)
        self.assertIn(unc['stability'], {'high', 'moderate', 'low'})

        stab = body['explanation_stability']
        for key in ['top_factor_agreement', 'mean_top3_overlap']:
            self.assertGreaterEqual(stab[key], 0)
            self.assertLessEqual(stab[key], 1)
        self.assertGreaterEqual(stab['mean_abs_point_change'], 0)
        self.assertIn(stab['label'], {'high', 'moderate', 'low'})

    def test_counterfactual_numbers_match_the_full_exported_pipeline(self):
        soft, tech = self.model_inputs()
        result = service._predict(soft, tech)
        body = insights.compute_insights(soft, tech, {}, result)
        best_code = result['best_job']['onet_soc_code']
        for action in body['counterfactuals']['actions'][:3]:
            with self.subTest(action=action['technology']):
                key = next(k for k in inference.IDF if inference.TECH_LABELS.get(k, k) == action['technology']
                           or inference.tech_key(action['technology']) == k)
                changed = insights.apply_action(tech, {**action, 'key': key})
                rerun = inference.recommend_jobs(soft, changed, n_alternatives=len(inference.jobs) - 1)[0]
                ranked = [rerun['best_job'], *rerun['alternative_jobs']]
                target = next(job for job in ranked if job['onet_soc_code'] == best_code)
                self.assertAlmostEqual(target['match_score_0_to_100'], action['new_score'], delta=0.011)
                self.assertEqual(target['rank'], action['new_rank'])

    def test_insights_are_deterministic(self):
        options = self.live_inputs()
        first = self.client.get('/api/career/insights', **options).json()
        second = self.client.get('/api/career/insights', **options).json()
        self.assertEqual(first, second)

    def test_legacy_profile_without_confidence_assumes_medium(self):
        response = self.client.get('/api/career/insights')
        self.assertEqual(response.status_code, 200, response.text)
        unc = response.json()['uncertainty']
        self.assertIn('assumed medium', unc['confidence_source'])
        self.assertEqual(unc['confidence_counts']['low'], 0)
        self.assertEqual(unc['confidence_counts']['high'], 0)
        self.assertGreater(unc['confidence_counts']['medium'], 0)

    def test_insights_route_honours_candidate_identity_and_upstream_errors(self):
        schema = self.client.get('/openapi.json').json()
        parameters = schema['paths']['/api/career/insights']['get']['parameters']
        self.assertTrue(any(p['name'] == 'candidate_id' and p['in'] == 'query' for p in parameters))
        self.data[DETAILS] = {**copy.deepcopy(ASSESSMENT), 'candidate_id': 'someone-else'}
        self.assertEqual(self.client.get('/api/career/insights', params={'candidate_id': CANDIDATE}).status_code, 502)
        self.mode = 'timeout'
        self.assertEqual(self.client.get('/api/career/insights').status_code, 504)
