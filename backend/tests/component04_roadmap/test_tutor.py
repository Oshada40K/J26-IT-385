# Owner: Dewmi - Component 04.
"""Adaptive learning tutor: scenarios A-L (service level) plus curriculum and rule checks.

Run from backend/:  .venv\\Scripts\\python -m unittest tests.component04_roadmap.test_tutor -v
Uses a temporary database; Component 01 is replaced by a fake CV profile, and no AI provider is called.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.component04_roadmap import curriculum, learning, lesson_provider, repository, service, tutor
from app.component04_roadmap.errors import LearningError

SOFTWARE_DEVELOPERS = "15-1252.00"
DATA_SCIENTISTS = "15-2051.00"
PF, GIT, PY = "SK001", "SK014", "SK002"
BANK = curriculum.load()


def answers(questions, skill_id, wrong=()):
    """Correct answers taken from the server-side lesson bank, except the question ids in `wrong`."""
    full = {q["id"]: q for t in BANK[skill_id] for q in t["quiz"] + t["diagnostic"]}
    out = {}
    for pq in questions:
        q = full[pq["id"] if isinstance(pq, dict) else pq]
        right = q["id"] not in wrong
        if q["type"] == "single":
            out[q["id"]] = q["answer"] if right else next(i for i in range(len(q["options"])) if i != q["answer"])
        elif q["type"] == "multi":
            out[q["id"]] = q["answer"] if right else [i for i in range(len(q["options"])) if i not in q["answer"]][:1]
        else:
            out[q["id"]] = q["sample_answer"] if right else "no idea"
    return out


def topic(skill_id, topic_id):
    return next(t for t in BANK[skill_id] if t["id"] == topic_id)


class TutorScenarios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"C4_DATABASE_PATH": str(Path(self.temp.name) / "c4.sqlite3"),
                                           "C4_EVIDENCE_DIR": str(Path(self.temp.name) / "evidence")})
        self.env.start()
        for key in ("C4_LLM_API_KEY", "ANTHROPIC_API_KEY", "C4_TUTOR_RULES", "C1_EVIDENCE_ENDPOINT"):
            os.environ.pop(key, None)
        self.cv = {}
        self.c1 = patch.object(service, "c1_profile", side_effect=lambda cid: {
            "candidate_id": cid, "skills": self.cv.get(cid, []), "assessment_id": f"cv-{cid}", "created_at": "2026-10-01"})
        self.c1.start()

    def tearDown(self):
        self.c1.stop()
        self.env.stop()
        self.temp.cleanup()

    def student(self, cid, cv, ratings, career=SOFTWARE_DEVELOPERS, projects=0, methods=("video_tutorials",)):
        self.cv[cid] = cv
        form = {"candidate_id": cid, "career_id": career,
                "confidence": [{"skill_id": s, "rating": r} for s, r in ratings.items()],
                "preferences": {"learning_methods": list(methods), "weekly_hours": "4-6", "weekly_study_hours": 5.0},
                "activity": {"num_projects": projects, "num_certifications": 0, "num_internships": 0}}
        repository.save({"assessment_id": f"a-{cid}", "candidate_id": cid, "career_id": career, "career_name": "",
                         "submitted_at": "2026-10-01T00:00:00+00:00", "previous_assessment_id": None,
                         "c1_assessment_id": f"cv-{cid}", "readiness_score": None, "form": form})
        return repository.get(f"a-{cid}")

    def skill(self, plan, skill_id):
        return next(s for s in plan["skills"] if s["skill_id"] == skill_id)

    def quiz(self, record, cid, skill_id, topic_id, wrong=()):
        lesson = learning.open_activity(record, cid, skill_id, topic_id)
        return learning.submit_attempt(record, cid, skill_id, "quiz", answers(lesson["quiz"], skill_id, wrong), topic_id)

    # A - a beginner starts at the first Beginner topic and gets a supported lesson
    def test_A_beginner_starts_at_the_beginning(self):
        rec = self.student("a", [], {PF: 1, GIT: 1})
        plan = learning.plan(rec, "a")
        self.assertEqual(plan["learner_profile"]["level"], "Novice")
        pf = self.skill(plan, PF)
        self.assertEqual(pf["placement"]["placed_stage"], "Beginner")
        self.assertIsNone(pf["placement"]["checkpoint"])
        self.assertEqual(plan["next_activity"]["topic_id"], "pf-b1")
        lesson = learning.open_activity(rec, "a", PF, "pf-b1")
        self.assertEqual(lesson["mode"], "foundation")                      # novice learners get step-by-step lessons
        part = next(s for s in lesson["sections"] if s["kind"] == "from_zero")
        self.assertFalse(part["collapsed"])                                # explained from zero, open by default
        self.assertTrue(part["text"] and part["items"])

    # B - evidence lets a student skip the basics, confirmed by a checkpoint diagnostic first
    def test_B_evidence_skips_basics_with_checkpoint(self):
        rec = self.student("b", [{"name": "Programming Fundamentals", "level": 3}], {PF: 3})
        pf = self.skill(learning.plan(rec, "b"), PF)
        self.assertEqual(pf["entry_stage"], "Intermediate")
        self.assertEqual(pf["placement"]["checkpoint"], "checkpoint")
        self.assertEqual(pf["next"]["kind"], "diagnostic")
        diag = learning.open_activity(rec, "b", PF, kind="diagnostic")
        self.assertTrue(all(t["stage"] == "Beginner" for t in diag["topics"]))
        out = learning.submit_attempt(rec, "b", PF, "diagnostic", answers(diag["questions"], PF), scope="checkpoint")
        self.assertEqual(out["decision"]["case"], "checkpoint_passed")
        pf = self.skill(out["plan"], PF)
        self.assertIsNone(pf["placement"]["checkpoint"])
        self.assertEqual(pf["next"]["topic_id"], "pf-i1")                   # continues at Intermediate

    # C - a failed checkpoint moves the start back to the weak stage (diagnostic decides, not the CV alone)
    def test_C_failed_checkpoint_lowers_the_start(self):
        rec = self.student("c", [{"name": "Programming Fundamentals", "level": 3}], {PF: 3})
        diag = learning.open_activity(rec, "c", PF, kind="diagnostic")
        out = learning.submit_attempt(rec, "c", PF, "diagnostic",
                                      answers(diag["questions"], PF, wrong=[q["id"] for q in diag["questions"]]),
                                      scope="checkpoint")
        pf = self.skill(out["plan"], PF)
        self.assertEqual(pf["placement"]["placed_stage"], "Beginner")
        self.assertIn(pf["next"]["kind"], ("revision", "lesson"))
        self.assertEqual(pf["next"]["topic_id"], "pf-b1")

    # D - a high quiz score masters the topic and advances
    def test_D_pass_advances(self):
        rec = self.student("d", [], {PF: 2})
        out = self.quiz(rec, "d", PF, "pf-b1")
        self.assertEqual(out["graded"]["score"], 1.0)
        self.assertEqual(out["decision"]["case"], "advance")
        self.assertEqual(repository.topic_progress("d", PF)["pf-b1"]["state"], "mastered")
        self.assertEqual(self.skill(out["plan"], PF)["next"]["topic_id"], "pf-b2")

    # E - a partial score gives targeted practice on the missed concepts
    def test_E_partial_score_targets_missed_concepts(self):
        rec = self.student("e", [], {PF: 2})
        quiz = topic(PF, "pf-b1")["quiz"]
        cut = max(1, round(len(quiz) * 0.34))                               # score between 0.5 and 0.8
        wrong = [q["id"] for q in quiz[:cut]]
        out = self.quiz(rec, "e", PF, "pf-b1", wrong=wrong)
        self.assertGreaterEqual(out["graded"]["score"], 0.5)
        self.assertLess(out["graded"]["score"], 0.8)
        self.assertEqual(out["decision"]["case"], "targeted_practice")
        self.assertTrue(out["decision"]["missed_concepts"])
        lesson = learning.open_activity(rec, "e", PF, "pf-b1")
        self.assertEqual(lesson["mode"], "focused")
        self.assertIn("focus", [s["kind"] for s in lesson["sections"]])

    # F - a low score re-teaches the topic step by step; feedback explains each answer after the attempt
    def test_F_low_score_reteaches_with_feedback(self):
        rec = self.student("f", [], {PF: 2})
        quiz = topic(PF, "pf-b1")["quiz"]
        out = self.quiz(rec, "f", PF, "pf-b1", wrong=[q["id"] for q in quiz])
        self.assertEqual(out["decision"]["case"], "reteach")
        self.assertEqual(out["decision"]["next_mode"], "foundation")
        self.assertTrue(all(r["explanation"] and not r["correct"] for r in out["graded"]["results"]))
        self.assertEqual(learning.open_activity(rec, "f", PF, "pf-b1")["mode"], "foundation")

    # G - repeated low scores on a later topic send the student back to its prerequisite
    def test_G_repeated_failure_goes_to_prerequisite(self):
        rec = self.student("g", [], {PF: 2})
        self.quiz(rec, "g", PF, "pf-b1")
        quiz = topic(PF, "pf-b2")["quiz"]
        all_wrong = [q["id"] for q in quiz]
        self.quiz(rec, "g", PF, "pf-b2", wrong=all_wrong)
        out = self.quiz(rec, "g", PF, "pf-b2", wrong=all_wrong)
        self.assertEqual(out["decision"]["case"], "prerequisite")
        self.assertEqual(out["decision"]["revisit_topic_id"], "pf-b1")
        self.assertTrue(out["decision"]["repeated_mistakes"])              # same concepts missed twice
        self.assertEqual(repository.topic_progress("g", PF)["pf-b1"]["state"], "needs_revision")
        nxt = self.skill(out["plan"], PF)["next"]
        self.assertEqual((nxt["kind"], nxt["topic_id"]), ("revision", "pf-b1"))

    # H - mastering a stage becomes capped C4 evidence: the roadmap regenerates and readiness is recomputed
    def test_H_mastery_regenerates_roadmap_and_readiness(self):
        rec = self.student("h", [], {PF: 1})
        before = learning.plan(rec, "h")
        out = None
        for t in BANK[PF]:
            if t["stage"] == "Beginner":
                out = self.quiz(rec, "h", PF, t["id"])
        self.assertEqual(out["roadmap_update"]["demonstrated_level_after"], 2)
        self.assertTrue(out["roadmap_update"]["changed"])
        gap = next(s for s in out["analysis"]["skill_gaps"]["skills"] if s["skill_id"] == PF)
        self.assertEqual(gap["evidence_source"], service.TUTOR_SOURCE)
        self.assertEqual(gap["current_level"], 2)
        step = next(s for st in out["analysis"]["roadmap"]["stages"] for s in st["steps"] if s["skill_id"] == PF)
        self.assertEqual(step["entry_stage"], "Intermediate")
        self.assertGreaterEqual(out["roadmap_update"]["readiness_after"], before["readiness"]["score"])
        kinds = [e["kind"] for e in repository.learning_events("h")]
        self.assertIn("roadmap_regenerated", kinds)

    # I - the tutor can never add more than the cap (3/5), whatever is mastered
    def test_I_tutor_evidence_is_capped(self):
        with patch.dict(os.environ, {"C4_TUTOR_RULES": json.dumps({"tutor_level_cap": 3})}):
            states = {t["id"]: "mastered" for t in BANK[PF]}
            self.assertEqual(tutor.demonstrated_level(BANK[PF], states, tutor.rules()), 3)
        evidence = {}
        repository.save_skill_learning("i", PF, "2026-10-01", demonstrated_level=5)
        merged = service.merge_tutor_evidence(evidence, "i")
        self.assertEqual(merged[PF]["level"], 3)
        self.assertEqual(merged[PF]["status"], "provisional")
        stronger = service.merge_tutor_evidence({PF: {"status": "verified", "level": 4, "source": "Component 01 (verified)"}}, "i")
        self.assertEqual(stronger[PF]["level"], 4)                         # stronger proof is never replaced

    # Lesson evidence below the CV level adds nothing and shows no "provisionally verified" badge
    def test_lesson_evidence_below_cv_level_is_ignored(self):
        rec = self.student("cv3", [{"name": "Programming Fundamentals", "level": 3}], {PF: 3})
        repository.save_skill_learning("cv3", PF, "2026-10-01", demonstrated_level=2)
        gap = next(s for s in service.analysis(rec)["skill_gaps"]["skills"] if s["skill_id"] == PF)
        self.assertEqual(gap["evidence_status"], "none")
        self.assertEqual(gap["current_level"], 3)

    # Lessons open in order: later topics stay locked until the earlier ones are done (also enforced on the server)
    def test_lessons_are_locked_until_earlier_topics_are_done(self):
        rec = self.student("lk", [{"name": "Programming Fundamentals", "level": 3}], {PF: 3})
        pf = self.skill(learning.plan(rec, "lk"), PF)
        self.assertTrue(all(t["locked"] for t in pf["topics"]))          # checkpoint pending: take the check first
        with self.assertRaises(LearningError) as ctx:
            learning.open_activity(rec, "lk", PF, "pf-a1")
        self.assertEqual(ctx.exception.status_code, 409)
        diag = learning.open_activity(rec, "lk", PF, kind="diagnostic")    # fail the checkpoint -> back to Beginner
        learning.submit_attempt(rec, "lk", PF, "diagnostic",
                                answers(diag["questions"], PF, wrong=[q["id"] for q in diag["questions"]]), scope="checkpoint")
        locks = {t["topic_id"]: t["locked"] for t in self.skill(learning.plan(rec, "lk"), PF)["topics"]}
        self.assertFalse(locks["pf-b1"])
        self.assertTrue(locks["pf-i1"] and locks["pf-a1"])
        for kind, call in (("lesson", lambda: learning.open_activity(rec, "lk", PF, "pf-a1")),
                           ("quiz", lambda: learning.submit_attempt(rec, "lk", PF, "quiz", {}, "pf-i1")),
                           ("test_out", lambda: learning.open_activity(rec, "lk", PF, "pf-i1", "diagnostic", scope="test_out"))):
            with self.assertRaises(LearningError, msg=kind) as ctx:
                call()
            self.assertEqual(ctx.exception.status_code, 409)
        self.quiz(rec, "lk", PF, "pf-b1")                                   # mastered -> stays open for review
        self.assertEqual(learning.open_activity(rec, "lk", PF, "pf-b1")["why_now"], "You are reviewing this topic.")

    # An assessment submitted before the CV upload (no candidate) gets a clear "submit again" message, not "forbidden"
    def test_assessment_without_cv_explains_how_to_unlock_lessons(self):
        rec = self.student("nocv", [], {PF: 2})
        rec = dict(rec, candidate_id=None)
        with self.assertRaises(LearningError) as ctx:
            learning.plan(rec, "nocv")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("Submit the assessment again", str(ctx.exception))

    # J - a claimed skill (rated 5/5, nothing in the CV) is checked before teaching; a confirmed claim is recorded
    def test_J_claimed_skill_gets_a_claim_check(self):
        rec = self.student("j", [], {GIT: 5})
        git = self.skill(learning.plan(rec, "j"), GIT)
        self.assertEqual(git["roadmap_status"], "unverified")
        self.assertEqual(git["placement"]["checkpoint"], "claim")
        diag = learning.open_activity(rec, "j", GIT, kind="diagnostic")
        out = learning.submit_attempt(rec, "j", GIT, "diagnostic", answers(diag["questions"], GIT), scope="claim")
        self.assertEqual(out["decision"]["mismatch"], "supported")
        self.assertEqual(repository.skill_learning("j")[GIT]["checkpoint"], "passed")

    # K - questions never include answers before an attempt, and progress is private
    def test_K_answers_hidden_and_ownership(self):
        rec = self.student("k", [], {PF: 2})
        lesson = learning.open_activity(rec, "k", PF, "pf-b1")
        for q in lesson["quiz"]:
            self.assertFalse({"answer", "explanation", "why_wrong", "sample_answer"} & set(q))
        diag = learning.open_activity(self.student("k2", [{"name": "Programming Fundamentals", "level": 3}], {PF: 3}),
                                      "k2", PF, kind="diagnostic")
        for q in diag["questions"]:
            self.assertNotIn("answer", q)
        with self.assertRaises(LearningError) as ctx:
            learning.plan(rec, "someone-else")
        self.assertEqual(ctx.exception.status_code, 403)
        with self.assertRaises(LearningError) as ctx:
            learning.plan(rec, None)
        self.assertEqual(ctx.exception.status_code, 401)
        with self.assertRaises(LearningError):
            learning.history(rec, "someone-else")

    # L - optional AI: without a key the tutor says so honestly; invalid AI output is rejected, valid output is saved
    def test_L_ai_lessons_are_optional_and_validated(self):
        rec = self.student("l", [], {PF: 2})
        plan = learning.plan(rec, "l")
        self.assertFalse(plan["ai"]["configured"])
        other = next(s for s in plan["skills"] if s["lessons"] is None)
        self.assertEqual(other["status"], "self_study")
        with self.assertRaises(LearningError) as ctx:
            learning.generate_lessons(rec, "l", other["skill_id"])
        self.assertEqual(ctx.exception.status_code, 503)
        with patch.dict(os.environ, {"C4_LLM_API_KEY": "test-key-not-real"}):
            with patch.object(lesson_provider, "call_model", return_value='[{"id": "x", "title": "broken"}]'):
                with self.assertRaises(LearningError):
                    learning.generate_lessons(rec, "l", other["skill_id"])
            valid = [dict(t, id=f"ai-{t['id']}", requires=[f"ai-{r}" for r in t["requires"]],
                          quiz=[dict(q, id=f"ai-{q['id']}") for q in t["quiz"]],
                          diagnostic=[dict(q, id=f"ai-{q['id']}") for q in t["diagnostic"]]) for t in BANK[GIT]]
            with patch.object(lesson_provider, "call_model", return_value=json.dumps(valid)):
                plan = learning.generate_lessons(rec, "l", other["skill_id"])
        self.assertEqual(self.skill(plan, other["skill_id"])["lessons"], "ai")
        lesson = learning.open_activity(rec, "l", other["skill_id"], valid[0]["id"])
        self.assertTrue(lesson["ai_generated"])

    # Practical self-checks are recorded as practice, never as mastery or evidence
    def test_practical_self_check_is_not_evidence(self):
        rec = self.student("p", [], {PF: 2})
        out = learning.submit_attempt(rec, "p", PF, "practical", {"rubric": [0, 1, 2]}, "pf-b1")
        self.assertEqual(out["decision"]["case"], "practical_recorded")
        self.assertNotEqual((repository.topic_progress("p", PF).get("pf-b1") or {}).get("state"), "mastered")
        self.assertEqual(out["roadmap_update"]["demonstrated_level_after"], 0)

    # Opening a lesson is recorded as "learning" but never counts as evidence
    def test_opening_a_lesson_is_not_evidence(self):
        rec = self.student("o", [], {PF: 2})
        learning.open_activity(rec, "o", PF, "pf-b1")
        self.assertEqual(repository.topic_progress("o", PF)["pf-b1"]["state"], "learning")
        self.assertEqual(repository.skill_learning("o"), {})

    # History is preserved when the CV (profile) changes and the roadmap is regenerated
    def test_profile_change_keeps_history(self):
        rec = self.student("x", [], {PF: 2})
        self.quiz(rec, "x", PF, "pf-b1")
        self.cv["x"] = [{"name": "Programming Fundamentals", "level": 4}]  # a new CV in Component 01
        plan = learning.plan(rec, "x")
        self.assertEqual(learning.history(rec, "x")["attempts"][0]["topic_id"], "pf-b1")
        pf = next((s for s in plan["skills"] if s["skill_id"] == PF), None)
        if pf:                                                              # still a gap: now starts higher
            self.assertEqual(pf["entry_stage"], "Advanced")

    # Lessons follow the lecture-notes layout and are arranged by the student's own preferences
    def test_lesson_layout_and_preferences(self):
        rec = self.student("pref", [], {PF: 1}, methods=("video_tutorials", "hands_on_projects"))
        lesson = learning.open_activity(rec, "pref", PF, "pf-b1")
        kinds = [s["kind"] for s in lesson["sections"]]
        for kind in ("main_idea", "from_zero", "key_ideas", "memory_trick", "career_hack", "mistakes", "summary", "recall", "next"):
            self.assertIn(kind, kinds)
        self.assertLess(kinds.index("main_idea"), kinds.index("from_zero"))
        self.assertLess(kinds.index("practical"), kinds.index("practice"))          # hands-on learners: practical first
        self.assertTrue(any("Step-by-step" in n for n in lesson["personalised"]))   # novice profile
        self.assertTrue(any("hands-on" in n for n in lesson["personalised"]))
        if "watch_first" in kinds:                                                  # only when the dataset has a video
            self.assertEqual(kinds[1], "watch_first")
            self.assertTrue(any("Video first" in n for n in lesson["personalised"]))
        self.assertEqual((lesson["topic_number"], lesson["topic_total"]), (1, len(BANK[PF])))
        recall = next(s for s in lesson["sections"] if s["kind"] == "recall")
        self.assertTrue(all(r["q"] and r["a"] for r in recall["recall"]))
        reader = self.student("read", [], {PF: 1}, methods=("reading",))
        kinds = [s["kind"] for s in learning.open_activity(reader, "read", PF, "pf-b1")["sections"]]
        self.assertNotIn("watch_first", kinds)                                       # no video for a reader

    # Career-specific examples: the same topic uses a data example for a data career
    def test_career_specific_examples(self):
        rec = self.student("ds", [], {PY: 2}, career=DATA_SCIENTISTS)
        plan = learning.plan(rec, "ds")
        py = next((s for s in plan["skills"] if s["skill_id"] == PY), None)
        if py is None:
            self.skipTest("Python is not in this career's roadmap")
        lesson = learning.open_activity(rec, "ds", PY, "py-b1")
        career = next(s for s in lesson["sections"] if s["kind"] == "career")
        self.assertEqual(career["text"], topic(PY, "py-b1")["career_examples"]["data"])


class CurriculumAndRules(unittest.TestCase):
    def test_bank_is_valid(self):
        self.assertEqual(set(BANK), {"SK001", "SK002", "SK008", "SK009", "SK010", "SK014"})
        for skill_id, topics in BANK.items():
            curriculum.validate_skill(skill_id, topics)

    def test_broken_topic_is_rejected(self):
        bad = dict(topic(PF, "pf-b1"), quiz=[dict(topic(PF, "pf-b1")["quiz"][0], answer=99)] * 3)
        with self.assertRaises(curriculum.CurriculumError):
            curriculum.validate_topic(bad)

    def test_short_answer_grading_uses_keywords(self):
        q = next(q for t in BANK.values() for tp in t for q in tp["quiz"] if q["type"] == "short")
        self.assertTrue(tutor.grade_question(q, q["sample_answer"])[0])
        self.assertFalse(tutor.grade_question(q, "")[0])

    def test_rules_override_and_bad_json(self):
        with patch.dict(os.environ, {"C4_TUTOR_RULES": '{"mastery_threshold": 0.9, "unknown": 1}'}):
            self.assertEqual(tutor.rules()["mastery_threshold"], 0.9)
            self.assertNotIn("unknown", tutor.rules())
        with patch.dict(os.environ, {"C4_TUTOR_RULES": "not json"}):
            self.assertEqual(tutor.rules(), tutor.DEFAULT_RULES)


if __name__ == "__main__":
    unittest.main()
