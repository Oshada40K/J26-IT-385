"""Situational judgement scoring and scoring-key agreement (Component 2)."""
import copy
import unittest

from fastapi.testclient import TestClient

from app.component02_personality import sjt
from app.main import app

KEY = sjt.load_key()
TRAITS = sjt.TRAITS


def best_for(trait: str, sign: int) -> dict[str, str]:
    """Choose, in every scenario, the option with the highest (sign=1) or lowest (-1) weight for a trait."""
    return {s["id"]: max(s["options"], key=lambda o: sign * o["weights"].get(trait, 0))["id"] for s in KEY["scenarios"]}


class KeyTests(unittest.TestCase):
    def test_eight_to_ten_scenarios_with_unique_ids_and_valid_weights(self):
        self.assertTrue(8 <= len(KEY["scenarios"]) <= 10)
        self.assertEqual(len({s["id"] for s in KEY["scenarios"]}), len(KEY["scenarios"]))
        for s in KEY["scenarios"]:
            self.assertGreaterEqual(len(s["options"]), 3, s["id"])
            for o in s["options"]:
                self.assertTrue(set(o["weights"]) <= set(TRAITS), (s["id"], o["id"]))
                self.assertTrue(all(w in (-1, 1) for w in o["weights"].values()), (s["id"], o["id"]))

    def test_every_trait_is_measured_by_at_least_four_scenarios(self):
        for t, (_, _, n) in sjt.trait_ranges(KEY).items():
            self.assertGreaterEqual(n, 4, t)

    def test_presented_scenarios_hide_the_key(self):
        for s in sjt.presented_scenarios(KEY):
            self.assertTrue(all(set(o) == {"id", "text"} for o in s["options"]))


class ScoringTests(unittest.TestCase):
    def test_extreme_choices_give_zero_and_one(self):
        for t in TRAITS:
            self.assertEqual(sjt.score_responses(best_for(t, 1), KEY)["traits"][t], 1.0, t)
            self.assertEqual(sjt.score_responses(best_for(t, -1), KEY)["traits"][t], 0.0, t)

    def test_scores_in_range_and_coverage_reported(self):
        result = sjt.score_responses({s["id"]: "A" for s in KEY["scenarios"]}, KEY)
        self.assertTrue(all(0 <= v <= 1 for v in result["traits"].values()))
        self.assertTrue(all(n >= 4 for n in result["coverage"].values()))

    def test_invalid_answers_are_rejected(self):
        answers = {s["id"]: "A" for s in KEY["scenarios"]}
        with self.assertRaisesRegex(ValueError, "Missing"):
            sjt.score_responses({k: v for k, v in answers.items() if k != "S1"}, KEY)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            sjt.score_responses({**answers, "S99": "A"}, KEY)
        with self.assertRaisesRegex(ValueError, "no option"):
            sjt.score_responses({**answers, "S1": "Z"}, KEY)


class KappaTests(unittest.TestCase):
    def test_identical_keys_agree_perfectly(self):
        self.assertEqual(sjt.key_agreement({"r1": KEY, "r2": KEY, "r3": KEY})["mean_kappa"], 1.0)

    def test_disagreement_lowers_kappa(self):
        other = copy.deepcopy(KEY)
        for s in other["scenarios"][:5]:
            for o in s["options"]:
                o["weights"] = {}
        result = sjt.key_agreement({"r1": KEY, "r2": other})
        self.assertLess(result["mean_kappa"], 0.8)

    def test_known_kappa_value(self):
        # 10 items, 8 agreements; each rater uses each category half the time -> kappa = (0.8 - 0.5) / 0.5
        self.assertAlmostEqual(sjt.cohen_kappa([1] * 5 + [0] * 5, [1] * 4 + [0] + [1] + [0] * 4), 0.6)


class ApiTests(unittest.TestCase):
    client = TestClient(app)

    def test_scenarios_and_score_endpoints(self):
        data = self.client.get("/api/personality/sjt").json()
        self.assertEqual(len(data["scenarios"]), len(KEY["scenarios"]))
        self.assertNotIn("weights", str(data))
        res = self.client.post("/api/personality/sjt/score", json={"responses": best_for("CON", 1)})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["traits"]["CON"], 1.0)

    def test_incomplete_answers_return_422(self):
        res = self.client.post("/api/personality/sjt/score", json={"responses": {"S1": "A"}})
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
