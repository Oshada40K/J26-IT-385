# Owner: Dewmi - Component 04.
"""Adaptive tutor rules (pure logic, no web framework or database code).

The tutor works on the lesson bank (curriculum/), the student's C4 analysis (roadmap order, entry and target stage,
status per skill) and the student's saved learning progress. All decisions are deterministic rules with the settings in
RULES, so every decision can be explained and tested. Nothing here is a trained ML model and nothing here calls an AI
service (see lesson_provider.py for the optional AI lesson generator).

Topic states
  not_started     not opened yet
  learning        lesson opened, no quiz passed yet (opening a lesson is never evidence)
  needs_revision  quiz or diagnostic below the mastery threshold
  mastered        quiz or diagnostic at/above the threshold (demonstrated in C4)
  from_evidence   below the student's evidence-based starting stage (CV or proof); skipped until a checkpoint confirms it
"""
import json
import os
import random
import re

STAGES = ("Beginner", "Intermediate", "Advanced")
STAGE_ORD = {s: i for i, s in enumerate(STAGES)}

DEFAULT_RULES = dict(
    mastery_threshold=0.8,            # quiz score that marks a topic as mastered (starting configuration, not a validated value)
    partial_threshold=0.5,            # >= partial and < mastery: targeted practice on the missed concepts; below: re-teach
    diagnostic_pass=0.8,              # checkpoint / claim-check / test-out pass mark
    reteach_before_prerequisite=2,    # attempts below partial_threshold before the tutor goes back to the prerequisite topic
    repeated_mistake_count=2,         # the same concept missed in this many attempts = repeated mistake
    tutor_level_cap=3,                # highest evidence level (0-5) C4 quizzes can add (same cap as C4's own proof checks)
    stage_levels={"Beginner": 2, "Intermediate": 3, "Advanced": 4},
)
DONE_STATES = ("mastered",)


def rules():
    """DEFAULT_RULES, optionally overridden by the JSON in the C4_TUTOR_RULES environment variable."""
    merged = json.loads(json.dumps(DEFAULT_RULES))
    override = os.getenv("C4_TUTOR_RULES", "").strip()
    if override:
        try:
            merged.update({k: v for k, v in json.loads(override).items() if k in DEFAULT_RULES})
        except ValueError:
            pass
    return merged


DATA_WORDS = ("data", "database", "statistic", "analyst", "scientist", "intelligence", "actuar", "geospatial", "bioinformatic")


def career_family(career_name):
    """Which worked-example family suits the career: 'data' or 'software' (the general default)."""
    name = (career_name or "").lower()
    return "data" if any(w in name for w in DATA_WORDS) else "software"


# ---------------------------------------------------------------------------------------------- placement
def topics_in_scope(topics, target_stage):
    """Topics needed for the career: every topic up to the target stage. Topics above it are optional extras."""
    return [t for t in topics if STAGE_ORD[t["stage"]] <= STAGE_ORD[target_stage]]


def placement(topics, step, progress, skill_state, rating=None):
    """Decide where this student starts in this skill.

    step:        the skill's roadmap step from the analysis (entry_stage, target_stage, status, current_level)
    progress:    {topic_id: saved progress row}
    skill_state: saved per-skill row (checkpoint, placed_stage, mismatch) or {}
    Returns a dict: placed_stage, target_stage, checkpoint (None | 'checkpoint' | 'claim'), checkpoint_topics, reason.
    """
    entry, target = step["entry_stage"], step["target_stage"]
    placed = skill_state.get("placed_stage") or entry
    if STAGE_ORD[placed] > STAGE_ORD[entry]:
        placed = entry                                        # a saved placement can lower, never raise, the start
    done = {tid for tid, p in progress.items() if p.get("state") in DONE_STATES}
    checkpoint, scope = None, []
    status = step.get("status")
    if status == "unverified" and skill_state.get("checkpoint") not in ("passed", "failed"):
        # Claimed skill (rated 4-5/5, CV 0-1/5): check the claim before teaching (confidence-aware analysis).
        claim_max = min(STAGE_ORD[target], STAGE_ORD["Intermediate"])
        scope = [t for t in topics if STAGE_ORD[t["stage"]] <= claim_max and t["id"] not in done]
        checkpoint = "claim" if scope else None
    elif STAGE_ORD[placed] > 0 and skill_state.get("checkpoint") not in ("passed", "failed"):
        # Evidence lets the student skip earlier stages: a short checkpoint confirms the skipped basics first.
        scope = [t for t in topics if STAGE_ORD[t["stage"]] < STAGE_ORD[placed] and t["id"] not in done]
        checkpoint = "checkpoint" if scope else None
    level = step.get("current_level", 0)
    if checkpoint == "claim":
        rated = f"you rated yourself {rating}/5" if rating else "you rated this skill highly"
        reason = (f"Your CV shows level {level}/5 but {rated}. A short diagnostic checks the claim before teaching, "
                  "so confidence alone is never treated as proof.")
    elif checkpoint == "checkpoint":
        reason = (f"Your evidence (level {level}/5) lets you skip to {placed}. A short checkpoint confirms the skipped "
                  f"{' and '.join(sorted({t['stage'] for t in scope}, key=STAGE_ORD.get))} basics before you continue.")
    elif STAGE_ORD[placed] < STAGE_ORD[entry]:
        reason = f"Your diagnostic showed gaps, so you continue from {placed} topics before moving on."
    elif STAGE_ORD[placed] > 0:
        reason = f"You start at {placed}: earlier topics are covered by your evidence and checkpoint."
    else:
        reason = "You start at Beginner because there is no evidence of this skill yet."
    return dict(placed_stage=placed, target_stage=target, checkpoint=checkpoint,
                checkpoint_topics=[t["id"] for t in scope], reason=reason)


def topic_states(topics, progress, place):
    """Effective state of every topic, after placement (saved progress wins over placement defaults)."""
    states = {}
    for t in topics:
        saved = (progress.get(t["id"]) or {}).get("state")
        if saved:
            states[t["id"]] = saved
        elif STAGE_ORD[t["stage"]] < STAGE_ORD[place["placed_stage"]]:
            states[t["id"]] = "from_evidence"
        else:
            states[t["id"]] = "not_started"
    return states


def lock_reasons(topics, states, place):
    """{topic_id: None (open) or the reason it is locked}. Lessons open in order: a topic opens only when every earlier
    topic of the skill is mastered or covered by evidence (so a re-teach or prerequisite decision cannot be skipped).
    Mastered topics always stay open for review. While a checkpoint / claim check is pending, only mastered topics open.
    A student who already knows a locked topic proves it with the diagnostic, not by opening later lessons."""
    if place["checkpoint"]:
        return {t["id"]: None if states[t["id"]] == "mastered" else
                "Take the short check for this skill first, so the coach knows where you should start." for t in topics}
    first = next((t for t in topics if states[t["id"]] not in ("mastered", "from_evidence")), None)
    out, reached = {}, False
    for t in topics:
        if states[t["id"]] in ("mastered", "from_evidence") or not reached:
            out[t["id"]] = None
        else:
            out[t["id"]] = f"Finish '{first['title']}' first. Lessons open in order so each one builds on the last."
        if first is not None and t["id"] == first["id"]:
            reached = True
    return out


def next_in_skill(topics, states, place):
    """The next activity inside one skill, or None when every topic in scope is done.
    Order: pending checkpoint -> earliest topic needing revision -> first unfinished topic whose prerequisites are met."""
    if place["checkpoint"]:
        return dict(kind="diagnostic", scope=place["checkpoint"], topic_id=None, reason=place["reason"])
    scope = topics_in_scope(topics, place["target_stage"])
    by_id = {t["id"]: t for t in topics}
    ok = lambda tid: states.get(tid) in ("mastered", "from_evidence")
    for t in scope:
        if states[t["id"]] == "needs_revision":
            return dict(kind="revision", topic_id=t["id"],
                        reason=f"Revise '{t['title']}': your last quiz showed gaps that later topics depend on.")
    for t in scope:
        if ok(t["id"]):
            continue
        missing = [r for r in t["requires"] if not ok(r)]
        if missing:
            first = by_id[missing[0]]
            return dict(kind="lesson", topic_id=first["id"],
                        reason=f"'{first['title']}' comes first because '{t['title']}' builds on it.")
        return dict(kind="lesson", topic_id=t["id"],
                    reason=f"Next topic at your level: {t['stage']}." if STAGE_ORD[t["stage"]] >= STAGE_ORD[place["placed_stage"]]
                    else f"Needed before your {place['placed_stage']} topics.")
    return None


def demonstrated_level(topics, states, cfg):
    """Evidence level (0-5) the student has demonstrated in C4 lessons: the highest stage whose topics (and all earlier
    stages' topics) are mastered through quizzes or diagnostics, mapped with stage_levels and capped by tutor_level_cap.
    Skipped 'from_evidence' topics do not count: that level already comes from the CV or proof."""
    level = 0
    for stage in STAGES:
        stage_topics = [t for t in topics if t["stage"] == stage]
        if not stage_topics or any(states.get(t["id"]) != "mastered" for t in stage_topics):
            break
        level = cfg["stage_levels"][stage]
    return min(level, cfg["tutor_level_cap"])


# ---------------------------------------------------------------------------------------------- questions and grading
def public_question(q):
    """A question as sent before an attempt: never the answer, explanation or feedback."""
    out = dict(id=q["id"], type=q["type"], prompt=q["prompt"], concept=q["concept"])
    if q["type"] in ("single", "multi"):
        out["options"] = list(q["options"])
    return out


def _norm(text):
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _option_text(q, idx):
    return q["options"][idx] if isinstance(idx, int) and 0 <= idx < len(q["options"]) else None


def grade_question(q, given):
    """Returns (correct: bool, feedback dict). given: int (single), list[int] (multi) or str (short)."""
    fb = dict(id=q["id"], type=q["type"], prompt=q["prompt"], concept=q["concept"], explanation=q["explanation"])
    if q["type"] == "single":
        try:
            choice = int(given)
        except (TypeError, ValueError):
            choice = None
        correct = choice == q["answer"]
        fb.update(your_answer=_option_text(q, choice), correct_answer=q["options"][q["answer"]])
        if not correct and choice is not None:
            why = (q.get("why_wrong") or {}).get(choice)
            if why:
                fb["why_your_answer_is_wrong"] = why
    elif q["type"] == "multi":
        chosen = set()
        for g in (given if isinstance(given, (list, tuple)) else []):
            try:
                chosen.add(int(g))
            except (TypeError, ValueError):
                pass
        key = set(q["answer"])
        correct = chosen == key
        fb.update(your_answer=[_option_text(q, i) for i in sorted(chosen) if _option_text(q, i)],
                  correct_answer=[q["options"][i] for i in sorted(key)])
        if not correct:
            wrong = [q["options"][i] for i in sorted(chosen - key) if _option_text(q, i)]
            missed = [q["options"][i] for i in sorted(key - chosen)]
            fb["why_your_answer_is_wrong"] = " ".join(
                p for p in (f"Not correct: {', '.join(wrong)}." if wrong else "",
                            f"Also correct: {', '.join(missed)}." if missed else "") if p)
    else:
        text = _norm(given)
        groups = q["answer"]
        hits = [any(_norm(k) in text for k in g) for g in groups]
        correct = bool(text) and all(hits)
        fb.update(your_answer=str(given or ""), correct_answer=q["sample_answer"], checked_by="keywords",
                  check_note="Short answers are checked automatically for key ideas, not marked by a person.")
        if not correct:
            fb["why_your_answer_is_wrong"] = ("Your answer does not mention: "
                                             + "; ".join(" / ".join(g) for g, h in zip(groups, hits) if not h) + ".")
    fb["correct"] = correct
    return correct, fb


def grade(questions, answers):
    """answers: {question_id: given}. Unanswered questions count as wrong. Returns score (0-1), feedback, missed concepts."""
    answers = answers or {}
    results, missed = [], []
    for q in questions:
        ok, fb = grade_question(q, answers.get(q["id"]))
        results.append(fb)
        if not ok:
            missed.append(q["concept"])
    score = sum(r["correct"] for r in results) / len(results) if results else 0.0
    return dict(score=round(score, 4), correct=sum(r["correct"] for r in results), total=len(results),
                results=results, missed_concepts=sorted(set(missed)))


# ---------------------------------------------------------------------------------------------- interactive exercises
# Practice only: checked instantly on the server so answers never reach the browser before an attempt, and never used
# for mastery, placement, evidence, roadmap or readiness (see learning.check_exercise).
EXERCISE_SECRET_KEYS = ("answer", "answers", "explanation", "fix")
EXERCISE_PUBLIC_KEYS = ("id", "type", "language", "prompt", "hint", "code", "setup", "options", "expected_output")


def shuffled_lines(ex):
    """order_steps lines in a fixed shuffled order (seeded by the exercise id) that is never the correct order."""
    lines = list(ex["lines"])
    rng = random.Random(ex["id"])
    for _ in range(20):
        rng.shuffle(lines)
        if lines != ex["lines"]:
            return lines
    return ex["lines"][1:] + ex["lines"][:1]                  # rotation: always different for 3+ distinct lines


def public_exercise(ex):
    """An exercise as sent with the lesson: never the answer(s), explanation or fixed line."""
    out = {k: ex[k] for k in EXERCISE_PUBLIC_KEYS if k in ex}
    if ex["type"] == "find_bug":
        out["lines"] = list(ex["lines"])
    elif ex["type"] == "order_steps":
        out["lines"] = shuffled_lines(ex)
    return out


def _norm_code(text, ignore_case=False):
    """Normalised short code answer: outer and repeated spaces, spaces around operators and punctuation, quote style
    (' or ") and a trailing ';' do not matter. Case matters unless ignore_case (SQL keywords)."""
    t = re.sub(r"\s+", " ", str(text or "").replace('"', "'")).strip()
    t = re.sub(r"\s*([^\w\s'])\s*", r"\1", t).rstrip(";").strip()
    return t.lower() if ignore_case else t


def _index(given):
    if isinstance(given, bool):
        return None
    if isinstance(given, int):
        return given
    if isinstance(given, str) and given.strip().isdigit():
        return int(given.strip())
    return None


def exercise_answer_ok(ex, given):
    """True when `given` has the right shape for the exercise type (an option / line index, a text, or the lines)."""
    if ex["type"] in ("predict_output", "find_bug"):
        size = len(ex["options"] if ex["type"] == "predict_output" else ex["lines"])
        i = _index(given)
        return i is not None and 0 <= i < size
    if ex["type"] == "fill_blank":
        return isinstance(given, str) and bool(given.strip())
    return isinstance(given, list) and sorted(map(str, given)) == sorted(ex["lines"])


def exercise_solution(ex):
    """What the student sees after a correct answer or after "Show answer": the explanation and the correct answer."""
    out = dict(explanation=ex["explanation"])
    if ex["type"] == "predict_output":
        out["correct_answer"] = ex["options"][ex["answer"]]
    elif ex["type"] == "find_bug":
        out["correct_answer"] = f"Line {ex['answer'] + 1}: {ex['lines'][ex['answer']].strip()}"
        if ex.get("fix"):
            out["fixed_line"] = ex["fix"].strip()
    elif ex["type"] == "fill_blank":
        out["correct_answer"] = ex["answers"][0]
        if len(ex["answers"]) > 1:
            out["also_accepted"] = list(ex["answers"][1:])
    else:
        out["correct_answer"] = list(ex["lines"])
    return out


def check_exercise(ex, given, reveal=False):
    """Check one exercise. reveal=True shows the solution without checking an answer (correct is None).
    A wrong answer gets only "Not quite" (plus the hint in the lesson); the solution comes with a correct answer or a reveal."""
    if reveal:
        return dict(id=ex["id"], type=ex["type"], correct=None, revealed=True, message="Here is the answer.",
                    **exercise_solution(ex))
    if ex["type"] in ("predict_output", "find_bug"):
        correct = _index(given) == ex["answer"]
    elif ex["type"] == "fill_blank":
        case = bool(ex.get("ignore_case"))
        correct = _norm_code(given, case) in {_norm_code(a, case) for a in ex["answers"]}
    else:
        correct = isinstance(given, list) and [str(x) for x in given] == list(ex["lines"])
    if correct:
        return dict(id=ex["id"], type=ex["type"], correct=True, revealed=False, message="Correct!", **exercise_solution(ex))
    return dict(id=ex["id"], type=ex["type"], correct=False, revealed=False,
                message="Not quite. Use the hint or try again.", can_reveal=True)


# ---------------------------------------------------------------------------------------------- adaptive decisions
def decide_after_quiz(topic, topics, graded, prev, cfg):
    """Adaptive decision after a topic quiz (Cases A-F of the design). prev: saved progress row for the topic (or {}).
    Returns the new progress fields and a decision explained in plain English."""
    score = graded["score"]
    attempts = int(prev.get("attempts") or 0) + 1
    low_attempts = int(prev.get("low_attempts") or 0)
    missed_counts = dict(prev.get("missed") or {})
    for c in graded["missed_concepts"]:
        missed_counts[c] = missed_counts.get(c, 0) + 1
    repeated = sorted(c for c in graded["missed_concepts"] if missed_counts[c] >= cfg["repeated_mistake_count"])
    best = max(score, float(prev.get("best_score") or 0))
    pct = f"{graded['correct']}/{graded['total']}"
    decision = dict(score=score, repeated_mistakes=repeated, missed_concepts=graded["missed_concepts"])
    if score >= cfg["mastery_threshold"]:
        state = "mastered"
        decision.update(case="advance", next_mode=None,
                        message=f"{pct} correct: you have shown you understand '{topic['title']}'. Moving on to the next activity.")
    elif score >= cfg["partial_threshold"]:
        state = "needs_revision"
        decision.update(case="targeted_practice", next_mode="focused", next_topic_id=topic["id"],
                        message=f"{pct} correct: good progress, but you missed {', '.join(graded['missed_concepts'])}. "
                                "Review the focused explanation for those ideas, then try the quiz again.")
    else:
        state = "needs_revision"
        low_attempts += 1
        prereqs = [t for t in topics if t["id"] in topic["requires"]]
        if low_attempts >= cfg["reteach_before_prerequisite"] and prereqs:
            back = prereqs[-1]
            decision.update(case="prerequisite", next_mode="foundation", next_topic_id=back["id"], revisit_topic_id=back["id"],
                            message=f"{pct} correct again. '{topic['title']}' builds on '{back['title']}', so we go back to "
                                    f"that topic first with a simpler explanation, then return here.")
        else:
            decision.update(case="reteach", next_mode="foundation", next_topic_id=topic["id"],
                            message=f"{pct} correct. Let's go through '{topic['title']}' again step by step, with a simpler "
                                    "explanation and another worked example, before the next quiz.")
    if repeated:
        decision["message"] += (f" You have missed {', '.join(repeated)} in {cfg['repeated_mistake_count']} or more attempts, "
                                "so the next lesson explains it a different way and highlights the common mistakes.")
        if decision.get("next_mode") == "focused":
            decision["next_mode"] = "foundation"
    return dict(state=state, attempts=attempts, low_attempts=low_attempts, best_score=best, last_score=score,
                missed=missed_counts), decision


def decide_after_diagnostic(scope_topics, graded, kind, cfg, rating=None):
    """Checkpoint / claim check / test-out. Topics whose diagnostic questions were all correct become mastered;
    the rest need revision. Returns ({topic_id: state}, passed, decision)."""
    owner = {q["id"]: t["id"] for t in scope_topics for q in t["diagnostic"]}
    by_topic = {}
    for r in graded["results"]:
        by_topic.setdefault(owner.get(r["id"]), []).append(r["correct"])
    states = {t["id"]: ("mastered" if all(by_topic.get(t["id"], [False])) else "needs_revision") for t in scope_topics}
    passed = graded["score"] >= cfg["diagnostic_pass"]
    weak = [t for t in scope_topics if states[t["id"]] == "needs_revision"]
    pct = f"{graded['correct']}/{graded['total']}"
    if kind == "claim":
        if passed:
            msg = f"{pct} correct: the diagnostic supports your self-rating. Those topics count as demonstrated."
            mismatch = "supported"
        else:
            rated = f"You rated yourself {rating}/5, but" if rating else "Your self-rating was high, but"
            msg = (f"{rated} the diagnostic showed gaps ({pct} correct) in "
                   f"{', '.join(t['title'] for t in weak)}. You will start with those topics; confidence alone is not counted as proficiency.")
            mismatch = "confirmed"
    elif kind == "checkpoint":
        mismatch = None
        msg = (f"{pct} correct: your earlier basics are confirmed, so they stay skipped." if passed and not weak else
               f"{pct} correct: you know most of the basics. Revise {', '.join(t['title'] for t in weak)} first; "
               "the other skipped topics stay skipped." if passed else
               f"{pct} correct: some basics need revision before the next level: {', '.join(t['title'] for t in weak)}.")
    else:   # test-out of one topic
        mismatch = None
        msg = (f"{pct} correct: you tested out of this topic." if passed else
               f"{pct} correct: not enough to skip this topic, so continue with the lesson.")
    if kind == "test_out" and not passed:
        states = {}                                           # a failed test-out simply leaves the topic to be learned
    return states, passed, dict(case=f"{kind}_{'passed' if passed else 'failed'}", message=msg, mismatch=mismatch,
                                score=graded["score"], missed_concepts=graded["missed_concepts"])


# ---------------------------------------------------------------------------------------------- lesson composition
def lesson_mode(topic, prev, profile_level, requested=None, cfg=None):
    """foundation (struggling / novice beginner), focused (partial understanding), challenge (experienced), or standard."""
    cfg = cfg or DEFAULT_RULES
    if requested in ("foundation", "focused", "challenge", "standard"):
        return requested
    last = prev.get("last_score")
    if prev.get("state") == "needs_revision" and last is not None:
        repeated = any(n >= cfg["repeated_mistake_count"] for n in (prev.get("missed") or {}).values())
        return "focused" if last >= cfg["partial_threshold"] and not repeated else "foundation"
    if profile_level == "Novice" and topic["stage"] == "Beginner":
        return "foundation"
    if profile_level == "Experienced":
        return "challenge"
    return "standard"


MODE_LABELS = {
    "foundation": "Step-by-step version: extra support, simpler steps and more practice.",
    "focused": "Focused revision: concentrates on the ideas you missed last time.",
    "challenge": "Fast track: core ideas only, plus a harder challenge, because your profile shows experience.",
    "standard": "Standard lesson at your level.",
}


def compose_lesson(topic, mode, family, prev=None, style_types=(), skill_name="", career_name=""):
    """The lesson the student sees, in a lecture-notes layout (main idea, explain from zero, real-life example, how it
    works, curated video, visual, worked example, interactive exercises, key ideas, memory trick, interview hack, common
    mistakes, practice, summary, memory test, next).
    Content changes with the mode (not only the label): foundation opens the step-by-step part and all common mistakes;
    focused puts the missed ideas first; challenge folds the beginner support away and adds a harder task.
    Learning-style changes that need resources (video first, reading) are added by learning.open_activity."""
    prev = prev or {}
    missed = sorted((prev.get("missed") or {}).items(), key=lambda kv: -kv[1])
    example_text = (topic.get("career_examples") or {}).get(family) or (topic.get("career_examples") or {}).get("software")
    sections = [dict(kind="objective", title="What you will learn", text=topic["objective"])]
    if mode in ("focused", "foundation") and missed:
        sections.append(dict(kind="focus", title="Focus on what you missed",
                             items=[f"{c} (missed in {n} attempt{'s' if n > 1 else ''})" for c, n in missed]))
    sections.append(dict(kind="main_idea", title="Main idea", text=topic["main_idea"]))
    sections.append(dict(kind="from_zero", title="Explain from zero", text=topic.get("from_zero"), items=list(topic["foundation"]),
                         collapsed=mode == "challenge"))
    if example_text:
        sections.append(dict(kind="career", title=f"Real-life example: {career_name or 'your career'}", text=example_text))
    sections.append(dict(kind="explanation", title="How it works", text=topic["explanation"]))
    if topic.get("video") and not topic.get("ai_generated"):  # only videos the lesson author checked, never AI-suggested links
        video = topic["video"]
        sections.append(dict(kind="video", title=f"Watch: {video['title']}", video=dict(video),
                             note=f"Video from YouTube ({video['channel'].strip()}), chosen by the lesson author. Not produced by CareerNova."))
    if topic.get("visual") and mode != "challenge":
        sections.append(dict(kind="visual", title=topic["visual"]["caption"], visual=topic["visual"]))
    sections.append(dict(kind="worked_example", title=f"Worked example: {topic['example']['title']}", example=topic["example"]))
    if topic.get("exercises"):
        sections.append(dict(kind="exercises", title="Practice: interactive exercises",
                             exercises=[public_exercise(e) for e in topic["exercises"]],
                             note="Practice only: checked instantly, but never graded and never counted as evidence of mastery."))
    sections.append(dict(kind="key_ideas", title="Key ideas to remember", items=list(topic["key_ideas"])))
    if topic.get("memory_trick"):
        sections.append(dict(kind="memory_trick", title="Memory trick", text=topic["memory_trick"]))
    if topic.get("career_hack"):
        sections.append(dict(kind="career_hack", title="Interview and job hack", text=topic["career_hack"]))
    if mode != "challenge" or missed:
        sections.append(dict(kind="mistakes", title="Common mistakes", items=list(topic["mistakes"])))
    hands_on = "project" in style_types                    # only "hands_on_projects" maps to "project" (analysis.METHOD_RESOURCE_TYPES)
    practice = [dict(kind="practice", title="Try it yourself", text=topic["practice"]),
                dict(kind="practical", title="Practical task (self-check)", text=topic["practical"]["task"],
                     items=list(topic["practical"]["rubric"]),
                     note="Use the checklist to judge your own work. Self-checks are recorded as practice, not as proof of mastery.")]
    if mode == "challenge":
        practice.insert(0, dict(kind="challenge", title="Challenge", text=topic["challenge"]))
    if hands_on:
        practice.reverse()                                   # project-based learners see the practical task first
    sections.extend(practice)
    sections.append(dict(kind="summary", title="Mini summary", text=f"{topic['main_idea']} {topic['key_ideas'][0]}"))
    if topic.get("recall"):
        sections.append(dict(kind="recall", title="Memory test", recall=[dict(q=r["q"], a=r["a"]) for r in topic["recall"]],
                             note="Try to answer in your own words first, then reveal the answer. This is practice and is not graded."))
    sections.append(dict(kind="next", title="What comes next", text=topic["next_link"]))
    return dict(topic_id=topic["id"], title=topic["title"], stage=topic["stage"], skill_name=skill_name, mode=mode,
                mode_label=MODE_LABELS[mode], sections=sections,
                quiz=[public_question(q) for q in topic["quiz"]],
                ai_generated=bool(topic.get("ai_generated")),
                source="AI-generated lesson (checked automatically against the lesson rules)" if topic.get("ai_generated")
                else "Curated lesson written for this project")
