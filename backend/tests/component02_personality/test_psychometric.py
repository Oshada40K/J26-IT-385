"""IPIP-50 questionnaire scoring (Component 2, T_psy)."""
import unittest

import numpy as np
from fastapi.testclient import TestClient

from app.component02_personality import psychometric
from app.main import app

INSTRUMENT = psychometric.load_instrument()
TRAITS = psychometric.TRAITS


def answers(trait_level: dict[str, int] | None = None, default: int = 3) -> dict[str, int]:
    """Answer as a person whose true level per trait is 1 (low) .. 5 (high)."""
    trait_level = trait_level or {}
    out = {}
    for item in INSTRUMENT["items"]:
        level = trait_level.get(item["trait"], default)
        out[item["id"]] = level if item["key"] == 1 else 6 - level
    out.update({c["id"]: c["expected"] for c in INSTRUMENT["attention_checks"]})
    return out


class InstrumentTests(unittest.TestCase):
    def test_fifty_items_ten_per_trait_with_both_keyings(self):
        self.assertEqual(len(INSTRUMENT["items"]), 50)
        for t in TRAITS:
            keys = [i["key"] for i in INSTRUMENT["items"] if i["trait"] == t]
            self.assertEqual(len(keys), 10, t)
            self.assertIn(-1, keys, t)
            self.assertIn(1, keys, t)

    def test_presented_order_includes_attention_checks_and_hides_keys(self):
        shown = psychometric.presented_items(INSTRUMENT)
        self.assertEqual(len(shown), 52)
        self.assertEqual({"AC1", "AC2"}, {i["id"] for i in shown} & {"AC1", "AC2"})
        self.assertTrue(all(set(i) == {"id", "text"} for i in shown))


class ScoringTests(unittest.TestCase):
    def test_reverse_keyed_items_are_recoded(self):
        result = psychometric.score_responses(answers({"CON": 5, "NEU": 1}), INSTRUMENT)
        self.assertEqual(result["traits"]["CON"], 1.0)
        self.assertEqual(result["traits"]["NEU"], 0.0)
        self.assertEqual(result["traits"]["OPN"], 0.5)
        self.assertTrue(result["valid"])

    def test_scores_stay_in_zero_to_one(self):
        rng = np.random.default_rng(0)
        for _ in range(50):
            r = answers()
            r.update({i["id"]: int(rng.integers(1, 6)) for i in INSTRUMENT["items"]})
            traits = psychometric.score_responses(r, INSTRUMENT)["traits"]
            self.assertTrue(all(0 <= v <= 1 for v in traits.values()))

    def test_failed_attention_check_is_flagged(self):
        r = answers()
        r["AC1"] = 1
        result = psychometric.score_responses(r, INSTRUMENT)
        self.assertFalse(result["attention_passed"])
        self.assertFalse(result["valid"])

    def test_same_answer_everywhere_is_flagged(self):
        r = {i["id"]: 4 for i in INSTRUMENT["items"]}
        r.update({c["id"]: c["expected"] for c in INSTRUMENT["attention_checks"]})
        self.assertFalse(psychometric.score_responses(r, INSTRUMENT)["valid"])

    def test_missing_unknown_and_out_of_range_answers_are_rejected(self):
        r = answers()
        del r["E1"]
        with self.assertRaisesRegex(ValueError, "Missing"):
            psychometric.score_responses(r, INSTRUMENT)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            psychometric.score_responses({**answers(), "X1": 3}, INSTRUMENT)
        with self.assertRaisesRegex(ValueError, "1 to 5"):
            psychometric.score_responses({**answers(), "E1": 6}, INSTRUMENT)


class CronbachAlphaTests(unittest.TestCase):
    def test_consistent_items_give_high_alpha_and_noise_gives_low(self):
        rng = np.random.default_rng(1)
        latent = rng.normal(size=(300, 1))
        consistent = latent + 0.3 * rng.normal(size=(300, 10))
        noise = rng.normal(size=(300, 10))
        self.assertGreater(psychometric.cronbach_alpha(consistent), 0.9)
        self.assertLess(psychometric.cronbach_alpha(noise), 0.3)


class ApiTests(unittest.TestCase):
    client = TestClient(app)

    def test_questionnaire_and_score_endpoints(self):
        items = self.client.get("/api/personality/questionnaire").json()["items"]
        self.assertEqual(len(items), 52)
        res = self.client.post("/api/personality/questionnaire/score", json={"responses": answers({"EXT": 4})})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["traits"]["EXT"], 0.75)

    def test_incomplete_answers_return_422(self):
        res = self.client.post("/api/personality/questionnaire/score", json={"responses": {"E1": 3}})
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
