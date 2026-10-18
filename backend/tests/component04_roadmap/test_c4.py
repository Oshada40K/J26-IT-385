"""Component 04 tests: assessment form API, explainable analysis and C1 integration."""
import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import unquote

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.component01_skill import repository as c1_repository
from app.component04_roadmap import evidence_check, service
from app.component04_roadmap.c4_engine import C_FEATURES
from app.component04_roadmap.router import router

SOFTWARE_DEVELOPERS = "15-1252.00"
REAL_GITHUB_GET = evidence_check._github_get                   # the tests patch it; kept for the HTTP-level test
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
        os.environ.pop("C4_ALLOW_REVIEW", None)               # reviewer endpoint is off by default
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

    def candidate(self, skills, github=None):
        """github: the GitHub username Component 01 found for this student (external_profiles)."""
        session = c1_repository.create_candidate()
        if skills is not None:
            profiles = [{"platform": "github", "handle": github, "url": f"https://github.com/{github}"}] if github else []
            c1_repository.save_assessment(session["candidate_id"], b"cv", {"skills": skills, "external_profiles": profiles})
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
        """Candidate whose CV has Python but no Java, and who rates Java 5/5 (so Java is unverified).
        Component 01 found the GitHub username "student" in the CV."""
        cv = [{"name": "Python", "level": 3, "confidence": "medium"}]
        candidate_id, headers = self.candidate(cv, github="student")
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

    def github_repo(self, languages, name="demo-project", description="", topics=(), owner=None, contributors=(),
                    readme=None, files=(), contents=None, fork=False):
        """Fake GitHub REST API for one repository (no network). owner defaults to the owner in the URL."""
        encoded = lambda text: None if text is None else {"encoding": "base64",
                                                          "content": base64.b64encode(text.encode()).decode()}

        def fake(path):
            self.assertTrue(path.startswith("/repos/"), path)
            parts = path.split("?")[0].split("/")
            login = owner or parts[2]
            rest = "/".join(parts[4:])
            if rest == "":
                return {"name": parts[3], "full_name": f"{login}/{parts[3]}", "owner": {"login": login},
                        "description": description, "size": 250, "topics": list(topics), "default_branch": "main",
                        "fork": fork}
            if rest == "languages":
                return languages
            if rest == "contributors":
                return [{"login": c} for c in contributors]
            if rest == "readme":
                return encoded(readme)
            if rest.startswith("git/trees/"):
                return {"tree": [{"path": p, "type": "blob"} for p in files], "truncated": False}
            if rest.startswith("contents/"):
                return encoded((contents or {}).get(unquote(rest.removeprefix("contents/"))))
            raise AssertionError(f"unexpected GitHub call {path}")
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
        self.assertIn("2/5", body["status_reason"])
        self.assertEqual([(c["check"], c["result"]) for c in body["check_details"]],
                         [("File type and size", "passed"), ("Reviewer check", "not_checked")])
        self.assertFalse(body["can_recheck"])                  # files wait for a reviewer
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
        self.assertIn("No signs of Java", body["status_reason"])
        self.assertEqual(body["check_details"][-1]["result"], "failed")
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
        self.assertEqual(body["status_reason"], evidence_check.REASON_UNREACHABLE)
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

    # ------------------------------------------------------------------ GitHub ownership / skill usage / recheck / review
    # These need only the C4 data files (no trained models): the student has no C4 assessment yet, so "analysis" is None.
    AWS = "SK028"

    def github_student(self):
        return self.candidate([{"name": "Python", "level": 3, "confidence": "medium"}], github="student")

    @staticmethod
    def checks(body):
        return {c["check"]: c["result"] for c in body["check_details"]}

    def test_github_url_is_normalised(self):
        expected = "https://github.com/student/library-app"
        for url in ("https://github.com/student/library-app.git", "https://github.com/student/library-app/",
                    "https://github.com/student/library-app.git/", "https://www.github.com/student/library-app",
                    "https://github.com/student/library-app/tree/main/src", "https://github.com/student/library-app?tab=x",
                    "https://github.com/student/library-app/blob/main/README.md#intro"):
            self.assertEqual(evidence_check.normalize_github_url(url), expected, url)
        for url in ("https://github.com/student", "https://github.com/student/repo/issues/1",
                    "http://github.com/student/repo", "https://github.com.evil.example/student/repo",
                    "https://github.com/student/.git"):
            self.assertIsNone(evidence_check.normalize_github_url(url), url)

        candidate_id, headers = self.github_student()
        self.github_repo({"Java": 4000})
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/library-app.git").json()
        self.assertEqual(body["url"], expected)                                   # stored without ".git"
        self.assertEqual(self.github_get.call_args_list[0].args[0], "/repos/student/library-app")
        self.assertEqual((body["status"], body["provisional_level"]), ("provisional", 3))
        self.assertEqual(self.checks(body)["Owned by or contributed to by you"], "passed")

    def test_wrong_owner_repo_is_rejected(self):
        candidate_id, headers = self.github_student()
        self.github_repo({"Python": 9000}, owner="someone-else", contributors=["someone-else", "helper"],
                         readme="Deploys to AWS Lambda")
        body = self.proof(headers, candidate_id, "github", "https://github.com/someone-else/aws-tools.git",
                          skill_id=self.AWS).json()
        self.assertEqual((body["status"], body["provisional_level"]), ("rejected", None))
        self.assertEqual(body["status_reason"], evidence_check.REASON_NOT_OWNER)
        self.assertEqual(self.checks(body)["Owned by or contributed to by you"], "failed")
        self.assertEqual(self.checks(body)["Shows AWS"], "not_checked")
        self.assertTrue(any("someone-else" in c["detail"] for c in body["check_details"]))

        # Someone else's repository is fine when the student is a contributor (GitHub logins ignore case).
        self.github_repo({"Python": 9000}, owner="team-org", contributors=["team-lead", "Student"],
                         readme="Deploys to AWS Lambda")
        body = self.proof(headers, candidate_id, "github", "https://github.com/team-org/aws-tools",
                          skill_id=self.AWS).json()
        self.assertEqual(body["status"], "provisional")
        self.assertIn("contributors list", body["check_details"][3]["detail"])

        # A fork owned by the student but with no commits from them is not proof.
        self.github_repo({"Python": 9000}, fork=True, contributors=["original-author"], readme="AWS demo")
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/forked-aws",
                          skill_id=self.AWS).json()
        self.assertEqual(body["status_reason"], evidence_check.REASON_NOT_OWNER)

    def test_no_github_username_in_c1_keeps_repo_pending_with_reason(self):
        candidate_id, headers = self.candidate([{"name": "Python", "level": 3, "confidence": "medium"}])
        self.github_repo({"Java": 4000})
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/library-app").json()
        self.assertEqual((body["status"], body["provisional_level"]), ("pending", None))
        self.assertEqual(body["status_reason"], evidence_check.REASON_NO_USERNAME)
        self.assertEqual(self.checks(body)["Owned by or contributed to by you"], "not_checked")
        self.assertEqual(self.checks(body)["Shows Java"], "passed")
        self.assertTrue(body["can_recheck"])

    def test_aws_usage_found(self):
        self.assertEqual(service.engine().name[self.AWS], "AWS")
        candidate_id, headers = self.github_student()
        cases = [  # (fake repository, expected sign)
            (dict(files=["app.py", "requirements.txt"], contents={"requirements.txt": "flask==3.0\nboto3>=1.34\n"}),
             "boto3 in requirements.txt"),
            (dict(files=["handler.js", "serverless.yml"]), "file serverless.yml"),
            (dict(files=["web/package.json"], contents={"web/package.json": '{"dependencies": {"@aws-sdk/client-s3": "3"}}'}),
             "aws-sdk in web/package.json"),
            (dict(files=["src/main.py", ".aws/config"]), "file .aws/config"),
            (dict(readme="# Photo app\nImages are stored on AWS S3."), "'aws' in the README"),
            (dict(topics=["aws", "serverless"]), "'aws' in the name, description and topics"),
        ]
        for repo, sign in cases:
            self.github_repo({"Python": 5000}, **repo)
            body = self.proof(headers, candidate_id, "github", "https://github.com/student/photo-app",
                              skill_id=self.AWS).json()
            self.assertEqual((body["status"], body["provisional_level"]), ("provisional", 3), sign)
            step = body["check_details"][-1]
            self.assertEqual((step["check"], step["result"]), ("Shows AWS", "passed"))
            self.assertIn(sign, step["detail"])

    def test_aws_usage_not_found(self):
        candidate_id, headers = self.github_student()
        self.github_repo({"Python": 5000}, name="todo-app", description="A simple todo list",
                         readme="# Todo\nRun `python app.py`. Uses a lambda to sort items.",
                         files=["app.py", "requirements.txt", "templates/index.html"],
                         contents={"requirements.txt": "flask==3.0\n"})
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/todo-app",
                          skill_id=self.AWS).json()
        self.assertEqual((body["status"], body["provisional_level"]), ("rejected", None))
        self.assertEqual(body["status_reason"], "No signs of AWS were found in this repository.")
        step = body["check_details"][-1]
        self.assertEqual((step["check"], step["result"]), ("Shows AWS", "failed"))
        for looked_at in ("languages", "README", "3 file names", "requirements.txt"):
            self.assertIn(looked_at, step["detail"])

    def test_github_unreachable_is_pending_and_can_be_checked_again(self):
        candidate_id, headers = self.github_student()
        body = self.proof(headers, candidate_id, "github", "https://github.com/student/library-app.git").json()
        self.assertEqual((body["status"], body["provisional_level"]), ("pending", None))   # setUp: GitHub offline
        self.assertEqual(body["status_reason"], "Could not reach GitHub, try again.")
        self.assertEqual(self.checks(body)["Repository found"], "not_checked")
        self.assertTrue(body["can_recheck"])
        recheck = f"/api/roadmap/evidence/{body['evidence_id']}/recheck"

        _, other = self.candidate(None)
        self.assertEqual(self.client.post(recheck).status_code, 401)
        self.assertEqual(self.client.post(recheck, headers=other).status_code, 403)
        self.assertEqual(self.client.post("/api/roadmap/evidence/missing/recheck", headers=headers).status_code, 404)

        self.github_repo({"Java": 4000})                                          # GitHub is back
        again = self.client.post(recheck, headers=headers)
        self.assertEqual(again.status_code, 200, again.text)
        self.assertEqual((again.json()["status"], again.json()["provisional_level"]), ("provisional", 3))
        listed = self.client.get(f"/api/roadmap/evidence/{candidate_id}", headers=headers).json()
        self.assertEqual([(e["evidence_id"], e["status"]) for e in listed], [(body["evidence_id"], "provisional")])

        file = self.proof(headers, candidate_id, "certificate_file", file=("cert.pdf", self.PDF, "application/pdf")).json()
        response = self.client.post(f"/api/roadmap/evidence/{file['evidence_id']}/recheck", headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("reviewer", response.json()["detail"])

    def test_github_rate_limit_and_network_errors_are_unreachable(self):
        limited = Mock(status_code=403, headers={"x-ratelimit-remaining": "0"})
        with patch.object(evidence_check.httpx, "get", return_value=limited) as get:
            with self.assertRaisesRegex(evidence_check.GitHubUnavailable, "rate limit"):
                REAL_GITHUB_GET("/repos/student/app")
        self.assertTrue(get.call_args.kwargs["follow_redirects"])                  # renamed repositories (301)
        with patch.object(evidence_check.httpx, "get", side_effect=evidence_check.httpx.ConnectTimeout("slow")):
            with self.assertRaisesRegex(evidence_check.GitHubUnavailable, "network error"):
                REAL_GITHUB_GET("/repos/student/app")
        with patch.object(evidence_check.httpx, "get", return_value=Mock(status_code=404, headers={})):
            self.assertIsNone(REAL_GITHUB_GET("/repos/student/app"))
        # A failure part-way through (e.g. reading the README) also keeps the proof pending.
        self.github_get.side_effect = lambda path: (
            {"name": "app", "owner": {"login": "student"}, "size": 10} if path == "/repos/student/app"
            else {"Python": 10} if path.endswith("/languages") else (_ for _ in ()).throw(
                evidence_check.GitHubUnavailable("GitHub rate limit reached")))
        result = evidence_check.check_github("https://github.com/student/app", "AWS", ["student"])
        self.assertEqual((result["status"], result["status_reason"]), ("pending", evidence_check.REASON_UNREACHABLE))
        self.assertEqual(result["check_details"][-1], {"check": "Shows AWS", "result": "not_checked",
                                                       "detail": "GitHub rate limit reached. Nothing was decided."})

    def test_certificate_file_counts_as_level_2(self):
        result = evidence_check.check("certificate_file", None, "AWS", file_name="aws.png", file_size=2048)
        self.assertEqual((result["status"], result["provisional_level"]), ("pending", 2))
        item = {"status": "pending", "type": "certificate_file", "proof_type": "certificate_file", "provisional_level": 2}
        self.assertEqual(service._usable_level(item), 2)                         # counts in the roadmap
        self.assertEqual(service._usable_level({**item, "status": "rejected"}), None)

    def test_review_endpoint_is_disabled_by_default(self):
        candidate_id, headers = self.github_student()
        file = self.proof(headers, candidate_id, "certificate_file", file=("aws.pdf", self.PDF, "application/pdf"),
                          skill_id=self.AWS).json()
        review = f"/api/roadmap/evidence/{file['evidence_id']}/review"
        response = self.client.post(review, json={"decision": "approve"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("C4_ALLOW_REVIEW=1", response.json()["detail"])
        self.assertEqual(self.client.get(f"/api/roadmap/evidence/{candidate_id}", headers=headers).json()[0]["status"],
                         "pending")

        with patch.dict(os.environ, {"C4_ALLOW_REVIEW": "1"}):
            self.assertEqual(self.client.post(review, json={"decision": "maybe"}).status_code, 422)
            self.assertEqual(self.client.post(review, json={"decision": "approve", "level": 5}).status_code, 422)
            approved = self.client.post(review, json={"decision": "approve", "note": "Valid AWS certificate"})
            self.assertEqual(approved.status_code, 200, approved.text)
            body = approved.json()
            self.assertEqual((body["status"], body["provisional_level"]), ("provisional", 3))
            self.assertEqual(self.checks(body)["Reviewer check"], "passed")
            self.assertIn("Valid AWS certificate", body["status_reason"])
            self.assertTrue(body["reviewed_at"])
            self.assertEqual(service.evidence_summary(candidate_id)[self.AWS]["source"], "Certificate (reviewer approved)")
            rejected = self.client.post(review, json={"decision": "reject", "note": "Name does not match"}).json()
            self.assertEqual((rejected["status"], rejected["provisional_level"]), ("rejected", None))
            self.assertEqual(self.client.post("/api/roadmap/evidence/missing/review",
                                              json={"decision": "reject"}).status_code, 404)

    @needs_models
    def test_github_proof_updates_the_roadmap_and_rejected_proof_does_not(self):
        cv = [{"name": "Python", "level": 3, "confidence": "medium"}]
        candidate_id, headers = self.candidate(cv, github="student")
        confidence = [{"skill_id": s["skill_id"], "rating": 5 if s["skill_id"] == self.AWS else 2} for s in self.questions(cv)]
        self.client.post("/api/roadmap/assessment", headers=headers, json={**form(confidence), "candidate_id": candidate_id})
        aws = lambda body: next(s for s in body["analysis"]["skill_gaps"]["skills"] if s["skill_id"] == self.AWS)

        self.github_repo({"Python": 100}, owner="other-user", readme="AWS")
        rejected = self.proof(headers, candidate_id, "github", "https://github.com/other-user/aws.git", skill_id=self.AWS).json()
        self.assertEqual((aws(rejected)["status"], aws(rejected)["evidence_status"]), ("unverified", "rejected"))
        self.assertEqual(aws(rejected)["evidence_detail"], evidence_check.REASON_NOT_OWNER)
        self.assertGreater(rejected["analysis"]["roadmap"]["total_steps"], 0)

        self.github_repo({"Python": 100}, files=["serverless.yml"])
        accepted = self.proof(headers, candidate_id, "github", "https://github.com/student/aws", skill_id=self.AWS).json()
        self.assertEqual((aws(accepted)["current_level"], aws(accepted)["evidence_status"]), (3, "provisional"))

    @needs_models
    def test_model_loading_restores_numpy(self):
        import numpy.random._pickle as npk
        before = getattr(npk, "__bit_generator_ctor")
        service.engine().ensure_models()
        self.assertIs(getattr(npk, "__bit_generator_ctor"), before)
        self.assertIsInstance(np.random.default_rng(1).random(), float)


if __name__ == "__main__":
    unittest.main()
