"""Confidence-weighted fusion and Personality Consistency Score (Component 2)."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.component02_personality import fusion
from app.main import app

TRAITS = fusion.TRAITS
CFG = fusion.load_config()


def source(levels: dict[str, float], **extra) -> dict:
    return {"traits": {t: levels.get(t, 0.5) for t in TRAITS}, **extra}


def questionnaire(levels, valid=True):
    return source(levels, valid=valid)


def scenarios(levels):
    return source(levels, coverage={t: 8 for t in TRAITS})


def writing(levels, words=300):
    return source(levels, word_count=words)


TRUE_PROFILE = {"OPN": 0.6, "CON": 0.5, "EXT": 0.4, "AGR": 0.55, "NEU": 0.5}


class FusionTests(unittest.TestCase):
    def test_agreeing_sources_give_high_consistency_and_no_flags(self):
        r = fusion.combine(questionnaire(TRUE_PROFILE), scenarios(TRUE_PROFILE), writing(TRUE_PROFILE))
        self.assertEqual(r["consistency"]["score"], 1.0)
        self.assertEqual(r["consistency"]["band"]["label"], "High")
        self.assertEqual(r["consistency"]["flagged_traits"], [])
        for t in TRAITS:
            self.assertAlmostEqual(r["traits"][t], TRUE_PROFILE[t])

    def test_simulated_socially_desirable_responding_lowers_pcs_and_flags_traits(self):
        """Self-report shifted towards desirable answers while behaviour stays the same (proposal 3.5)."""
        honest = fusion.combine(questionnaire(TRUE_PROFILE), scenarios(TRUE_PROFILE), writing(TRUE_PROFILE))
        faked = {**TRUE_PROFILE, "CON": 0.95, "AGR": 0.95, "NEU": 0.05}
        r = fusion.combine(questionnaire(faked), scenarios(TRUE_PROFILE), writing(TRUE_PROFILE))
        self.assertLess(r["consistency"]["score"], honest["consistency"]["score"])
        self.assertEqual(set(r["consistency"]["flagged_traits"]), {"CON", "AGR", "NEU"})
        self.assertEqual(r["consistency"]["per_trait"]["CON"]["direction"], "self-report higher")
        self.assertEqual(r["consistency"]["per_trait"]["NEU"]["direction"], "behaviour higher")

    def test_fused_score_lies_between_sources_and_keeps_both_estimates(self):
        r = fusion.combine(questionnaire({"CON": 0.9}), scenarios({"CON": 0.3}), None)
        self.assertTrue(0.3 < r["traits"]["CON"] < 0.9)
        self.assertEqual(r["consistency"]["per_trait"]["CON"]["questionnaire"], 0.9)
        self.assertAlmostEqual(r["consistency"]["per_trait"]["CON"]["behavioural"], 0.3)

    def test_more_text_gives_text_more_weight(self):
        short = fusion.combine(None, scenarios({"EXT": 0.2}), writing({"EXT": 0.8}, words=30))
        long = fusion.combine(None, scenarios({"EXT": 0.2}), writing({"EXT": 0.8}, words=300))
        self.assertGreater(long["behavioural"]["EXT"], short["behavioural"]["EXT"])

    def test_invalid_questionnaire_gets_half_weight(self):
        valid = fusion.combine(questionnaire({"CON": 1.0}), scenarios({"CON": 0.0}), None)
        invalid = fusion.combine(questionnaire({"CON": 1.0}, valid=False), scenarios({"CON": 0.0}), None)
        self.assertLess(invalid["traits"]["CON"], valid["traits"]["CON"])
        self.assertTrue(invalid["notes"])

    def test_missing_sources(self):
        only_q = fusion.combine(questionnaire(TRUE_PROFILE))
        self.assertIsNone(only_q["consistency"])
        self.assertEqual(only_q["traits"]["OPN"], 0.6)
        with self.assertRaises(ValueError):
            fusion.combine()

    def test_bands(self):
        self.assertEqual(fusion.band_for(0.8, CFG)["label"], "High")
        self.assertEqual(fusion.band_for(0.6, CFG)["label"], "Moderate")
        self.assertEqual(fusion.band_for(0.2, CFG)["label"], "Low")


class FakePredictor:
    def predict(self, answers):
        return {t: 0.5 for t in TRAITS}


class AssessApiTests(unittest.TestCase):
    client = TestClient(app)

    def body(self):
        q = self.client.get("/api/personality/questionnaire").json()["items"]
        s = self.client.get("/api/personality/sjt").json()["scenarios"]
        answers = {i["id"]: 3 for i in q}
        answers.update({"AC1": 4, "AC2": 1})
        return {"questionnaire": answers, "sjt": {x["id"]: "A" for x in s},
                "answers": ["I like to plan my work carefully and finish tasks early with my team every week."] * 2}

    def test_full_assessment_returns_profile_and_consistency(self):
        with patch("app.component02_personality.text_trait.get_predictor", return_value=FakePredictor()):
            res = self.client.post("/api/personality/assess", json=self.body())
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(set(data["traits"]), set(TRAITS))
        self.assertEqual(set(data["sources"]), {"questionnaire", "situational_judgement", "text"})
        self.assertTrue(0 <= data["consistency"]["score"] <= 1)

    def test_empty_request_returns_422(self):
        self.assertEqual(self.client.post("/api/personality/assess", json={}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
