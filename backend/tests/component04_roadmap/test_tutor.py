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
                          diagnostic=[dict(q, id=f"ai-{q['id']}") for q in t["diagnostic"]],
                          exercises=[dict(e, id=f"ai-{e['id']}") for e in t["exercises"]]) for t in BANK[GIT]]
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

    # A student who prefers video gets the curated video first, instead of the dataset video
    def test_curated_video_first_for_video_learners(self):
        rec = self.student("vid", [], {PF: 1}, methods=("video_tutorials",))
        lesson = learning.open_activity(rec, "vid", PF, "pf-b1")
        kinds = [s["kind"] for s in lesson["sections"]]
        expected = topic(PF, "pf-b1")["video"]
        self.assertEqual(kinds[:2], ["objective", "video"])
        self.assertEqual(kinds.count("video"), 1)
        self.assertNotIn("watch_first", kinds)
        self.assertEqual(lesson["sections"][1]["video"], expected)
        self.assertEqual(lesson["sections"][1]["title"], f"Watch first: {expected['title']}")
        self.assertIn("Video first: you prefer video tutorials.", lesson["personalised"])

    # A student who does not prefer video still sees it, right after "How it works" (optional)
    def test_curated_video_after_explanation_for_other_learners(self):
        rec = self.student("rd", [], {PF: 1}, methods=("reading",))
        lesson = learning.open_activity(rec, "rd", PF, "pf-b1")
        kinds = [s["kind"] for s in lesson["sections"]]
        expected = topic(PF, "pf-b1")["video"]
        self.assertEqual(kinds.index("video"), kinds.index("explanation") + 1)
        section = lesson["sections"][kinds.index("video")]
        self.assertEqual(section["title"], f"Watch: {expected['title']}")
        self.assertEqual(section["note"], f"Video from YouTube ({expected['channel']}), chosen by the lesson author. Not produced by CareerNova.")
        self.assertNotIn("watch_first", kinds)
        self.assertFalse(any("Video first" in n for n in lesson["personalised"]))

    # A topic without a curated video keeps the dataset "Watch first" behaviour
    def test_dataset_video_only_without_a_curated_video(self):
        rec = self.student("ds-vid", [], {PF: 1}, methods=("video_tutorials",))
        no_videos = {skill: [{k: v for k, v in t.items() if k != "video"} for t in topics] for skill, topics in BANK.items()}
        dataset_video = dict(title="Dataset video", type="video", level="Beginner", url="https://example.com/v")
        with patch.object(learning, "bank", return_value=no_videos), \
                patch.object(service.engine(), "recommend_resources", return_value=[dataset_video]):
            lesson = learning.open_activity(rec, "ds-vid", PF, "pf-b1")
        kinds = [s["kind"] for s in lesson["sections"]]
        self.assertEqual(kinds[:2], ["objective", "watch_first"])
        self.assertNotIn("video", kinds)
        self.assertIn("Video first: you prefer video tutorials.", lesson["personalised"])

    # ---------------------------------------------------------------- interactive exercises (practice only)
    INTERACTIVE_NOTE = "Interactive practice first: you prefer interactive coding exercises."

    def lesson_kinds(self, cid, methods, topic_id="pf-b1"):
        rec = self.student(cid, [], {PF: 1}, methods=methods)
        lesson = learning.open_activity(rec, cid, PF, topic_id)
        return rec, lesson, [s["kind"] for s in lesson["sections"]]

    # A student who chose interactive exercises gets them right after "How it works", with their own note
    def test_interactive_learner_gets_exercises_after_how_it_works(self):
        _, lesson, kinds = self.lesson_kinds("ix", ("interactive_exercises",))
        self.assertEqual(kinds.count("exercises"), 1)
        self.assertEqual(kinds.index("exercises"), kinds.index("explanation") + 1)
        self.assertIn(self.INTERACTIVE_NOTE, lesson["personalised"])
        self.assertFalse(any("hands-on" in n for n in lesson["personalised"]))     # no longer treated as hands-on
        self.assertLess(kinds.index("practice"), kinds.index("practical"))           # practical task not moved first
        section = lesson["sections"][kinds.index("exercises")]
        self.assertEqual(section["title"], "Practice: interactive exercises")
        self.assertEqual([e["id"] for e in section["exercises"]], [e["id"] for e in topic(PF, "pf-b1")["exercises"]])

    # Without that preference the exercises follow the worked example and the note is absent
    def test_other_learners_get_exercises_after_the_worked_example(self):
        hands_on_note = "Practical task first: you prefer hands-on learning."
        for cid, methods in (("rx", ("reading",)), ("hx", ("hands_on_projects",)), ("vx", ("video_tutorials",))):
            _, lesson, kinds = self.lesson_kinds(cid, methods)
            self.assertEqual(kinds.index("exercises"), kinds.index("worked_example") + 1, methods)
            self.assertNotIn(self.INTERACTIVE_NOTE, lesson["personalised"])
            hands_on = methods == ("hands_on_projects",)                 # the hands-on rule is kept for hands-on only
            self.assertEqual(hands_on_note in lesson["personalised"], hands_on, methods)
            self.assertEqual(kinds.index("practical") < kinds.index("practice"), hands_on, methods)

    # Dewmi's own case: video tutorials AND interactive exercises
    def test_video_and_interactive_learner(self):
        _, lesson, kinds = self.lesson_kinds("vix", ("video_tutorials", "interactive_exercises"))
        self.assertEqual(kinds[:2], ["objective", "video"])                          # curated video first
        self.assertEqual(kinds.index("exercises"), kinds.index("explanation") + 1)   # exercises right after "How it works"
        self.assertIn("Video first: you prefer video tutorials.", lesson["personalised"])
        self.assertIn(self.INTERACTIVE_NOTE, lesson["personalised"])
        self.assertFalse(any("hands-on" in n for n in lesson["personalised"]))
        self.assertEqual(kinds.count("video"), 1)
        self.assertEqual(kinds.count("exercises"), 1)

    # interactive_exercises plus reading: the reading still comes after "How it works", the exercises come first
    def test_interactive_and_reading_learner(self):
        docs = dict(title="Docs", type="documentation", level="Beginner", url="https://example.com/d")
        rec = self.student("irx", [], {PF: 1}, methods=("reading", "interactive_exercises"))
        with patch.object(service.engine(), "recommend_resources", return_value=[docs]):
            kinds = [s["kind"] for s in learning.open_activity(rec, "irx", PF, "pf-b1")["sections"]]
        at = kinds.index("explanation")
        self.assertEqual(kinds[at + 1], "exercises")
        self.assertIn("read_more", kinds)

    # Answers, explanations and fixed lines are never sent with the lesson; order_steps lines arrive shuffled
    def test_exercise_answers_not_sent_before_an_attempt(self):
        for sid, topics in BANK.items():
            for t in topics:
                section = next(s for s in tutor.compose_lesson(t, "standard", "software")["sections"] if s["kind"] == "exercises")
                full = {e["id"]: e for e in t["exercises"]}
                for pub in section["exercises"]:
                    self.assertFalse(set(tutor.EXERCISE_SECRET_KEYS) & set(pub), pub["id"])
                    if pub["type"] == "order_steps":
                        self.assertNotEqual(pub["lines"], full[pub["id"]]["lines"], pub["id"])
                        self.assertEqual(sorted(pub["lines"]), sorted(full[pub["id"]]["lines"]))
        _, lesson, _ = self.lesson_kinds("hide", ("interactive_exercises",))
        sent = json.dumps(lesson)
        for e in topic(PF, "pf-b1")["exercises"]:
            self.assertNotIn(e["explanation"], sent)

    # Checks, wrong answers and reveals are stored for history but never change progress, evidence or readiness
    def test_exercise_attempts_are_practice_only(self):
        rec = self.student("prx", [], {PF: 2}, methods=("interactive_exercises",))
        learning.open_activity(rec, "prx", PF, "pf-b1")
        before = dict(progress=repository.topic_progress("prx"), skills=repository.skill_learning("prx"),
                      events=repository.learning_events("prx", limit=500), analysis=service.analysis(rec)["readiness"],
                      plan=self.skill(learning.plan(rec, "prx"), PF))
        e1, e2, e3 = topic(PF, "pf-b1")["exercises"]
        wrong = learning.check_exercise(rec, "prx", PF, "pf-b1", e1["id"], (e1["answer"] + 1) % len(e1["options"]))
        self.assertEqual((wrong["correct"], wrong["attempt_number"], wrong["practice_only"]), (False, 1, True))
        self.assertTrue(wrong["can_reveal"])
        self.assertFalse({"explanation", "correct_answer"} & set(wrong))                 # wrong: "Not quite" only
        right = learning.check_exercise(rec, "prx", PF, "pf-b1", e1["id"], e1["answer"])
        self.assertEqual((right["correct"], right["attempt_number"], right["solved_without_reveal"]), (True, 2, True))
        self.assertEqual(right["explanation"], e1["explanation"])
        self.assertEqual(right["correct_answer"], e1["options"][e1["answer"]])
        shown = learning.check_exercise(rec, "prx", PF, "pf-b1", e2["id"], reveal=True)
        self.assertEqual((shown["correct"], shown["revealed"], shown["attempt_number"]), (None, True, 0))
        self.assertEqual(shown["correct_answer"], e2["answers"][0])
        after_reveal = learning.check_exercise(rec, "prx", PF, "pf-b1", e2["id"], e2["answers"][0])
        self.assertEqual((after_reveal["correct"], after_reveal["attempt_number"]), (True, 1))
        self.assertTrue(after_reveal["revealed_before"])
        self.assertFalse(after_reveal["solved_without_reveal"])
        for _ in range(5):                                                               # repeated practice
            learning.check_exercise(rec, "prx", PF, "pf-b1", e3["id"], e3["answer"])
        after = dict(progress=repository.topic_progress("prx"), skills=repository.skill_learning("prx"),
                     events=repository.learning_events("prx", limit=500), analysis=service.analysis(rec)["readiness"],
                     plan=self.skill(learning.plan(rec, "prx"), PF))
        self.assertEqual(after, before)
        self.assertEqual(after["progress"][PF]["pf-b1"]["state"], "learning")
        self.assertEqual(after["plan"]["demonstrated_level"], 0)
        hist = learning.history(rec, "prx")
        self.assertEqual(hist["attempts"], [])                                           # quiz history is not crowded
        self.assertEqual(len(hist["exercise_attempts"]), 9)
        self.assertTrue(all(a["kind"] == "exercise" for a in hist["exercise_attempts"]))
        self.assertEqual(hist["exercise_summary"], dict(tried=3, checks=8, solved=3, solved_without_reveal=2, revealed=1))
        stored = hist["exercise_attempts"][-1]                                           # oldest first at the end
        self.assertEqual(stored["answers"], dict(exercise_id=e1["id"], answer=(e1["answer"] + 1) % len(e1["options"]),
                                                 reveal=False))
        self.assertEqual(stored["score"], 0.0)

    def test_exercise_check_ownership_and_errors(self):
        rec = self.student("own", [], {PF: 2})
        ex = topic(PF, "pf-b1")["exercises"][0]
        for owner, status in (("someone-else", 403), (None, 401)):
            with self.assertRaises(LearningError) as ctx:
                learning.check_exercise(rec, owner, PF, "pf-b1", ex["id"], 0)
            self.assertEqual(ctx.exception.status_code, status)
        for args, status in (((PF, "pf-b1", "pf-b1-e9", 0), 404), ((PF, "nope", ex["id"], 0), 404),
                             (("SK999", "pf-b1", ex["id"], 0), 404), ((PF, "pf-b1", ex["id"], None), 400),
                             ((PF, "pf-b1", ex["id"], 99), 400), ((PF, "pf-b1", ex["id"], "text"), 400)):
            with self.assertRaises(LearningError) as ctx:
                learning.check_exercise(rec, "own", *args)
            self.assertEqual(ctx.exception.status_code, status, args)
        self.assertEqual(repository.attempts_for("own", kind="exercise"), [])


class ModelLoading(unittest.TestCase):
    # Page load sends the analysis and the lesson plan at the same time; the second must not see half-loaded models.
    def test_concurrent_first_requests_wait_for_all_models(self):
        import threading
        import time
        from app.component04_roadmap.analysis import C4Analyzer
        engine = C4Analyzer()
        real_load = engine.load_models

        def slow_load(models_dir):                           # cfg is set first, then each model, like the real loader
            real_load(models_dir)
            models, engine.models = dict(engine.models), {}
            time.sleep(0.3)
            engine.models.update(models)

        errors = []

        def use():
            try:
                engine.ensure_models()
                engine.models["A_gap"]
            except Exception as exc:                         # noqa: BLE001 - any failure is the bug
                errors.append(repr(exc))
        with patch.object(engine, "load_models", side_effect=slow_load):
            first = threading.Thread(target=use)
            first.start()
            deadline = time.time() + 30
            while not engine.cfg and time.time() < deadline:  # wait until cfg is set but the models are not
                time.sleep(0.005)
            others = [threading.Thread(target=use) for _ in range(3)]
            for t in others:
                t.start()
            for t in [first, *others]:
                t.join()
        self.assertEqual(errors, [])


class CurriculumAndRules(unittest.TestCase):
    def test_bank_is_valid(self):
        self.assertEqual(set(BANK), {"SK001", "SK002", "SK008", "SK009", "SK010", "SK014"})
        for skill_id, topics in BANK.items():
            curriculum.validate_skill(skill_id, topics)

    def test_broken_topic_is_rejected(self):
        bad = dict(topic(PF, "pf-b1"), quiz=[dict(topic(PF, "pf-b1")["quiz"][0], answer=99)] * 3)
        with self.assertRaises(curriculum.CurriculumError):
            curriculum.validate_topic(bad)

    def test_curated_videos_pass_validation(self):
        bank = curriculum.load()                             # the bank still loads with the videos merged in
        for skill_id, topics in bank.items():
            for t in topics:
                if "video" in t:
                    curriculum.validate_enrichment(t, f"{skill_id}/{t['id']}")
                    self.assertRegex(t["video"]["checked_on"], r"^\d{4}-\d{2}-\d{2}$")

    def test_malformed_video_is_rejected(self):
        good = dict(youtube_id="abcDEF12_-x", title="A title", channel="A channel", why="What it covers.")
        curriculum.validate_enrichment(dict(video=good), "t")
        for bad_id in ("short", "abcDEF12_-x1", "abcDEF12_-\n", "abc DEF12_x", "abcDEF12/-x", None, 12345678901):
            with self.assertRaises(curriculum.CurriculumError):
                curriculum.validate_enrichment(dict(video=dict(good, youtube_id=bad_id)), "t")
        for key in ("title", "channel", "why"):
            with self.assertRaises(curriculum.CurriculumError):
                curriculum.validate_enrichment(dict(video=dict(good, **{key: "  "})), "t")
        with self.assertRaises(curriculum.CurriculumError):
            curriculum.validate_enrichment(dict(video="abcDEF12_-x"), "t")

    # AI-generated lessons must not show a video link the lesson author never checked
    def test_ai_generated_topic_never_shows_a_video(self):
        video = dict(youtube_id="abcDEF12_-x", title="A title", channel="A channel", why="What it covers.")
        lesson = tutor.compose_lesson(dict(topic(PF, "pf-b1"), video=video, ai_generated=True), "standard", "software")
        self.assertNotIn("video", [s["kind"] for s in lesson["sections"]])

    # ---------------------------------------------------------------- interactive exercises
    def all_exercises(self):
        return [(t, e) for topics in BANK.values() for t in topics for e in t["exercises"]]

    def test_every_topic_has_three_valid_exercises(self):
        topics = [t for ts in BANK.values() for t in ts]
        self.assertEqual(len(topics), 27)
        for t in topics:
            self.assertEqual(len(t["exercises"]), 3, t["id"])
            self.assertGreaterEqual(len({e["type"] for e in t["exercises"]}), 2, t["id"])
            curriculum.validate_exercises(t["exercises"], f"x/{t['id']}")
        for skill_id, topics in BANK.items():                  # every skill practises all four types
            self.assertEqual({e["type"] for t in topics for e in t["exercises"]}, set(curriculum.EXERCISE_TYPES), skill_id)
        ids = [e["id"] for _, e in self.all_exercises()]
        self.assertEqual(len(ids), 81)
        self.assertEqual(len(set(ids)), 81)
        for t, e in self.all_exercises():                       # code exercises use the topic's language
            if e["language"] in curriculum.RUNNABLE_LANGUAGES:
                self.assertEqual(e["language"], t["example"]["language"], e["id"])

    def test_malformed_exercises_are_rejected(self):
        good = {e["id"]: e for _, e in self.all_exercises()}
        where = lambda e: f"x/{e['id'].rsplit('-e', 1)[0]}"
        broken = [
            dict(good["pf-b1-e1"], type="quiz"), dict(good["pf-b1-e1"], language="java"), dict(good["pf-b1-e1"], hint=" "),
            {k: v for k, v in good["pf-b1-e1"].items() if k != "explanation"},
            dict(good["pf-b1-e1"], answer=4), dict(good["pf-b1-e1"], answer=True), dict(good["pf-b1-e1"], options=["1", "1", "2"]),
            dict(good["pf-b1-e1"], options=["1", "2"]), {k: v for k, v in good["pf-b1-e1"].items() if k != "code"},
            dict(good["pf-b1-e2"], code="for n in range(7): print(n)"), dict(good["pf-b1-e2"], code="____ = ____"),
            dict(good["pf-b1-e2"], answers=[]), dict(good["pf-b1-e2"], answers=["x" * 81]),
            {k: v for k, v in good["pf-b1-e2"].items() if k != "expected_output"},
            dict(good["pf-b1-e3"], answer=9), {k: v for k, v in good["pf-b1-e3"].items() if k != "fix"},
            dict(good["pf-b1-e3"], fix=good["pf-b1-e3"]["lines"][3]),
            dict(good["oop-a1-e2"], answer=1),                   # "    def move(self):" appears twice: ambiguous
            dict(good["pf-b2-e3"], lines=["a", "a", "b"]), dict(good["pf-b2-e3"], lines=["a", "b"]),
            {k: v for k, v in good["sql-b1-e1"].items() if k != "setup"}, dict(good["sql-b1-e2"], ignore_case="yes"),
            "not an exercise",
        ]
        for bad in broken:
            with self.assertRaises(curriculum.CurriculumError, msg=str(bad)[:80]):
                curriculum.validate_exercise(bad, where(good["pf-b1-e1"]) if isinstance(bad, str) else where(bad))
        three = topic(PF, "pf-b1")["exercises"]
        for exercises in ([three[0]], three + [dict(three[0], id="pf-b1-e4")], [three[0], three[0]],
                          [dict(e, id=e["id"].replace("pf-b1", "pf-b2")) for e in three], "pf-b1-e1"):
            with self.assertRaises(curriculum.CurriculumError):
                curriculum.validate_exercises(exercises, "SK001/pf-b1")
        with self.assertRaises(curriculum.CurriculumError):    # and through the topic validator used by load()
            curriculum.validate_topic(dict(topic(PF, "pf-b1"), exercises=[dict(three[0], answer=7)] + three[1:]), PF)

    # Every python and sql answer is checked by running the code (exercise_runner); bash/text by structure only
    def test_exercise_answers_are_checked_by_running_the_code(self):
        from .exercise_runner import is_runnable, verify
        runnable = [e for _, e in self.all_exercises() if is_runnable(e)]
        self.assertEqual(len(runnable), 68)
        for e in runnable:
            with self.subTest(exercise=e["id"]):
                self.assertEqual(verify(e), [])
        structure_only = sorted(e["id"] for _, e in self.all_exercises() if not is_runnable(e))
        self.assertEqual(structure_only, sorted(["pf-i1-e3"] + [f"git-{t}-e{i}" for t in ("b1", "b2", "i1", "a1") for i in (1, 2, 3)]))

    # The runner really catches wrong answers (so a passing run means something)
    def test_exercise_runner_detects_wrong_answers(self):
        from .exercise_runner import verify
        good = {e["id"]: e for _, e in self.all_exercises()}
        for bad in (dict(good["pf-b1-e1"], answer=0), dict(good["sql-b1-e1"], answer=1),
                    dict(good["pf-b1-e2"], answers=["n % 2 == 1"]), dict(good["sql-b2-e2"], answers=["WHERE"]),
                    dict(good["py-b2-e3"], fix="for i in range(2, len(prices)):"),
                    dict(good["pf-b2-e3"], lines=["a = 1", "b = 2", "print(a + b)"], expected_output="3"),
                    dict(good["sql-i2-e3"], expected_output="Pen; Lamp; Desk")):
            self.assertNotEqual(verify(bad), [], bad["id"])

    def test_exercise_grading_and_normalisation(self):
        for _, e in self.all_exercises():
            right = (e["answers"][0] if e["type"] == "fill_blank" else list(e["lines"]) if e["type"] == "order_steps"
                     else e["answer"])
            wrong = ("no idea" if e["type"] == "fill_blank" else tutor.shuffled_lines(e) if e["type"] == "order_steps"
                     else (e["answer"] + 1) % len(e.get("options") or e["lines"]))
            self.assertTrue(tutor.check_exercise(e, right)["correct"], e["id"])
            self.assertFalse(tutor.check_exercise(e, wrong)["correct"], e["id"])
            self.assertTrue(tutor.exercise_answer_ok(e, right) and tutor.exercise_answer_ok(e, wrong), e["id"])
        ex = {e["id"]: e for _, e in self.all_exercises()}
        for eid, given, ok in (("pf-b1-e2", "n%2==0", True), ("pf-b1-e2", "  n % 2  ==  0 ", True), ("pf-b1-e2", "n % 2 == 1", False),
                               ("py-i1-e2", 'greeting="Hi"', True), ("py-i1-e2", "greeting = 'Hi'", True),
                               ("py-b1-e3", "Int(year)", False), ("sql-b1-e2", "is null;", True), ("sql-i1-e2", "left outer", True),
                               ("dsa-i1-e2", "target-n", True), ("dsa-i1-e2", "n - target", False), ("pf-b1-e1", "1", True)):
            self.assertEqual(tutor.check_exercise(ex[eid], given)["correct"], ok, (eid, given))
        self.assertFalse(tutor.exercise_answer_ok(ex["pf-b2-e3"], ["only one line"]))
        self.assertFalse(tutor.exercise_answer_ok(ex["pf-b1-e1"], True))
        shown = tutor.check_exercise(ex["pf-b1-e3"], None, reveal=True)
        self.assertEqual(shown["correct_answer"], "Line 4: if m > 50:")
        self.assertEqual(shown["fixed_line"], "if m >= 50:")

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
