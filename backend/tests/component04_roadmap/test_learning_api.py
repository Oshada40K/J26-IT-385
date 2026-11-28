# Owner: Dewmi - Component 04.
"""HTTP-level tests for the adaptive learning endpoints (/api/roadmap/learning/...): ownership, answers hidden,
attempts saved and the regenerated analysis returned. Needs FastAPI (run from backend/ with the project venv):
    .venv\\Scripts\\python -m unittest tests.component04_roadmap.test_learning_api -v
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.component01_skill import repository as c1_repository
from app.component04_roadmap import curriculum, service
from app.component04_roadmap.router import router

from .c3_stub import StubC03

SOFTWARE_DEVELOPERS = "15-1252.00"
BANK = curriculum.load()
needs_models = unittest.skipUnless(service.engine().models_available(), "trained model files are not present")


@needs_models
class LearningApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"C4_DATABASE_PATH": str(Path(self.temp.name) / "c4.sqlite3"),
                                           "SKILL_DATABASE_PATH": str(Path(self.temp.name) / "skills.sqlite3"),
                                           "C4_EVIDENCE_DIR": str(Path(self.temp.name) / "evidence")})
        self.env.start()
        for key in ("C1_EVIDENCE_ENDPOINT", "C4_LLM_API_KEY", "ANTHROPIC_API_KEY", "C4_TUTOR_RULES"):
            os.environ.pop(key, None)
        self.c3 = StubC03().start()           # Component 03 stub: Software Developers is its #1
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.c3.stop()
        self.env.stop()
        self.temp.cleanup()

    def student(self, skills):
        session = c1_repository.create_candidate()
        c1_repository.save_assessment(session["candidate_id"], b"cv", {"skills": skills, "external_profiles": []})
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        questions = self.client.post("/api/roadmap/assessment/questions", headers=headers,
                                     json={"career_id": SOFTWARE_DEVELOPERS, "c1_skills": skills}).json()["skills"]
        body = {"career_id": SOFTWARE_DEVELOPERS, "confidence": [{"skill_id": q["skill_id"], "rating": 2} for q in questions],
                "preferences": {"learning_methods": ["video_tutorials"], "weekly_hours": "4-6"},
                "experience": {"num_projects": 0, "num_certifications": 0, "num_internships": 0}}
        saved = self.client.post("/api/roadmap/assessment", headers=headers, json=body)
        self.assertEqual(saved.status_code, 201, saved.text)
        return saved.json()["assessment_id"], headers

    def test_plan_lesson_attempt_and_history(self):
        aid, headers = self.student([])
        plan = self.client.get(f"/api/roadmap/learning/{aid}", headers=headers)
        self.assertEqual(plan.status_code, 200, plan.text)
        nxt = plan.json()["next_activity"]
        self.assertEqual(nxt["kind"], "lesson")
        lesson = self.client.get(f"/api/roadmap/learning/{aid}/activity", headers=headers,
                                 params={"skill_id": nxt["skill_id"], "topic_id": nxt["topic_id"]})
        self.assertEqual(lesson.status_code, 200, lesson.text)
        quiz = lesson.json()["quiz"]
        self.assertTrue(quiz and all("answer" not in q for q in quiz))
        full = {q["id"]: q for t in BANK[nxt["skill_id"]] for q in t["quiz"]}
        answers = {q["id"]: (full[q["id"]]["sample_answer"] if q["type"] == "short" else full[q["id"]]["answer"]) for q in quiz}
        attempt = self.client.post(f"/api/roadmap/learning/{aid}/attempts", headers=headers,
                                   json={"skill_id": nxt["skill_id"], "kind": "quiz", "topic_id": nxt["topic_id"],
                                         "answers": answers})
        self.assertEqual(attempt.status_code, 200, attempt.text)
        body = attempt.json()
        self.assertEqual(body["decision"]["case"], "advance")
        self.assertIn("readiness", body["analysis"])
        history = self.client.get(f"/api/roadmap/learning/{aid}/history", headers=headers).json()
        self.assertEqual(history["attempts"][0]["topic_id"], nxt["topic_id"])

    # Interactive exercises: no answers in the lesson, server-side check, practice only, private
    def test_exercise_check_endpoint(self):
        aid, headers = self.student([])
        nxt = self.client.get(f"/api/roadmap/learning/{aid}", headers=headers).json()["next_activity"]
        lesson = self.client.get(f"/api/roadmap/learning/{aid}/activity", headers=headers,
                                 params={"skill_id": nxt["skill_id"], "topic_id": nxt["topic_id"]}).json()
        section = next(s for s in lesson["sections"] if s["kind"] == "exercises")
        full = {e["id"]: e for t in BANK[nxt["skill_id"]] for e in t["exercises"]}
        for pub in section["exercises"]:
            self.assertFalse({"answer", "answers", "explanation", "fix"} & set(pub))
        pub = section["exercises"][0]
        ex = full[pub["id"]]
        right = ex["answers"][0] if ex["type"] == "fill_blank" else ex["lines"] if ex["type"] == "order_steps" else ex["answer"]
        url = f"/api/roadmap/learning/{aid}/exercises/check"
        body = {"skill_id": nxt["skill_id"], "topic_id": nxt["topic_id"], "exercise_id": pub["id"], "answer": right}
        readiness = self.client.get(f"/api/roadmap/analysis/{aid}", headers=headers).json()["readiness"]
        checked = self.client.post(url, headers=headers, json=body)
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertEqual((checked.json()["correct"], checked.json()["attempt_number"]), (True, 1))
        self.assertEqual(checked.json()["explanation"], ex["explanation"])
        self.assertEqual(self.client.get(f"/api/roadmap/analysis/{aid}", headers=headers).json()["readiness"], readiness)
        history = self.client.get(f"/api/roadmap/learning/{aid}/history", headers=headers).json()
        self.assertEqual(history["exercise_attempts"][0]["answers"]["exercise_id"], pub["id"])
        self.assertEqual(history["exercise_summary"]["solved_without_reveal"], 1)
        _, other = self.student([])
        self.assertEqual(self.client.post(url, headers=other, json=body).status_code, 403)
        self.assertEqual(self.client.post(url, headers=headers, json=dict(body, exercise_id="nope")).status_code, 404)
        self.assertEqual(self.client.post(url, headers=headers, json=dict(body, answer=None)).status_code, 400)
        self.assertEqual(self.client.post(url, headers=headers, json=dict(body, answer="x" * 301)).status_code, 422)

    def test_learning_progress_is_private(self):
        aid, _ = self.student([])
        _, other = self.student([])
        self.assertEqual(self.client.get(f"/api/roadmap/learning/{aid}", headers=other).status_code, 403)
        self.assertEqual(self.client.get(f"/api/roadmap/learning/{aid}/history", headers=other).status_code, 403)
        self.assertIn(self.client.get(f"/api/roadmap/learning/{aid}").status_code, (401, 403))

    def test_invalid_requests(self):
        aid, headers = self.student([])
        self.assertEqual(self.client.post(f"/api/roadmap/learning/{aid}/attempts", headers=headers,
                                          json={"skill_id": "SK001", "kind": "quiz"}).status_code, 422)
        self.assertEqual(self.client.get(f"/api/roadmap/learning/{aid}/activity", headers=headers,
                                         params={"skill_id": "SK001", "kind": "nope"}).status_code, 400)
        self.assertEqual(self.client.post(f"/api/roadmap/learning/{aid}/generate/SK015", headers=headers).status_code, 503)
        self.assertEqual(self.client.post(f"/api/roadmap/learning/{aid}/generate/SK004", headers=headers).status_code, 409)


if __name__ == "__main__":
    unittest.main()
