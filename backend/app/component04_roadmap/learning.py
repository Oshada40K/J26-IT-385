# Owner: Dewmi - Component 04.
"""Adaptive learning service: connects the tutor rules (tutor.py), the lesson bank (curriculum/ and optional AI lessons),
the student's saved progress (repository.py) and the existing C4 analysis (service.analysis).

Flow: analysis (gaps, priority, roadmap, entry/target stage per skill) -> placement per skill (checkpoint / claim check)
-> next activity -> lesson adapted to the learner -> quiz / diagnostic -> grading and feedback -> adaptive decision ->
saved progress -> demonstrated level fed back into the analysis as C4 evidence (capped) -> roadmap and readiness regenerate.
Opening a lesson is never evidence; only graded quizzes and diagnostics change mastery.
"""
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from . import curriculum, lesson_provider, repository, service, tutor
from .analysis import METHOD_RESOURCE_TYPES
from .errors import LearningError

ATTEMPT_KINDS = ("quiz", "diagnostic", "practical")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def bank():
    return curriculum.load()


def topics_for(skill_id):
    """(topics, source) for a skill: curated lessons first, then a saved AI-generated course, else (None, None)."""
    if skill_id in bank():
        return bank()[skill_id], "curated"
    saved = repository.generated_curriculum(skill_id)
    if saved:
        return lesson_provider.normalise_topics(saved["topics"]), "ai"
    return None, None


# ---------------------------------------------------------------------------------------------- context
def _check_owner(record, owner):
    if not owner:
        raise LearningError("Upload your CV in Component 01 to use the learning tutor, so your progress can be saved.", 401)
    if not record.get("candidate_id"):
        raise LearningError("This assessment was submitted before your CV was uploaded, so it is not linked to your CV. "
                            "Submit the assessment again to unlock the lessons.", 409)
    if record.get("candidate_id") != owner:
        raise LearningError("You can only see your own learning progress.", 403)


def _context(record, owner):
    """Ownership check, then the student's current analysis and the facts the tutor needs."""
    _check_owner(record, owner)
    analysis = service.analysis(record)
    steps = [s for stage in analysis["roadmap"]["stages"] for s in stage["steps"]]
    ratings = {s["skill_id"]: s.get("self_rating") for s in analysis["skill_gaps"]["skills"]}
    methods = analysis["inputs"].get("learning_methods") or []
    style = list(dict.fromkeys(t for m in methods for t in METHOD_RESOURCE_TYPES.get(m, [])))
    return dict(record=record, owner=owner, analysis=analysis, steps=steps, ratings=ratings, style=style,
                profile=analysis["learner_profile"], career=analysis["target_career"], cfg=tutor.rules())


def _skill_view(ctx, step, progress_all, learning_all):
    sid = step["skill_id"]
    topics, source = topics_for(sid)
    view = dict(skill_id=sid, skill_name=step["skill_name"], roadmap_step=step["step"], roadmap_status=step["status"],
                entry_stage=step["entry_stage"], target_stage=step["target_stage"], current_level=step["current_level"],
                target_level=step["target_level"], lessons=source)
    if not topics:
        view.update(status="self_study", topics=[], next=None, progress=None,
                    message="Interactive lessons are not available for this skill yet. Use the roadmap resources and the "
                            "practical project; your progress is confirmed when your updated CV shows the skill.")
        return view, None, None, None
    progress = progress_all.get(sid, {})
    state = learning_all.get(sid, {})
    place = tutor.placement(topics, step, progress, state, ctx["ratings"].get(sid))
    states = tutor.topic_states(topics, progress, place)
    nxt = tutor.next_in_skill(topics, states, place)
    in_scope = {t["id"] for t in tutor.topics_in_scope(topics, place["target_stage"])}
    done = sum(states[t] in ("mastered", "from_evidence") for t in in_scope)
    locks = tutor.lock_reasons(topics, states, place)
    view.update(placement=place, mismatch=state.get("mismatch"),
                demonstrated_level=tutor.demonstrated_level(topics, states, ctx["cfg"]),
                progress=dict(done=done, total=len(in_scope), percent=round(100 * done / len(in_scope)) if in_scope else 100),
                topics=[dict(topic_id=t["id"], title=t["title"], stage=t["stage"], state=states[t["id"]], objective=t["objective"],
                             in_scope=t["id"] in in_scope, best_score=(progress.get(t["id"]) or {}).get("best_score"),
                             attempts=(progress.get(t["id"]) or {}).get("attempts", 0),
                             locked=bool(locks[t["id"]]), lock_reason=locks[t["id"]]) for t in topics],
                next=nxt)
    if nxt is None:
        view["status"] = "completed"
        view["message"] = (f"All {place['target_stage']}-level topics needed for this career are done in the tutor. "
                           "Finish the practical project and add it to your CV so Component 01 can confirm a higher level.")
    elif any(states[t] == "needs_revision" for t in in_scope):
        view["status"] = "revision"
    else:
        view["status"] = "pending"
    return view, topics, place, states


def _build_plan(ctx):
    owner = ctx["owner"]
    progress_all, learning_all = repository.topic_progress(owner), repository.skill_learning(owner)
    skills, next_activity = [], None
    for step in ctx["steps"]:
        view, *_ = _skill_view(ctx, step, progress_all, learning_all)
        if view["status"] in ("pending", "revision"):
            if next_activity is None:
                view["status"] = "active" if view["status"] == "pending" else "revision"
                nxt = view["next"]
                topic = next((t for t in view["topics"] if t["topic_id"] == nxt.get("topic_id")), None)
                next_activity = dict(nxt, skill_id=view["skill_id"], skill_name=view["skill_name"],
                                     topic_title=topic["title"] if topic else None, stage=topic["stage"] if topic else None)
            elif view["status"] == "pending":
                view["status"] = "next" if not any(s["status"] == "next" for s in skills) else "upcoming"
        skills.append(view)
    if next_activity is None:
        message = ("You have finished every interactive lesson in your roadmap. Continue with the practical projects and the "
                   "self-study skills." if any(s["status"] == "completed" for s in skills) else
                   "None of your roadmap skills has interactive lessons yet. Use the roadmap resources and practical projects.")
    else:
        message = (f"Quick check: {next_activity['skill_name']}" if next_activity["kind"] == "diagnostic" else
                   f"Next: {next_activity['skill_name']} - {next_activity['topic_title']}")
    analysis = ctx["analysis"]
    return dict(
        assessment_id=ctx["record"]["assessment_id"], career=ctx["career"], learner_profile=ctx["profile"],
        learning_style=ctx["style"], next_activity=next_activity, message=message, skills=skills,
        readiness=dict(score=analysis["readiness"]["score"], band=analysis["readiness"]["band"]),
        events=repository.learning_events(owner),
        ai=lesson_provider.ai_status(),
        rules=dict(ctx["cfg"], explanation=(
            f"A quiz score of {ctx['cfg']['mastery_threshold']:.0%} or more marks a topic as mastered and you move on. "
            f"{ctx['cfg']['partial_threshold']:.0%}-{ctx['cfg']['mastery_threshold']:.0%} gives targeted practice on the ideas you "
            f"missed. Below {ctx['cfg']['partial_threshold']:.0%} the topic is taught again step by step; after "
            f"{ctx['cfg']['reteach_before_prerequisite']} low scores you go back to the prerequisite topic. Mastered stages count "
            f"as C4 evidence up to level {ctx['cfg']['tutor_level_cap']}/5, which updates your roadmap and readiness score. "
            "These thresholds are starting settings, not validated values.")),
    )


def plan(record, owner):
    return _build_plan(_context(record, owner))


def _find_step(ctx, skill_id):
    step = next((s for s in ctx["steps"] if s["skill_id"] == skill_id), None)
    if not step:
        raise LearningError("This skill is not part of your current roadmap.", 404)
    return step


def _skill_parts(ctx, skill_id):
    step = _find_step(ctx, skill_id)
    view, topics, place, states = _skill_view(ctx, step, repository.topic_progress(ctx["owner"]),
                                              repository.skill_learning(ctx["owner"]))
    if not topics:
        raise LearningError(view["message"], 404)
    return step, view, topics, place, states


def _topic(topics, topic_id):
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        raise LearningError("Unknown topic for this skill.", 404)
    return topic


def _open_topic(topics, states, place, topic_id):
    """The topic, if it is unlocked for this student (tutor.lock_reasons); 409 with the reason otherwise."""
    topic = _topic(topics, topic_id)
    reason = tutor.lock_reasons(topics, states, place)[topic["id"]]
    if reason:
        raise LearningError(reason, 409)
    return topic


def _diagnostic_scope(topics, place, scope, topic_id, states=None):
    if scope == "test_out":
        return [_open_topic(topics, states, place, topic_id)]
    if not place["checkpoint"]:
        raise LearningError("There is no pending diagnostic for this skill.", 409)
    return [t for t in topics if t["id"] in place["checkpoint_topics"]]


# ---------------------------------------------------------------------------------------------- activities
def open_activity(record, owner, skill_id, topic_id=None, kind="lesson", mode=None, scope=None):
    """A lesson (adapted to the learner) or a diagnostic. Questions never include answers before an attempt."""
    ctx = _context(record, owner)
    step, view, topics, place, states = _skill_parts(ctx, skill_id)
    if kind == "diagnostic":
        scope = scope or place["checkpoint"]
        chosen = _diagnostic_scope(topics, place, scope, topic_id, states)
        return dict(kind="diagnostic", scope=scope, skill_id=skill_id, skill_name=step["skill_name"],
                    reason=place["reason"] if scope != "test_out" else
                    f"Answer {len(chosen[0]['diagnostic'])} questions. Pass and you can skip '{chosen[0]['title']}'.",
                    topics=[dict(topic_id=t["id"], title=t["title"], stage=t["stage"]) for t in chosen],
                    questions=[tutor.public_question(q) for t in chosen for q in t["diagnostic"]])
    topic = _open_topic(topics, states, place, topic_id)
    prev = repository.topic_progress(owner, skill_id).get(topic["id"], {})
    chosen_mode = tutor.lesson_mode(topic, prev, ctx["profile"]["level"], mode, ctx["cfg"])
    lesson = tutor.compose_lesson(topic, chosen_mode, tutor.career_family(ctx["career"]["career_name"]), prev,
                                  ctx["style"], step["skill_name"], ctx["career"]["career_name"])
    engine = service.engine()
    lesson["supplementary_resources"] = engine.recommend_resources(
        skill_id, step["current_level"] / 5, ctx["style"], k=3, entry_stage=topic["stage"], profile=ctx["profile"])
    _personalise(lesson, ctx, prev, topics, topic)
    lesson["why_now"] = (view["next"] or {}).get("reason") if (view["next"] or {}).get("topic_id") == topic["id"] else \
        "You are reviewing this topic." if states[topic["id"]] == "mastered" else "You opened this topic yourself."
    lesson["state"] = states[topic["id"]]
    if states[topic["id"]] == "not_started":                     # opening a lesson is recorded, but is not evidence
        repository.save_topic_progress(owner, skill_id, topic["id"], _now(), "learning", source="opened")
        lesson["state"] = "learning"
    return lesson


def _mode_reason(mode, prev, level):
    if mode == "focused":
        return "Focused revision: your last quiz showed which ideas to work on, so they come first."
    if mode == "foundation" and prev.get("state") == "needs_revision":
        return "Step-by-step again: your last score was low, so the lesson explains it more simply."
    if mode == "foundation":
        return f"Step-by-step version: your learner profile is {level}."
    if mode == "challenge":
        return f"Fast track with a challenge: your learner profile is {level}."
    return f"Standard version: your learner profile is {level}."


def _personalise(lesson, ctx, prev, topics, topic):
    """Arrange the lesson for this student and say how: lesson version (profile and last result), video first (the
    topic's curated video, else a level-matched video from the dataset), extra reading (dataset), interactive
    exercises right after "How it works" (prefers interactive coding exercises), practical first (prefers hands-on
    projects), career examples."""
    methods = ctx["analysis"]["inputs"].get("learning_methods") or []
    resources = lesson.get("supplementary_resources") or []
    sections = lesson["sections"]
    notes = [_mode_reason(lesson["mode"], prev, ctx["profile"]["level"])]
    curated = next((x for x in sections if x["kind"] == "video"), None)
    video = next((r for r in resources if r.get("type") == "video"), None)
    if "video_tutorials" in methods and curated:
        sections.remove(curated)
        curated["title"] = f"Watch first: {curated['video']['title']}"
        sections.insert(1, curated)
        notes.append("Video first: you prefer video tutorials.")
    elif "video_tutorials" in methods and video:
        sections.insert(1, dict(kind="watch_first", title="Watch first", resource=video,
                                text="A short video at this level to watch before you read the lesson."))
        notes.append("Video first: you prefer video tutorials.")
    docs = next((r for r in resources if r.get("type") == "documentation"), None)
    if "reading" in methods and docs:
        at = next((i for i, x in enumerate(sections) if x["kind"] == "explanation"), len(sections) - 1) + 1
        if at < len(sections) and sections[at]["kind"] == "video":   # the curated video stays right after "How it works"
            at += 1
        sections.insert(at, dict(kind="read_more", title="Read more", resource=docs,
                                 text="Documentation at this level for a deeper read."))
        notes.append("Further reading added: you prefer reading documentation.")
    exercises = next((x for x in sections if x["kind"] == "exercises"), None)
    if "interactive_exercises" in methods and exercises:         # after the other moves, so nothing ends up between them
        sections.remove(exercises)
        at = next((i for i, x in enumerate(sections) if x["kind"] == "explanation"), len(sections) - 1) + 1
        sections.insert(at, exercises)
        notes.append("Interactive practice first: you prefer interactive coding exercises.")
    if "project" in (ctx["style"] or []):                        # only hands_on_projects maps to "project"
        notes.append("Practical task first: you prefer hands-on learning.")
    notes.append(f"Examples chosen for {ctx['career']['career_name']}.")
    lesson["personalised"] = notes
    lesson["topic_number"] = next(i for i, t in enumerate(topics, 1) if t["id"] == topic["id"])
    lesson["topic_total"] = len(topics)


def submit_attempt(record, owner, skill_id, kind, answers, topic_id=None, scope=None):
    """Grade a quiz, diagnostic or practical self-check, apply the adaptive decision, save everything, regenerate
    the roadmap and return feedback plus the next activity."""
    if kind not in ATTEMPT_KINDS:
        raise LearningError(f"kind must be one of {ATTEMPT_KINDS}.", 400)
    ctx = _context(record, owner)
    cfg, now = ctx["cfg"], _now()
    step, view, topics, place, states = _skill_parts(ctx, skill_id)
    before = dict(readiness=ctx["analysis"]["readiness"]["score"], level=step["current_level"], entry=step["entry_stage"],
                  demonstrated=view["demonstrated_level"])
    progress = repository.topic_progress(owner, skill_id)
    if kind == "quiz":
        topic = _open_topic(topics, states, place, topic_id)
        graded = tutor.grade(topic["quiz"], answers)
        fields, decision = tutor.decide_after_quiz(topic, topics, graded, progress.get(topic["id"], {}), cfg)
        repository.save_topic_progress(owner, skill_id, topic["id"], now, source="quiz", **fields)
        if decision.get("revisit_topic_id"):
            back = progress.get(decision["revisit_topic_id"], {})
            repository.save_topic_progress(owner, skill_id, decision["revisit_topic_id"], now, "needs_revision",
                                           attempts=back.get("attempts", 0), low_attempts=back.get("low_attempts", 0),
                                           best_score=back.get("best_score"), last_score=back.get("last_score"),
                                           missed=back.get("missed"), source="prerequisite")
    elif kind == "diagnostic":
        scope = scope or place["checkpoint"]
        chosen = _diagnostic_scope(topics, place, scope, topic_id, states)
        graded = tutor.grade([q for t in chosen for q in t["diagnostic"]], answers)
        new_states, passed, decision = tutor.decide_after_diagnostic(chosen, graded, scope, cfg, ctx["ratings"].get(skill_id))
        for tid, state in new_states.items():
            old = progress.get(tid, {})
            repository.save_topic_progress(owner, skill_id, tid, now, state, attempts=old.get("attempts", 0),
                                           low_attempts=old.get("low_attempts", 0),
                                           best_score=old.get("best_score"), last_score=old.get("last_score"),
                                           missed=old.get("missed"), source="diagnostic")
        if scope in ("checkpoint", "claim"):
            weak = [t for t in chosen if new_states.get(t["id"]) == "needs_revision"]
            lowest = min((tutor.STAGE_ORD[t["stage"]] for t in weak), default=None)
            placed = tutor.STAGES[lowest] if lowest is not None else None
            repository.save_skill_learning(owner, skill_id, now, checkpoint="passed" if passed else "failed",
                                           placed_stage=placed, mismatch=decision.get("mismatch"))
    else:   # practical self-check: recorded as practice only
        topic = _open_topic(topics, states, place, topic_id)
        checked = sorted({int(i) for i in (answers or {}).get("rubric", []) if str(i).isdigit()
                          and 0 <= int(i) < len(topic["practical"]["rubric"])})
        graded = dict(score=None, correct=len(checked), total=len(topic["practical"]["rubric"]), results=[],
                      missed_concepts=[], self_checked=[topic["practical"]["rubric"][i] for i in checked])
        decision = dict(case="practical_recorded", message=(
            f"Recorded: you self-checked {len(checked)} of {graded['total']} criteria. Self-checks are practice, not proof; "
            "add the finished project to your CV or portfolio so it can be verified."))
    # Demonstrated level -> C4 evidence -> regenerated analysis (Dynamic Roadmap Regeneration).
    progress_all, learning_all = repository.topic_progress(owner), repository.skill_learning(owner)
    place_after = tutor.placement(topics, step, progress_all.get(skill_id, {}), learning_all.get(skill_id, {}),
                                  ctx["ratings"].get(skill_id))
    states_after = tutor.topic_states(topics, progress_all.get(skill_id, {}), place_after)
    level_after = tutor.demonstrated_level(topics, states_after, cfg)
    if level_after != (learning_all.get(skill_id) or {}).get("demonstrated_level", 0):
        repository.save_skill_learning(owner, skill_id, now, demonstrated_level=level_after)
    repository.add_learning_event(owner, skill_id, decision["case"], f"{step['skill_name']}: {decision['message']}", now)
    after_ctx = _context(record, owner)
    after_step = next((s for s in after_ctx["steps"] if s["skill_id"] == skill_id), None)
    update = _roadmap_update(step, after_step, before, level_after, after_ctx)
    if update["changed"]:
        repository.add_learning_event(owner, skill_id, "roadmap_regenerated", update["message"], now)
    attempt_id = uuid4().hex
    result = dict(graded=graded, decision=decision, roadmap_update=update)
    repository.save_attempt(dict(attempt_id=attempt_id, candidate_id=owner, assessment_id=record["assessment_id"],
                                 skill_id=skill_id, topic_id=topic_id, kind=kind, score=graded.get("score"),
                                 answers=answers, result=result, created_at=now))
    new_plan = _build_plan(after_ctx)
    return dict(attempt_id=attempt_id, kind=kind, skill_id=skill_id, topic_id=topic_id, scope=scope, **result,
                next_activity=new_plan["next_activity"], plan=new_plan, analysis=after_ctx["analysis"])


def _roadmap_update(step, after_step, before, level_after, after_ctx):
    """Explain to the student whether and why the roadmap changed after this attempt."""
    name = step["skill_name"]
    readiness_after = after_ctx["analysis"]["readiness"]["score"]
    changed, parts = False, []
    if level_after > before["demonstrated"]:
        changed = True
        parts.append(f"You have now demonstrated {name} up to level {level_after}/5 in C4 lessons.")
    if after_step is None:
        changed = True
        parts.append(f"{name} has left your roadmap because your evidence now meets this career's level.")
    elif after_step["entry_stage"] != before["entry"]:
        changed = True
        parts.append(f"The roadmap now starts {name} at {after_step['entry_stage']} instead of {before['entry']}, so you "
                     f"continue with the {after_step['entry_stage']} lessons.")
    if round(readiness_after, 1) != round(before["readiness"], 1):
        changed = True
        parts.append(f"Your readiness score changed from {before['readiness']:.0f} to {readiness_after:.0f}.")
    return dict(changed=changed, message=" ".join(parts) if parts else "Your roadmap stays the same: no new evidence of a higher level yet.",
                readiness_before=before["readiness"], readiness_after=readiness_after,
                demonstrated_level_before=before["demonstrated"], demonstrated_level_after=level_after)


def check_exercise(record, owner, skill_id, topic_id, exercise_id, answer=None, reveal=False):
    """Check one interactive exercise (or reveal its answer) and store the attempt for history. PRACTICE ONLY: this
    never reads or writes topic progress, skill placement, demonstrated level or learning events, and never runs the
    analysis, so it cannot change mastery, evidence, the roadmap or readiness. Deliberately light (no lock check):
    an exercise's answer is practice material, never a quiz or diagnostic answer.
    Stored per attempt: the answer, whether it was a reveal, the attempt number for this exercise (checks only),
    whether the answer had been revealed before, and solved_without_reveal."""
    _check_owner(record, owner)
    topics, _ = topics_for(skill_id)
    if not topics:
        raise LearningError("There are no lessons for this skill.", 404)
    topic = _topic(topics, topic_id)
    ex = next((e for e in topic.get("exercises") or [] if e["id"] == exercise_id), None)
    if not ex:
        raise LearningError("Unknown exercise for this topic.", 404)
    reveal = bool(reveal)
    if not reveal and not tutor.exercise_answer_ok(ex, answer):
        raise LearningError("Choose or type an answer before checking.", 400)
    earlier = [a for a in repository.attempts_for(owner, limit=None, kind="exercise", topic_id=topic["id"])
               if (a.get("answers") or {}).get("exercise_id") == exercise_id]
    checks_before = sum(1 for a in earlier if not a["answers"].get("reveal"))
    revealed_before = any(a["answers"].get("reveal") for a in earlier)
    feedback = tutor.check_exercise(ex, answer, reveal)
    feedback.update(exercise_id=exercise_id, attempt_number=checks_before + (0 if reveal else 1),
                    revealed_before=revealed_before,
                    solved_without_reveal=bool(feedback["correct"]) and not revealed_before,
                    practice_only=True)
    attempt_id = uuid4().hex
    repository.save_attempt(dict(attempt_id=attempt_id, candidate_id=owner, assessment_id=record["assessment_id"],
                                 skill_id=skill_id, topic_id=topic["id"], kind="exercise",
                                 score=None if reveal else float(feedback["correct"]),
                                 answers=dict(exercise_id=exercise_id, answer=answer, reveal=reveal),
                                 result=feedback, created_at=_now()))
    return dict(feedback, attempt_id=attempt_id)


def _exercise_summary(rows):
    """Per student: exercises tried, solved, solved without revealing the answer, and revealed."""
    ids = lambda pred: sorted({a["answers"].get("exercise_id") for a in rows if pred(a)})
    return dict(tried=len(ids(lambda a: True)), checks=sum(1 for a in rows if not a["answers"].get("reveal")),
                solved=len(ids(lambda a: (a.get("result") or {}).get("correct") is True)),
                solved_without_reveal=len(ids(lambda a: (a.get("result") or {}).get("solved_without_reveal") is True)),
                revealed=len(ids(lambda a: a["answers"].get("reveal"))))


def history(record, owner):
    ctx_owner = owner
    if not ctx_owner:
        raise LearningError("Upload your CV in Component 01 to see your learning history.", 401)
    if record.get("candidate_id") != ctx_owner:
        raise LearningError("You can only see your own learning progress.", 403)
    exercise_rows = repository.attempts_for(owner, limit=None, kind="exercise")
    return dict(attempts=repository.attempts_for(owner, exclude_kind="exercise"),        # quizzes, diagnostics, self-checks
                exercise_attempts=exercise_rows[:50], exercise_summary=_exercise_summary(exercise_rows),
                events=repository.learning_events(owner, limit=50))


def generate_lessons(record, owner, skill_id):
    """Ask the optional AI provider for a validated course for a skill that has no curated lessons."""
    ctx = _context(record, owner)
    step = _find_step(ctx, skill_id)
    if skill_id in bank():
        raise LearningError("This skill already has curated lessons.", 409)
    try:
        topics, status = lesson_provider.generate_topics(skill_id, step["skill_name"], ctx["career"]["career_name"],
                                                         step["target_stage"])
    except lesson_provider.AIUnavailable as exc:
        raise LearningError(str(exc), 503) from exc
    now = _now()
    repository.save_generated_curriculum(skill_id, status["provider"], status["model"], topics, now)
    repository.add_learning_event(owner, skill_id, "ai_lessons_generated",
                                  f"{step['skill_name']}: AI-generated lessons were created and passed the automatic checks.", now)
    return _build_plan(_context(record, owner))
