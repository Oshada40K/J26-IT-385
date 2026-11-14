"""Expert-agreement toolkit: metric correctness and a blind-sheet round trip on the fixture."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.component03_career.evaluation import expert_agreement as ea
from app.component03_career.evaluation import export_rating_sheet as sheet
from app.component03_career.job_matching_training_output import inference
from app.component03_career.profile_adapter import adapt_technical_profile

FIXTURES = Path(__file__).parent / 'fixtures'


class MetricTests(unittest.TestCase):
    def test_ndcg_perfect_reversed_and_random_baseline(self):
        self.assertAlmostEqual(ea.ndcg_at_k([5, 4, 3, 2, 1]), 1.0)
        reversed_order = ea.ndcg_at_k([1, 2, 3, 4, 5])
        self.assertLess(reversed_order, 1.0)
        baseline = ea.random_ndcg_at_k([5, 4, 3, 2, 1])
        self.assertGreater(baseline, reversed_order)
        self.assertLess(baseline, 1.0)
        self.assertEqual(ea.ndcg_at_k([1, 1, 1]), 1.0)   # ties: any order is ideal
        self.assertEqual(ea.ndcg_at_k([]), 0.0)

    def test_precision_and_spearman(self):
        self.assertEqual(ea.precision_at_k([5, 3, 4], 3), 2 / 3)
        self.assertEqual(ea.precision_at_k([2], 1), 0.0)
        self.assertAlmostEqual(ea.spearman([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertAlmostEqual(ea.spearman([1, 2, 3], [30, 20, 10]), -1.0)
        self.assertAlmostEqual(ea.spearman([1, 2, 3, 4], [1, 1, 2, 2]), 0.894, places=3)
        self.assertTrue(ea.spearman([1, 2], [1, 1]) != ea.spearman([1, 2], [1, 1]))   # NaN when constant


class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inference.load_saved_matcher(Path(inference.__file__).parent)

    def test_export_and_score_blind_sheet(self):
        technical = adapt_technical_profile(json.loads((FIXTURES / 'component01_assessment.json').read_text(encoding='utf-8-sig')))
        soft = json.loads((Path(inference.__file__).parents[2] / 'component02_personality' / 'soft_skills.json').read_text(encoding='utf-8'))
        result = sheet.recommend(soft, technical)
        rows, key = sheet.build_rows([result])
        self.assertEqual(len(rows), 5)
        self.assertEqual({row['item_id'] for row in rows}, {row['item_id'] for row in key})
        self.assertTrue(all(row['relevance_1_to_5'] == '' for row in rows))
        self.assertNotIn('model_rank', rows[0])
        # Shuffled: the displayed order must not simply equal the model order for this seed.
        shown = [next(k['model_rank'] for k in key if k['item_id'] == row['item_id']) for row in rows]
        self.assertNotEqual(shown, [1, 2, 3, 4, 5])

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            sheet.write_csv(folder / 'model_key.csv', key)
            # A rater who agrees with the model exactly, and one who inverts it.
            for name, transform in [('agree', lambda rank: 6 - rank), ('invert', lambda rank: rank)]:
                filled = [{**row, 'relevance_1_to_5': transform(rank)} for row, rank in zip(rows, shown)]
                sheet.write_csv(folder / f'{name}.csv', filled)
            report = ea.evaluate(ea.read_csv(folder / 'model_key.csv'), [folder / 'agree.csv', folder / 'invert.csv'])
        self.assertAlmostEqual(report['raters']['agree']['ndcg_at_5'], 1.0)
        self.assertEqual(report['raters']['agree']['precision_at_1'], 1.0)
        self.assertLess(report['raters']['invert']['ndcg_at_5'], report['raters']['agree']['random_ndcg_at_5'])
        self.assertAlmostEqual(report['inter_rater_spearman'], -1.0)
        self.assertIn('NDCG@5', ea.markdown_table(report))

    def test_main_writes_three_files(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet.main(['--technical', str(FIXTURES / 'component01_assessment.json'), '--out', folder])
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             ['candidate_profiles.md', 'model_key.csv', 'rating_sheet.csv'])
            with open(Path(folder) / 'rating_sheet.csv', newline='', encoding='utf-8') as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 5)
