"""Component 04 tests: assessment form API, explainable analysis and C1 integration."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.component01_skill import repository as c1_repository
from app.component04_roadmap import service
from app.component04_roadmap.c4_engine import C_FEATURES
from app.component04_roadmap.router import router

SOFTWARE_DEVELOPERS = "15-1252.00"
MODELS = service.engine().models_available()
needs_models = unittest.skipUnless(MODELS, "trained model files are not present (*.joblib is git-ignored)")


def form(confidence, methods=("video_tutorials",), hours="4-6", projects=0, certifications=0, internships=0, **extra):
    return {"career_id": SOFTWARE_DEVELOPERS, "confidence": confidence,
            "preferences": {"learning_methods": list(methods), "weekly_hours": hours, **extra},
            "experience": {"num_projects": projects, "num_certifications": certifications, "num_internships": internships}}


class C4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"C4_DATABASE_PATH": str(Path(self.temp.name) / "c4.sqlite3"),
                                           "SKILL_DATABASE_PATH": str(Path(self.temp.name) / "skills.sqlite3")})
        self.env.start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def candidate(self, skills):
        session = c1_repository.create_candidate()
        if skills is not None:
            c1_repository.save_assessment(session["candidate_id"], b"cv", {"skills": skills})
        return session["candidate_id"], {"Authorization": f"Bearer {session['access_token']}"}

    def questions(self, c1_skills=()):
        response = self.client.post("/api/roadmap/assessment/questions",
                                    json={"career_id": SOFTWARE_DEVELOPERS, "c1_skills": list(c1_skills)})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["skills"]

    def rate_all(self, skills, rating=3):
        return [{"skill_id": s["skill_id"], "rating": rating} for s in skills]

    # ------------------------------------------------------------------ form API
    def test_questions_are_unique_and_include_cv_skills(self):
        skills = self.questions([{"name": "React", "level": 3}, {"name": "reactjs", "level": 2}, {"name": "Unknownium"}])
        ids = [s["skill_id"] for s in skills]
        self.assertTrue(10 <= len(ids) <= 15)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(next(s for s in skills if s["skill_name"] == "React")["in_cv"])

    def test_unseen_career_is_rejected_safely(self):
        response = self.client.post("/api/roadmap/assessment/questions", json={"career_name": "Astronaut"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("not one of", response.json()["detail"])

    def test_submission_validation(self):
        bad = form([{"skill_id": "SK018", "rating": 9}], methods=["other"], projects=-1)
        response = self.client.post("/api/roadmap/assessment", json=bad)
        self.assertEqual(response.status_code, 422)
        duplicate = form([{"skill_id": "SK018", "rating": 2}, {"skill_id": "SK018", "rating": 3}])
        self.assertEqual(self.client.post("/api/roadmap/assessment", json=duplicate).status_code, 422)

    def test_assessments_are_private_to_their_candidate(self):
        candidate_id, headers = self.candidate([{"name": "Python", "level": 3, "confidence": "medium"}])
        saved = self.client.post("/api/roadmap/assessment", headers=headers,
                                 json={**form(self.rate_all(self.questions())), "candidate_id": candidate_id})
        self.assertEqual(saved.status_code, 201, saved.text)
        assessment_id = saved.json()["assessment_id"]
        _, other = self.candidate(None)
        self.assertEqual(self.client.get(f"/api/roadmap/assessment/{assessment_id}", headers=other).status_code, 403)
        self.assertEqual(self.client.get(f"/api/roadmap/analysis/{assessment_id}").status_code, 403)
        latest = self.client.get("/api/roadmap/assessment/latest", headers=headers)
        self.assertEqual(latest.json()["assessment_id"], assessment_id)

    def test_missing_models_keep_the_form_working(self):
        with patch.object(service.engine(), "models_dir", Path(self.temp.name) / "missing"), \
             patch.object(service.engine(), "cfg", {}):
            saved = self.client.post("/api/roadmap/assessment", json=form(self.rate_all(self.questions())))
            self.assertEqual(saved.status_code, 201)
            self.assertIsNone(saved.json()["readiness_score"])
            response = self.client.get(f"/api/roadmap/analysis/{saved.json()['assessment_id']}")
            self.assertEqual(response.status_code, 503)
            self.assertIn("missing", response.json()["detail"])

    # ------------------------------------------------------------------ analysis
    def analyse(self, cv_skills, rating=3, **form_args):
        candidate_id, headers = self.candidate(cv_skills)
        questions = self.questions(cv_skills or [])
        body = {**form(self.rate_all(questions, rating), **form_args), "candidate_id": candidate_id}
        saved = self.client.post("/api/roadmap/assessment", headers=headers, json=body)
        self.assertEqual(saved.status_code, 201, saved.text)
        response = self.client.get(f"/api/roadmap/analysis/{saved.json()['assessment_id']}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), headers, body

    @needs_models
    def test_confidence_never_counts_as_proficiency(self):
        result, _, _ = self.analyse([], rating=5)
        for skill in result["skill_gaps"]["skills"]:
            self.assertEqual(skill["current_proficiency"], 0)
            self.assertEqual(skill["status"], "gap")
            self.assertTrue(skill["overconfident"])
        self.assertTrue(any("No CV skills" in w for w in result["warnings"]))

    @needs_models
    def test_priority_score_is_the_documented_weighted_sum(self):
        result, _, _ = self.analyse([{"name": "Python", "level": 4, "confidence": "medium"}])
        weights = [f["weight"] for f in result["priorities"][0]["factors"]]
        self.assertAlmostEqual(sum(weights), 1.0, places=3)
        scores = [p["priority_score"] for p in result["priorities"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for p in result["priorities"]:
            self.assertAlmostEqual(p["priority_score"], sum(f["value"] * f["weight"] for f in p["factors"]), places=3)
            for f in p["factors"]:
                self.assertGreaterEqual(f["value"], 0)
                self.assertLessEqual(f["value"], 1)

    @needs_models
    def test_readiness_matches_trained_linear_model(self):
        eng = service.engine()
        cv = {"candidate_id": None, "skills": [{"name": "JavaScript", "level": 4, "confidence": "medium"},
                                               {"name": "Git", "level": 4, "confidence": "medium"}]}
        record = {"career_id": SOFTWARE_DEVELOPERS, "confidence": [], "preferences": {},
                  "activity": {"num_projects": 3, "num_certifications": 1, "num_internships": 1}}
        readiness = eng.analyze_assessment(cv, record)["readiness"]
        terms = {t["feature"]: t for g in readiness["groups"] for t in g["terms"]}
        self.assertAlmostEqual(readiness["raw_score"], readiness["intercept"] + sum(t["points"] for t in terms.values()), places=3)
        x = pd.DataFrame([{f: terms[f]["value"] for f in C_FEATURES}])
        predicted = eng.models["C_readiness"]["model"].predict(x)[0]
        self.assertAlmostEqual(readiness["raw_score"], predicted, delta=0.01)  # API values are rounded to 4 d.p.
        self.assertTrue(0 <= readiness["score"] <= 100)

    @needs_models
    def test_gap_status_agrees_with_readiness_coverage(self):
        result, _, _ = self.analyse([{"name": "Selenium", "level": 3, "confidence": "medium"},
                                     {"name": "JavaScript", "level": 4, "confidence": "medium"},
                                     {"name": "Git", "level": 5, "confidence": "medium"}])
        summary = result["skill_gaps"]["summary"]
        coverage = next(t for g in result["readiness"]["groups"] for t in g["terms"] if t["feature"] == "coverage_ratio")
        self.assertAlmostEqual((summary["met"] + summary["review"]) / summary["required"], coverage["value"], places=3)
        for skill in result["skill_gaps"]["skills"]:
            self.assertEqual(skill["status"] == "gap", skill["current_level"] < skill["required_level"], skill["skill_name"])

    @needs_models
    def test_roadmap_orders_prerequisites_and_stages(self):
        result, _, _ = self.analyse([{"name": "Python", "level": 2, "confidence": "low"}], methods=["video_tutorials"])
        steps = [s for stage in result["roadmap"]["stages"] for s in stage["steps"]]
        seen = set()
        for step in steps:
            self.assertTrue(set(step["prerequisites"]) <= seen, step["skill_name"])
            self.assertTrue(step["milestones"] and step["activities"] and step["project"])
            self.assertLessEqual(step["start_week"], step["end_week"])
            seen.add(step["skill_name"])
        stages = [s["stage"] for s in result["roadmap"]["stages"]]
        self.assertEqual(stages, sorted(stages, key=["Beginner", "Intermediate", "Advanced"].index))
        eng = service.engine()
        for step in steps:
            available = set(eng.res[eng.res.skill_id == step["skill_id"]].resource_type)
            if "video" in available:
                self.assertEqual(step["resources"][0]["type"], "video")

    @needs_models
    def test_roadmap_updates_when_cv_and_experience_change(self):
        first, headers, body = self.analyse([{"name": "JavaScript", "level": 1, "confidence": "low"}])
        candidate_id = body["candidate_id"]
        c1_repository.save_assessment(candidate_id, b"cv2", {"skills": [
            {"name": "JavaScript", "level": 5, "confidence": "medium"}, {"name": "HTML", "level": 5, "confidence": "medium"},
            {"name": "React", "level": 5, "confidence": "medium"}]})
        body["experience"] = {"num_projects": 4, "num_certifications": 2, "num_internships": 1}
        saved = self.client.post("/api/roadmap/assessment", headers=headers, json=body).json()
        second = self.client.get(f"/api/roadmap/analysis/{saved['assessment_id']}", headers=headers).json()
        self.assertGreater(second["readiness"]["score"], first["readiness"]["score"])
        self.assertLess(second["roadmap"]["total_hours"], first["roadmap"]["total_hours"])
        self.assertEqual(second["assessment"]["previous"]["assessment_id"], first["assessment"]["assessment_id"])
        stale = self.client.get(f"/api/roadmap/analysis/{first['assessment']['assessment_id']}", headers=headers).json()
        self.assertTrue(stale["assessment"]["changes"])

    @needs_models
    def test_model_loading_restores_numpy(self):
        import numpy.random._pickle as npk
        before = getattr(npk, "__bit_generator_ctor")
        service.engine().ensure_models()
        self.assertIs(getattr(npk, "__bit_generator_ctor"), before)
        self.assertIsInstance(np.random.default_rng(1).random(), float)


if __name__ == "__main__":
    unittest.main()
