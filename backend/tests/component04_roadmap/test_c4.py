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
from app.component04_roadmap import evidence_check, service
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
                                           "SKILL_DATABASE_PATH": str(Path(self.temp.name) / "skills.sqlite3"),
                                           "C4_EVIDENCE_DIR": str(Path(self.temp.name) / "evidence")})
        self.env.start()
        os.environ.pop("C1_EVIDENCE_ENDPOINT", None)          # Component 01 verifier not connected in tests
        os.environ.pop("GITHUB_TOKEN", None)
        # Never call the real GitHub API: by default it is "unreachable" (proof stays pending).
        self.github = patch.object(evidence_check, "_github_get",
                                   side_effect=evidence_check.GitHubUnavailable("offline in tests"))
        self.github_get = self.github.start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.github.stop()
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
            self.assertEqual(skill["status"], "unverified")      # rated 5/5 with no CV evidence
            self.assertNotEqual(skill["severity"], "none")
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

    def analyse_with_ratings(self, cv_skills, ratings, default=2):
        """Submit with a specific rating per skill (default for the rest) and return the analysis."""
        candidate_id, headers = self.candidate(cv_skills)
        confidence = [{"skill_id": s["skill_id"], "rating": ratings.get(s["skill_id"], default)}
                      for s in self.questions(cv_skills)]
        self.assertTrue(set(ratings) <= {c["skill_id"] for c in confidence})
        saved = self.client.post("/api/roadmap/assessment", headers=headers,
                                 json={**form(confidence), "candidate_id": candidate_id})
        self.assertEqual(saved.status_code, 201, saved.text)
        response = self.client.get(f"/api/roadmap/analysis/{saved.json()['assessment_id']}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    @needs_models
    def test_claimed_skill_without_cv_evidence_is_unverified(self):
        cv = [{"name": "Python", "level": 3, "confidence": "medium"}]
        result = self.analyse_with_ratings(cv, {"SK028": 5})          # AWS rated 5/5, not in the CV
        aws = next(s for s in result["skill_gaps"]["skills"] if s["skill_id"] == "SK028")
        self.assertEqual(aws["status"], "unverified")
        self.assertEqual(aws["severity"], "critical")
        self.assertIn("You rated yourself 5/5", aws["message"])
        step = next(s for stage in result["roadmap"]["stages"] for s in stage["steps"] if s["skill_id"] == "SK028")
        self.assertEqual(step["reason"], "verify claimed skill")
        self.assertEqual(step["estimated_hours"], 10)
        self.assertIn(step["resources"][0]["type"], ("project", "certification"))
        self.assertEqual(result["skill_gaps"]["summary"]["unverified"], 1)

        # The engine's own output (c4_engine.run) follows the same rules.
        eng = service.engine()
        eng.ensure_models()
        out = eng.run({"candidate_id": None, "skills": cv}, {},
                      {"career_id": SOFTWARE_DEVELOPERS, "confidence": [{"skill_id": "SK028", "rating": 5}]})
        item = next(s for s in out["skill_gap_report"] if s["skill_id"] == "SK028")
        self.assertEqual((item["status"], item["severity"], item["is_deficient"]), ("unverified", "critical", 1))
        self.assertTrue(item["message"].startswith("You rated yourself 5/5"))
        engine_step = next(s for s in out["roadmap"] if s["skill_id"] == "SK028")
        self.assertEqual((engine_step["reason"], engine_step["estimated_hours"]), ("verify claimed skill", 10))
        self.assertIn(engine_step["resources"][0]["type"], ("project", "certification"))

    @needs_models
    def test_high_cv_level_with_low_rating_is_not_unverified(self):
        result = self.analyse_with_ratings([{"name": "AWS", "level": 5, "confidence": "medium"}], {"SK028": 1})
        aws = next(s for s in result["skill_gaps"]["skills"] if s["skill_id"] == "SK028")
        self.assertNotEqual(aws["status"], "unverified")
        self.assertEqual(aws["severity"], "none")
        self.assertTrue(aws["underconfident"])
        self.assertNotIn("rated yourself", aws["message"])

    @needs_models
    def test_confidence_never_lowers_cv_severity(self):
        cv = [{"name": "JavaScript", "level": 1, "confidence": "low"}]
        low = self.analyse_with_ratings(cv, {"SK004": 1})
        high = self.analyse_with_ratings(cv, {"SK004": 5})
        severity = lambda r: next(s for s in r["skill_gaps"]["skills"] if s["skill_id"] == "SK004")["severity"]
        self.assertEqual(severity(low), severity(high))
        self.assertNotEqual(severity(high), "none")

    # ------------------------------------------------------------------ optional evidence
    STRONG_CV = [{"name": n, "level": l, "confidence": "medium"} for n, l in
                 [("Python", 4), ("React", 2), ("Kubernetes", 2), ("JavaScript", 3), ("Git", 3), ("HTML", 4)]]

    @needs_models
    def test_roadmap_is_generated_without_any_evidence(self):
        result = self.analyse_with_ratings([{"name": "Python", "level": 3, "confidence": "medium"}], {"SK028": 5})
        self.assertGreater(result["roadmap"]["total_steps"], 0)
        self.assertTrue(all(s["evidence_status"] == "none" for s in result["skill_gaps"]["skills"]))
        self.assertTrue(any(s["status"] == "unverified" for s in result["skill_gaps"]["skills"]))

    @needs_models
    def test_unverified_skill_ranks_below_similar_real_gap(self):
        result = self.analyse_with_ratings(self.STRONG_CV, {}, default=5)     # every skill rated 5/5
        priorities = result["priorities"]
        scores = [p["priority_score"] for p in priorities]
        self.assertEqual(scores, sorted(scores, reverse=True))               # re-ranked after the factor
        gaps = [p for p in priorities if p["status"] == "gap"]
        claimed = [p for p in priorities if p["status"] == "unverified"]
        self.assertTrue(gaps and claimed)
        for p in claimed:
            self.assertAlmostEqual(p["priority_score"], p["base_priority_score"] * 0.6, places=3)
        # An unverified skill with a similar (even higher) original score still ranks below the real gap.
        similar = [(g, c) for g in gaps for c in claimed if 0 <= c["base_priority_score"] - g["base_priority_score"] < 0.1]
        self.assertTrue(similar)
        for gap, claim in similar:
            self.assertLess(gap["rank"], claim["rank"])

    @needs_models
    def test_potential_score_uses_claims_but_real_score_ignores_them(self):
        result = self.analyse_with_ratings(self.STRONG_CV, {}, default=5)
        readiness = result["readiness"]
        claimed = {s["skill_id"]: s["skill_name"] for s in result["skill_gaps"]["skills"] if s["status"] == "unverified"}
        self.assertTrue(claimed)
        self.assertIsInstance(readiness["potential_score"], int)
        self.assertGreaterEqual(readiness["potential_score"], round(readiness["score"]) + 1)
        self.assertTrue(set(readiness["potential_skills"]) <= set(claimed.values()))
        # Same student with the claimed self-ratings removed: the real score does not change.
        eng = service.engine()
        cv = {"candidate_id": None, "skills": self.STRONG_CV}
        confidence = [{"skill_id": s["skill_id"], "rating": 5} for s in self.questions(self.STRONG_CV)]
        record = {"career_id": SOFTWARE_DEVELOPERS, "confidence": confidence, "preferences": {},
                  "activity": {"num_projects": 0, "num_certifications": 0, "num_internships": 0}}
        with_claims = eng.analyze_assessment(cv, record)["readiness"]
        without = eng.analyze_assessment(cv, {**record, "confidence": [c for c in confidence if c["skill_id"] not in claimed]})["readiness"]
        self.assertEqual(with_claims["score"], without["score"])
        self.assertNotIn("potential_score", without)

    @needs_models
    def test_evidence_is_pending_then_verified_by_a_higher_cv_level(self):
        cv = [{"name": "Python", "level": 3, "confidence": "medium"}]
        candidate_id, headers = self.candidate(cv)
        confidence = [{"skill_id": s["skill_id"], "rating": 5 if s["skill_id"] == "SK028" else 2} for s in self.questions(cv)]
        saved = self.client.post("/api/roadmap/assessment", headers=headers,
                                 json={**form(confidence), "candidate_id": candidate_id}).json()
        url = f"/api/roadmap/analysis/{saved['assessment_id']}"
        aws = lambda r: next(s for s in r["skill_gaps"]["skills"] if s["skill_id"] == "SK028")

        proof = {"candidate_id": candidate_id, "skill_id": "SK028", "type": "github", "url": "https://github.com/student/aws-demo"}
        self.assertEqual(self.client.post("/api/roadmap/evidence", json=proof).status_code, 401)
        _, other = self.candidate(None)
        self.assertEqual(self.client.post("/api/roadmap/evidence", headers=other, json=proof).status_code, 403)
        response = self.client.post("/api/roadmap/evidence", headers=headers, json=proof)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["status"], "pending")

        pending = self.client.get(url, headers=headers).json()
        self.assertEqual((aws(pending)["evidence_status"], aws(pending)["status"]), ("pending", "unverified"))
        self.assertGreater(pending["roadmap"]["total_steps"], 0)                # pending proof never blocks the roadmap

        # New Component 01 results with a higher AWS level -> verified and regenerated.
        c1_repository.save_assessment(candidate_id, b"cv2", {"skills": cv + [{"name": "AWS", "level": 4, "confidence": "medium"}]})
        update = service.on_c1_assessment_updated(candidate_id)
        self.assertEqual(update["verified_skills"], ["SK028"])
        for result in (update["analysis"], self.client.get(url, headers=headers).json()):
            self.assertEqual(aws(result)["evidence_status"], "verified")
            self.assertNotEqual(aws(result)["status"], "unverified")
            steps = [s for stage in result["roadmap"]["stages"] for s in stage["steps"]]
            self.assertFalse(any(s["skill_id"] == "SK028" and s["status"] == "unverified" for s in steps))

    # ------------------------------------------------------------------ proof upload and provisional checks
    PDF = b"%PDF-1.4\n% test certificate\n"

    def claimed_java(self):
        """Candidate whose CV has Python but no Java, and who rates Java 5/5 (so Java is unverified)."""
        cv = [{"name": "Python", "level": 3, "confidence": "medium"}]
        candidate_id, headers = self.candidate(cv)
        confidence = [{"skill_id": s["skill_id"], "rating": 5 if s["skill_id"] == "SK003" else 2} for s in self.questions(cv)]
        saved = self.client.post("/api/roadmap/assessment", headers=headers,
                                 json={**form(confidence), "candidate_id": candidate_id})
        self.assertEqual(saved.status_code, 201, saved.text)
        return candidate_id, headers, f"/api/roadmap/analysis/{saved.json()['assessment_id']}"

    def proof(self, headers, candidate_id, proof_type, url=None, file=None, skill_id="SK003"):
        data = {"candidate_id": candidate_id, "skill_id": skill_id, "proof_type": proof_type}
        if url:
            data["url"] = url
        return self.client.post("/api/roadmap/evidence", headers=headers, data=data,
                                files={"file": file} if file else None)

    def github_repo(self, languages, name="demo-project", description="", topics=()):
        def fake(path):
            if path.endswith("/languages"):
                return languages
            return {"name": name, "description": description, "size": 250, "topics": list(topics)}
        self.github_get.side_effect = fake

    @staticmethod
    def java(result):
        return next(s for s in result["skill_gaps"]["skills"] if s["skill_id"] == "SK003")

    def test_evidence_rejects_invalid_links(self):
        candidate_id, headers = self.candidate([])
        for proof_type, url, message in [
                ("github", "http://github.com/student/java-app", "https://"),
                ("github", "https://gitlab.com/student/java-app", "GitHub repository link"),
                ("github", "https://github.com/student", "GitHub repository link"),
                ("certificate_link", "http://www.credly.com/badges/1", "https://"),
                ("certificate_link", None, "Enter a link")]:
            response = self.proof(headers, candidate_id, proof_type, url)
            self.assertEqual(response.status_code, 400, (proof_type, url))
            self.assertIn(message, response.json()["detail"])
        response = self.proof(headers, candidate_id, "github", "https://github.com/a/b", skill_id="SK999")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown skill_id", response.json()["detail"])
        self.github_get.assert_not_called()

    def test_evidence_rejects_large_or_wrong_files(self):
        candidate_id, headers = self.candidate([])
        cases = [(("cert.pdf", self.PDF + b"0" * (5 * 1024 * 1024), "application/pdf"), "larger than 5 MB"),
                 (("cert.txt", b"plain text", "text/plain"), "Only PDF, PNG or JPG"),
                 (("cert.pdf", b"\x89PNG\r\n\x1a\nimage", "application/pdf"), "Only PDF, PNG or JPG")]
        for file, message in cases:
            response = self.proof(headers, candidate_id, "certificate_file", file=file)
            self.assertEqual(response.status_code, 400, file[0])
            self.assertIn(message, response.json()["detail"])
        self.assertEqual(self.proof(headers, candidate_id, "certificate_file").status_code, 400)   # no file

    @needs_models
    def test_matching_github_repo_is_provisional_and_regenerates_roadmap(self):
        candidate_id, headers, url = self.claimed_java()
        self.assertEqual(self.java(self.client.get(url, headers=headers).json())["status"], "unverified")
        self.github_repo({"Java": 5400, "HTML": 300})
        response = self.proof(headers, candidate_id, "github", "https://github.com/student/library-app")
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual((body["status"], body["provisional_level"]), ("provisional", 3))
        java = self.java(body["analysis"])                    # regenerated roadmap returned with the evidence
        self.assertNotEqual(java["status"], "unverified")
        self.assertEqual((java["current_level"], java["evidence_status"]), (3, "provisional"))
        self.assertEqual(java["evidence_source"], "GitHub (provisional)")
        steps = [s for stage in body["analysis"]["roadmap"]["stages"] for s in stage["steps"]]
        self.assertFalse(any(s["skill_id"] == "SK003" and s["reason"] == "verify claimed skill" for s in steps))

    @needs_models
    def test_certificate_links_trusted_domain_only(self):
        candidate_id, headers, _ = self.claimed_java()
        trusted = self.proof(headers, candidate_id, "certificate_link", "https://www.credly.com/badges/java-se-11").json()
        self.assertEqual((trusted["status"], trusted["provisional_level"]), ("provisional", 3))
        for link in ("https://my-certificates.example.com/java", "https://www.linkedin.com/in/student"):
            unknown = self.proof(headers, candidate_id, "certificate_link", link).json()
            self.assertEqual((unknown["status"], unknown["provisional_level"]), ("pending", None), link)
        self.github_get.assert_not_called()                    # certificate links are never fetched

    @needs_models
    def test_certificate_file_is_pending_at_level_2(self):
        candidate_id, headers, url = self.claimed_java()
        response = self.proof(headers, candidate_id, "certificate_file", file=("Java Cert.pdf", self.PDF, "application/pdf"))
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual((body["status"], body["provisional_level"], body["file_name"]), ("pending", 2, "Java Cert.pdf"))
        self.assertNotIn("file_path", body)                    # the private path is never returned
        stored = list((Path(self.temp.name) / "evidence").iterdir())
        self.assertEqual([p.read_bytes() for p in stored], [self.PDF])
        java = self.java(body["analysis"])
        self.assertEqual((java["current_level"], java["evidence_source"]), (2, "Certificate (pending review)"))

    @needs_models
    def test_rejected_evidence_does_not_change_proficiency(self):
        candidate_id, headers, url = self.claimed_java()
        before = self.java(self.client.get(url, headers=headers).json())
        self.github_repo({"Python": 9000}, name="data-scripts")
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/data-scripts").json()
        self.assertEqual(body["status"], "rejected")
        self.assertIn("does not show Java", body["check_details"])
        after = self.java(body["analysis"])
        self.assertEqual((after["current_proficiency"], after["status"]), (before["current_proficiency"], "unverified"))
        self.assertEqual(after["evidence_status"], "rejected")

    @needs_models
    def test_provisional_level_is_capped_at_3_despite_self_rating_5(self):
        candidate_id, headers, url = self.claimed_java()
        self.github_repo({"Java": 100})
        self.proof(headers, candidate_id, "github", "https://github.com/student/java-one")
        self.proof(headers, candidate_id, "certificate_link", "https://www.coursera.org/account/accomplishments/verify/X")
        java = self.java(self.client.get(url, headers=headers).json())
        self.assertEqual(java["self_rating"], 5)
        self.assertEqual((java["current_level"], java["current_proficiency"]), (3, 0.6))

    @needs_models
    def test_deleting_evidence_restores_previous_result(self):
        candidate_id, headers, url = self.claimed_java()
        before = self.client.get(url, headers=headers).json()
        self.github_repo({"Java": 100})
        added = self.proof(headers, candidate_id, "github", "https://github.com/student/java-one").json()
        self.assertNotEqual(self.java(added["analysis"])["status"], "unverified")
        listed = self.client.get(f"/api/roadmap/evidence/{candidate_id}", headers=headers).json()
        self.assertEqual([(e["skill_name"], e["status"]) for e in listed], [("Java", "provisional")])
        _, other = self.candidate(None)
        self.assertEqual(self.client.delete(f"/api/roadmap/evidence/{added['evidence_id']}", headers=other).status_code, 403)
        self.assertEqual(self.client.get(f"/api/roadmap/evidence/{candidate_id}", headers=other).status_code, 403)

        deleted = self.client.delete(f"/api/roadmap/evidence/{added['evidence_id']}", headers=headers)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        restored = deleted.json()["analysis"]
        for key in ("current_proficiency", "status", "severity", "evidence_status", "evidence_source"):
            self.assertEqual(self.java(restored)[key], self.java(before)[key], key)
        self.assertEqual(restored["readiness"]["score"], before["readiness"]["score"])
        self.assertEqual(restored["roadmap"]["total_steps"], before["roadmap"]["total_steps"])
        self.assertEqual(self.client.get(f"/api/roadmap/evidence/{candidate_id}", headers=headers).json(), [])

    @needs_models
    def test_github_unavailable_keeps_proof_pending(self):
        candidate_id, headers, _ = self.claimed_java()
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/java-one").json()
        self.assertEqual((body["status"], body["provisional_level"]), ("pending", None))
        self.assertIn("could not be checked", body["check_details"])
        self.assertEqual(self.java(body["analysis"])["status"], "unverified")      # pending link adds no level

    @needs_models
    def test_component01_verifier_sets_verified_level(self):
        candidate_id, headers, _ = self.claimed_java()
        reply = unittest.mock.Mock(status_code=200, json=lambda: {"level": 4}, raise_for_status=lambda: None)
        with patch.dict(os.environ, {"C1_EVIDENCE_ENDPOINT": "https://c1.example/verify"}), \
             patch.object(service.httpx, "post", return_value=reply) as post:
            body = self.proof(headers, candidate_id, "certificate_link", "https://www.credly.com/badges/1").json()
        self.assertEqual(post.call_args.args[0], "https://c1.example/verify")
        self.assertEqual((body["status"], body["verified_level"]), ("verified", 4))
        java = self.java(body["analysis"])
        self.assertEqual((java["current_level"], java["evidence_status"]), (4, "verified"))

    @needs_models
    def test_model_loading_restores_numpy(self):
        import numpy.random._pickle as npk
        before = getattr(npk, "__bit_generator_ctor")
        service.engine().ensure_models()
        self.assertIs(getattr(npk, "__bit_generator_ctor"), before)
        self.assertIsInstance(np.random.default_rng(1).random(), float)


if __name__ == "__main__":
    unittest.main()
