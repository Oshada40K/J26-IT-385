# Owner: Dewmi - Component 04.
"""The target career is decided on the server from Component 03's recommendation (c3_link.py), never chosen by the
student. Component 03 is replaced by a stub (c3_stub.StubC03), so the real C03 model is never run here.
    .venv\\Scripts\\python -m unittest tests.component04_roadmap.test_c3_link -v
"""
import asyncio
import itertools
import json
import os
import random
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.component01_skill import repository as c1_repository
from app.component04_roadmap import c3_link, c4_engine, repository, service
from app.component04_roadmap.c4_engine import NoSupportedCareer, select_career_from_c3
from app.component04_roadmap.router import router

from . import c3_stub
from .c3_stub import (CHIEF_EXECUTIVES, DEFAULT_JOBS, NONE_SUPPORTED, SOFTWARE_DEVELOPERS, STATISTICIANS,
                      SYSTEMS_ANALYSTS, UNSUPPORTED_TOP1, WEB_DEVELOPERS, StubC03)

needs_models = unittest.skipUnless(service.engine().models_available(), "trained model files are not present")
SNAPSHOT_FIELDS = {"onet_version", "model_type", "retrieved_at", "rule", "jobs", "selected_rank", "selected_career_id",
                   "top1_supported", "fallback_used", "fallback_reason"}
RECOMMENDED = "/api/roadmap/assessment/recommended-career"


def answers(skills, career_id=None):
    body = {"confidence": [{"skill_id": s["skill_id"], "rating": 3} for s in skills],
            "preferences": {"learning_methods": ["video_tutorials"], "weekly_hours": "4-6"},
            "experience": {"num_projects": 1, "num_certifications": 0, "num_internships": 0}}
    return {**body, "career_id": career_id} if career_id else body


class C3ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"C4_DATABASE_PATH": str(Path(self.temp.name) / "c4.sqlite3"),
                                           "SKILL_DATABASE_PATH": str(Path(self.temp.name) / "skills.sqlite3"),
                                           "C4_EVIDENCE_DIR": str(Path(self.temp.name) / "evidence")})
        self.env.start()
        os.environ.pop("C1_EVIDENCE_ENDPOINT", None)
        self.c3 = StubC03().start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.c3.stop()
        self.env.stop()
        self.temp.cleanup()

    def candidate(self, skills=()):
        """Signed-in CV candidate; skills=None means signed in but no CV assessment yet."""
        session = c1_repository.create_candidate()
        if skills is not None:
            c1_repository.save_assessment(session["candidate_id"], b"cv", {"skills": list(skills), "external_profiles": []})
        return session["candidate_id"], {"Authorization": f"Bearer {session['access_token']}"}

    def questions(self, headers, **body):
        return self.client.post("/api/roadmap/assessment/questions", headers=headers, json={"c1_skills": [], **body})

    def submit(self, headers, career_id=None):
        skills = self.questions(headers).json()["skills"]
        return self.client.post("/api/roadmap/assessment", headers=headers, json=answers(skills, career_id))

    # (a) top5_supported: C3's #1 when C4 supports it
    def test_a_picks_c3_top1_when_supported(self):
        cid, headers = self.candidate()
        response = self.client.get(RECOMMENDED, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual((body["career_id"], body["career_name"]), SOFTWARE_DEVELOPERS)
        self.assertEqual((body["c3_rank"], body["c3_score"], body["rule"]), (1, 80.0, "top5_supported"))
        self.assertFalse(body["fallback_used"])
        self.assertIsNone(body["fallback_reason"])
        self.assertTrue(body["top1_supported"])
        self.assertEqual([j["rank"] for j in body["jobs"]], [1, 2, 3, 4, 5])
        self.assertEqual([j["selected"] for j in body["jobs"]], [True, False, False, False, False])
        # C03 was called once, for the signed-in owner, with the student's own token forwarded.
        self.assertEqual(self.c3.calls, [{"candidate_id": cid, "authorization": headers["Authorization"]}])
        self.assertEqual(self.questions(headers).json()["career_id"], SOFTWARE_DEVELOPERS[0])

    # (b) top5_supported: next supported job when C3's #1 is outside C4, with the fallback recorded
    def test_b_falls_back_to_next_supported_and_records_it(self):
        self.c3.jobs = UNSUPPORTED_TOP1                          # #1 Chief Executives, #2 Web Developers
        _, headers = self.candidate()
        body = self.client.get(RECOMMENDED, headers=headers).json()
        self.assertEqual((body["career_id"], body["c3_rank"]), (WEB_DEVELOPERS[0], 2))
        self.assertTrue(body["fallback_used"])
        self.assertFalse(body["top1_supported"])
        self.assertEqual((body["c3_top1"]["job_title"], body["c3_top1"]["supported"]), (CHIEF_EXECUTIVES[1], False))
        self.assertEqual(body["fallback_reason"], "C3's top job 'Chief Executives' is outside C4's IT occupations; "
                                                  "using 'Web Developers'")
        self.assertEqual(self.questions(headers).json()["career_id"], WEB_DEVELOPERS[0])

    # (c) strict_top1: no roadmap when C3's #1 is outside C4
    def test_c_strict_top1_refuses_when_top1_unsupported(self):
        self.c3.jobs = UNSUPPORTED_TOP1
        _, headers = self.candidate()
        with patch.object(c4_engine, "C3_CAREER_RULE", "strict_top1"):
            response = self.client.get(RECOMMENDED, headers=headers)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertIn("strict_top1", response.json()["detail"])
            self.assertEqual(self.questions(headers).status_code, 422)
            submitted = self.client.post("/api/roadmap/assessment", headers=headers, json=answers([{"skill_id": "SK001"}]))
            self.assertEqual(submitted.status_code, 422)
            self.c3.jobs = DEFAULT_JOBS                          # supported #1 -> allowed under strict_top1
            body = self.client.get(RECOMMENDED, headers=headers).json()
            self.assertEqual((body["career_id"], body["rule"]), (SOFTWARE_DEVELOPERS[0], "strict_top1"))
        self.assertIsNone(repository.latest_for(self.c3.calls[0]["candidate_id"]))

    # (d) none of C3's 5 jobs supported: clear error, nothing saved
    def test_d_no_supported_career_is_a_clear_error_and_nothing_is_saved(self):
        self.c3.jobs = NONE_SUPPORTED
        cid, headers = self.candidate()
        response = self.client.get(RECOMMENDED, headers=headers)
        self.assertEqual(response.status_code, 422)
        self.assertIn("None of Component 3's careers is supported", response.json()["detail"])
        self.assertIn("#1 Chief Executives", response.json()["detail"])
        self.assertEqual(self.questions(headers).status_code, 422)
        body = answers([{"skill_id": "SK001"}])
        self.assertEqual(self.client.post("/api/roadmap/assessment", headers=headers, json=body).status_code, 422)
        self.assertIsNone(repository.latest_for(cid))

    # (e) C03 unavailable: 503 (504 for a timeout), never a fallback to a manual choice
    def test_e_c03_unavailable_is_503_and_timeout_is_504(self):
        cid, headers = self.candidate()
        body = answers([{"skill_id": "SK001"}], SOFTWARE_DEVELOPERS[0])   # even a career in the body is not used
        for error, status in ((HTTPException(502, "Upstream profile API returned HTTP 404"), 503),
                              (HTTPException(500, "Career inference failed"), 503),
                              (AttributeError("'State' object has no attribute 'career_client'"), 503),
                              (HTTPException(504, "Upstream profile API timed out"), 504)):
            self.c3.error = error
            for response in (self.client.get(RECOMMENDED, headers=headers), self.questions(headers),
                             self.client.post("/api/roadmap/assessment", headers=headers, json=body)):
                self.assertEqual(response.status_code, status, (error, response.text))
                self.assertIn("Component 03", response.json()["detail"])
        self.assertIsNone(repository.latest_for(cid))

        async def slow(request, candidate_id):
            await asyncio.sleep(1)
        with patch.object(c3_link, "_call_c03", slow), patch.object(c3_link, "C3_TIMEOUT_SECONDS", 0.05):
            response = self.client.get(RECOMMENDED, headers=headers)
        self.assertEqual(response.status_code, 504)
        self.assertIn("did not answer", response.json()["detail"])

    # (f) no signed-in candidate (or no CV yet): refused before C03 is called, so C03's sample data is never used
    def test_f_no_candidate_is_refused_and_c03_is_never_called(self):
        body = answers([{"skill_id": "SK001"}])
        for response in (self.client.get(RECOMMENDED), self.questions({}),
                         self.client.post("/api/roadmap/assessment", json=body)):
            self.assertEqual(response.status_code, 401, response.text)
            self.assertIn("Component 01", response.json()["detail"])
        expired = {"Authorization": "Bearer not-a-real-token"}
        self.assertEqual(self.client.get(RECOMMENDED, headers=expired).status_code, 401)
        _, no_cv = self.candidate(None)
        for response in (self.client.get(RECOMMENDED, headers=no_cv), self.questions(no_cv)):
            self.assertEqual(response.status_code, 409, response.text)
            self.assertIn("No CV assessment", response.json()["detail"])
        self.assertEqual(self.c3.calls, [])                      # never called, so never with candidate_id=None

    def test_c3_link_itself_refuses_a_missing_candidate(self):
        with self.assertRaises(c3_link.C3LinkError) as ctx:
            asyncio.run(c3_link.c3_recommendation(None, None))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(self.c3.calls, [])

    # (g) a different career in the body is rejected (not silently switched); the same career is accepted
    def test_g_body_career_different_from_c3_is_409(self):
        cid, headers = self.candidate()
        response = self.submit(headers, career_id=WEB_DEVELOPERS[0])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("Software Developers", response.json()["detail"])
        self.assertIsNone(repository.latest_for(cid))
        self.assertEqual(self.questions(headers, career_id=WEB_DEVELOPERS[0]).status_code, 409)
        self.assertEqual(self.questions(headers, career_name="web developers").status_code, 409)
        self.assertEqual(self.questions(headers, career_name="Astronaut").status_code, 404)   # unknown to C4
        self.assertEqual(self.submit(headers, career_id=SOFTWARE_DEVELOPERS[0]).status_code, 201)
        self.assertEqual(self.submit(headers).status_code, 201)

    # (h) the C3 snapshot is saved with the assessment and appears in the analysis
    def test_h_snapshot_is_saved_with_every_field(self):
        self.c3.jobs = UNSUPPORTED_TOP1
        self.c3.scores = [91.5, 88.25, 70.0, 65.1, 60.0]
        cid, headers = self.candidate()
        saved = self.submit(headers)
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual((saved.json()["career_source"], saved.json()["career_id"]), ("c3", WEB_DEVELOPERS[0]))
        record = self.client.get(f"/api/roadmap/assessment/{saved.json()['assessment_id']}", headers=headers).json()
        snap = record["c3_snapshot"]
        self.assertEqual(set(snap), SNAPSHOT_FIELDS)
        self.assertEqual((snap["onet_version"], snap["rule"]), ("30.0", "top5_supported"))
        self.assertTrue(snap["model_type"].startswith("XGBRegressor"))
        self.assertTrue(snap["retrieved_at"].endswith("+00:00"))
        self.assertEqual(snap["jobs"], [{"rank": i + 1, "onet_soc_code": c, "job_title": t, "score": s}
                                        for i, ((c, t), s) in enumerate(zip(UNSUPPORTED_TOP1, self.c3.scores))])
        self.assertEqual((snap["selected_rank"], snap["selected_career_id"]), (2, WEB_DEVELOPERS[0]))
        self.assertEqual((snap["top1_supported"], snap["fallback_used"]), (False, True))
        self.assertIn("Chief Executives", snap["fallback_reason"])
        self.assertEqual(record["form"]["career_id"], WEB_DEVELOPERS[0])
        # Stored as JSON in its own column, in exactly this shape (the c3_json shape is built only for the engine).
        with closing(sqlite3.connect(os.environ["C4_DATABASE_PATH"])) as db, db:
            stored = db.execute("SELECT career_source, c3_snapshot_json FROM c4_assessments").fetchone()
        self.assertEqual((stored[0], json.loads(stored[1])), ("c3", snap))

    @needs_models
    def test_h_snapshot_reaches_the_analysis(self):
        self.c3.jobs = UNSUPPORTED_TOP1
        _, headers = self.candidate([{"name": "JavaScript", "level": 2, "confidence": "medium"}])
        saved = self.submit(headers).json()
        result = self.client.get(f"/api/roadmap/analysis/{saved['assessment_id']}", headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        result = result.json()
        self.assertEqual(result["target_career"], {"career_id": WEB_DEVELOPERS[0], "career_name": WEB_DEVELOPERS[1]})
        self.assertEqual(result["career_source"], "c3")
        c3 = result["c3_recommendation"]
        self.assertEqual((c3["career_id"], c3["c3_rank"], c3["c3_score"]), (WEB_DEVELOPERS[0], 2, 76.5))
        self.assertEqual((c3["c3_top1"]["job_title"], c3["fallback_used"]), ("Chief Executives", True))
        self.assertIn("C3's top job 'Chief Executives' is outside C4's IT occupations; using 'Web Developers'",
                      result["warnings"])
        # The analysis uses the stored snapshot: a later C03 change does not change this roadmap.
        self.c3.jobs = DEFAULT_JOBS
        again = self.client.get(f"/api/roadmap/analysis/{saved['assessment_id']}", headers=headers).json()
        self.assertEqual(again["target_career"]["career_id"], WEB_DEVELOPERS[0])
        self.assertEqual(again["c3_recommendation"], c3)

    # (i) legacy assessments (saved before the career came from C03) still load
    def write_legacy(self, cid):
        form = {"candidate_id": cid, "career_id": SYSTEMS_ANALYSTS[0], "confidence": [],
                "preferences": {"learning_methods": ["reading"], "weekly_hours": "4-6", "weekly_study_hours": 5.0},
                "activity": {"num_projects": 0, "num_certifications": 0, "num_internships": 0}}
        # The table as it was before this change (no career_source / c3_snapshot_json columns).
        with closing(sqlite3.connect(os.environ["C4_DATABASE_PATH"])) as db, db:
            db.execute("""CREATE TABLE c4_assessments (id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id TEXT UNIQUE NOT NULL, candidate_id TEXT, career_id TEXT NOT NULL,
                career_name TEXT NOT NULL, submitted_at TEXT NOT NULL, previous_assessment_id TEXT,
                c1_assessment_id TEXT, readiness_score REAL, form_json TEXT NOT NULL)""")
            db.execute("INSERT INTO c4_assessments (assessment_id, candidate_id, career_id, career_name, submitted_at, "
                       "form_json) VALUES (?,?,?,?,?,?)", ("legacy-1", cid, SYSTEMS_ANALYSTS[0], SYSTEMS_ANALYSTS[1],
                                                           "2026-09-01T00:00:00+00:00", json.dumps(form)))
        return "legacy-1"

    def test_i_legacy_record_loads_as_student_selected_legacy(self):
        cid, headers = self.candidate()
        aid = self.write_legacy(cid)
        record = self.client.get(f"/api/roadmap/assessment/{aid}", headers=headers)
        self.assertEqual(record.status_code, 200, record.text)
        self.assertEqual((record.json()["career_source"], record.json()["c3_snapshot"]), ("student_selected_legacy", None))
        self.assertEqual(record.json()["career_id"], SYSTEMS_ANALYSTS[0])          # never rewritten
        latest = self.client.get("/api/roadmap/assessment/latest", headers=headers).json()
        self.assertEqual(latest["career_source"], "student_selected_legacy")

    @needs_models
    def test_i_legacy_record_analysis_is_200(self):
        cid, headers = self.candidate()
        aid = self.write_legacy(cid)
        result = self.client.get(f"/api/roadmap/analysis/{aid}", headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["career_source"], "student_selected_legacy")
        self.assertIsNone(result.json()["c3_recommendation"])
        self.assertEqual(result.json()["target_career"]["career_id"], SYSTEMS_ANALYSTS[0])
        self.assertEqual(result.json()["assessment"]["history"][0]["career_source"], "student_selected_legacy")
        self.assertEqual(self.c3.calls, [])                      # the analysis never calls C03

    # (j) career-check reports a changed C03 selection and never changes the assessment
    def test_j_career_check_reports_change(self):
        cid, headers = self.candidate()
        aid = self.submit(headers).json()["assessment_id"]
        url = f"/api/roadmap/assessment/{aid}/career-check"
        check = self.client.get(url, headers=headers)
        self.assertEqual(check.status_code, 200, check.text)
        self.assertEqual((check.json()["changed"], check.json()["legacy"]), (False, False))
        self.assertEqual(check.json()["saved"]["c3_rank"], 1)
        self.c3.jobs = [WEB_DEVELOPERS, SOFTWARE_DEVELOPERS, *DEFAULT_JOBS[2:]]   # e.g. after a new CV
        check = self.client.get(url, headers=headers).json()
        self.assertTrue(check["changed"])
        self.assertEqual((check["current"]["career_id"], check["saved"]["career_id"]),
                         (WEB_DEVELOPERS[0], SOFTWARE_DEVELOPERS[0]))
        self.assertIn("Web Developers", check["message"])
        self.assertEqual(repository.get(aid)["career_id"], SOFTWARE_DEVELOPERS[0])   # nothing changed automatically
        _, other = self.candidate()
        self.assertEqual(self.client.get(url, headers=other).status_code, 403)

    def test_j_career_check_for_legacy_record(self):
        cid, headers = self.candidate()
        aid = self.write_legacy(cid)
        check = self.client.get(f"/api/roadmap/assessment/{aid}/career-check", headers=headers).json()
        self.assertTrue(check["legacy"])
        self.assertTrue(check["changed"])                         # chose Systems Analysts; C03 #1 is Software Dev.
        self.assertEqual((check["saved"]["career_source"], check["saved"]["c3_rank"]), ("student_selected_legacy", None))


class SelectionRuleTests(unittest.TestCase):
    """(k) the single selection rule: select_career_from_c3 and c4_engine.student_from_json agree."""

    @classmethod
    def setUpClass(cls):
        cls.eng = service.engine()
        cls.supported = cls.eng.req_by_career

    def jobs(self, pairs):
        return [{"rank": i + 1, "onet_soc_code": c, "job_title": t, "score": 50 - i} for i, (c, t) in enumerate(pairs)]

    def via_engine(self, pairs, rule, key="onet_soc_code"):
        jobs = [{"ranking": i + 1, "job": t, "score": 50 - i, **({key: c} if key else {})} for i, (c, t) in enumerate(pairs)]
        st = self.eng.student_from_json({"candidate_id": "x", "skills": []},
                                        {"top_jobs": {"candidate_id": "x", "jobs": jobs}}, {}, None, rule=rule)
        return st["career_id"], [w for w in st["warnings"] if w.startswith("C3's top job")]

    def test_k_pure_rule_and_engine_agree(self):
        pool = [SOFTWARE_DEVELOPERS, WEB_DEVELOPERS, SYSTEMS_ANALYSTS, CHIEF_EXECUTIVES, STATISTICIANS,
                *c3_stub.NONE_SUPPORTED[1:]]
        cases = list(itertools.permutations(pool[:5], 5))[:60] + [random.Random(seed).sample(pool, 5) for seed in range(60)]
        checked = 0
        for pairs, rule, key in itertools.product(cases, c4_engine.C3_CAREER_RULES, ("onet_soc_code", "onet_code", None)):
            try:
                pure = select_career_from_c3(self.jobs(pairs), self.supported, rule)
                expected = (pure["career_id"], [pure["fallback_reason"]] if pure["fallback_used"] else [])
            except NoSupportedCareer as exc:
                expected = ("error", str(exc))
            try:
                got = self.via_engine(pairs, rule, key)
            except NoSupportedCareer as exc:
                got = ("error", str(exc))
            self.assertEqual(got, expected, (pairs, rule, key))
            checked += 1
        self.assertEqual(checked, 120 * 2 * 3)

    def test_k_rules_on_fixed_inputs(self):
        top5 = select_career_from_c3(self.jobs(UNSUPPORTED_TOP1), self.supported, "top5_supported")
        self.assertEqual((top5["career_id"], top5["rank"], top5["fallback_used"]), (WEB_DEVELOPERS[0], 2, True))
        with self.assertRaises(NoSupportedCareer):
            select_career_from_c3(self.jobs(UNSUPPORTED_TOP1), self.supported, "strict_top1")
        with self.assertRaises(NoSupportedCareer):
            select_career_from_c3(self.jobs(NONE_SUPPORTED), self.supported, "top5_supported")
        with self.assertRaises(ValueError):
            select_career_from_c3(self.jobs(DEFAULT_JOBS), self.supported, "student_choice")
        # Ranks are respected even when C03's list arrives out of order.
        shuffled = list(reversed(self.jobs(UNSUPPORTED_TOP1)))
        self.assertEqual(select_career_from_c3(shuffled, self.supported)["career_id"], WEB_DEVELOPERS[0])

    def test_title_only_c3_json_gives_the_same_result_as_before(self):
        """The training notebook's c3_json has titles only (no codes): matched by the normalised title, with the
        same career, options and warning text as before this change."""
        c3 = {"top_jobs": {"candidate_id": "x", "jobs": [
            {"ranking": 3, "job": "Web Developers", "score": 40},
            {"ranking": 1, "job": "Chief Executives", "score": 60},
            {"ranking": 2, "job": "  software   DEVELOPERS ", "score": 50}]}}
        st = self.eng.student_from_json({"candidate_id": "x", "skills": []}, c3)
        self.assertEqual(st["career_id"], SOFTWARE_DEVELOPERS[0])
        self.assertEqual(st["career_options"], [
            {"rank": 1, "career_name": "Chief Executives", "career_id": None, "c3_score": 60, "supported": False},
            {"rank": 2, "career_name": "  software   DEVELOPERS ", "career_id": SOFTWARE_DEVELOPERS[0], "c3_score": 50,
             "supported": True},
            {"rank": 3, "career_name": "Web Developers", "career_id": WEB_DEVELOPERS[0], "c3_score": 40, "supported": True}])
        self.assertIn("C3's top job 'Chief Executives' is outside C4's IT occupations; using '  software   DEVELOPERS '",
                      st["warnings"])
        # Explicit career (form or argument) still wins and adds no C3 warning, exactly as before.
        st = self.eng.student_from_json({"candidate_id": "x", "skills": []}, c3, {"career_id": WEB_DEVELOPERS[0]})
        self.assertEqual(st["career_id"], WEB_DEVELOPERS[0])
        self.assertFalse(any(w.startswith("C3's top job") for w in st["warnings"]))
        with self.assertRaisesRegex(ValueError, "None of Component 3's careers is supported by Component 4"):
            self.eng.student_from_json({"candidate_id": "x", "skills": []},
                                       {"top_jobs": {"jobs": [{"ranking": 1, "job": "Chief Executives"}]}})
        # Code first, then onet_code, then title: a code wins over a misleading title.
        jobs = [{"rank": 1, "onet_soc_code": WEB_DEVELOPERS[0], "onet_code": SYSTEMS_ANALYSTS[0], "job_title": "Software Developers"}]
        self.assertEqual(select_career_from_c3(jobs, self.supported, title_to_code=self.eng.title_to_code)["career_id"],
                         WEB_DEVELOPERS[0])
        jobs = [{"rank": 1, "onet_code": SYSTEMS_ANALYSTS[0], "job_title": "Software Developers"}]
        self.assertEqual(select_career_from_c3(jobs, self.supported, title_to_code=self.eng.title_to_code)["career_id"],
                         SYSTEMS_ANALYSTS[0])

    def test_snapshot_converts_to_c3_json_only_for_the_engine(self):
        rec = {"onet_version": "30.0", "model_type": "m", "jobs": self.jobs(UNSUPPORTED_TOP1)}
        selection, snap = c3_link.snapshot_from(rec, self.supported)
        self.assertEqual(set(snap), SNAPSHOT_FIELDS)
        c3_json = c3_link.snapshot_to_c3_json(snap, "x")
        st = self.eng.student_from_json({"candidate_id": "x", "skills": []}, c3_json, {}, snap["selected_career_id"],
                                        rule=snap["rule"], career_from_c3=True)
        self.assertEqual(st["career_id"], selection["career_id"])
        self.assertIn(snap["fallback_reason"], st["warnings"])


if __name__ == "__main__":
    unittest.main()
