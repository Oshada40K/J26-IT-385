# Owner: Dewmi - Component 04.
"""Curated lesson bank for the adaptive tutor.

Each skill module defines SKILL_ID and TOPICS (a list of topic dicts). Every topic has a stage (Beginner / Intermediate /
Advanced), in-skill prerequisites (requires), the lesson parts (objective, main idea, explanation, foundation steps for
learners who need more support, a challenge for experienced learners, a worked example, career examples, key ideas,
common mistakes, practice, a practical task with a self-check rubric, a link to the next step), quiz questions and
diagnostic questions. validate_topic() checks the structure, so a broken lesson is rejected at start-up and AI-generated
lessons can be checked with the same rules.
"""
from . import dsa, git, oop, programming_fundamentals, python, sql
from .enrichment import ENRICHMENT

STAGES = ("Beginner", "Intermediate", "Advanced")
QUESTION_TYPES = ("single", "multi", "short")
REQUIRED_TOPIC_KEYS = ("id", "title", "stage", "requires", "objective", "main_idea", "explanation", "foundation", "challenge",
                       "example", "key_ideas", "mistakes", "practice", "practical", "next_link", "quiz", "diagnostic")
MODULES = (programming_fundamentals, python, sql, git, oop, dsa)


class CurriculumError(ValueError):
    pass


def validate_question(q, where):
    for key in ("id", "type", "prompt", "answer", "explanation", "concept"):
        if not q.get(key) and q.get(key) != 0:
            raise CurriculumError(f"{where}: question is missing '{key}'")
    kind = q["type"]
    if kind not in QUESTION_TYPES:
        raise CurriculumError(f"{where}/{q['id']}: unknown type {kind}")
    if kind in ("single", "multi"):
        options = q.get("options") or []
        if len(options) < 2 or len(set(options)) != len(options):
            raise CurriculumError(f"{where}/{q['id']}: needs two or more distinct options")
        answers = [q["answer"]] if kind == "single" else q["answer"]
        if kind == "single" and not isinstance(q["answer"], int):
            raise CurriculumError(f"{where}/{q['id']}: single answer must be one option index")
        if kind == "multi" and (not isinstance(q["answer"], list) or not q["answer"]):
            raise CurriculumError(f"{where}/{q['id']}: multi answer must be a non-empty list of indexes")
        if any(not isinstance(a, int) or not 0 <= a < len(options) for a in answers):
            raise CurriculumError(f"{where}/{q['id']}: answer index out of range")
        for idx in (q.get("why_wrong") or {}):
            if idx in answers or not 0 <= int(idx) < len(options):
                raise CurriculumError(f"{where}/{q['id']}: why_wrong must refer to a wrong option")
    else:   # short answer: answer = list of keyword groups; each group needs one match
        if not isinstance(q["answer"], list) or not all(isinstance(g, list) and g for g in q["answer"]) or not q.get("sample_answer"):
            raise CurriculumError(f"{where}/{q['id']}: short answers need keyword groups and a sample_answer")


def validate_topic(topic, skill_id="?"):
    where = f"{skill_id}/{topic.get('id', '?')}"
    missing = [k for k in REQUIRED_TOPIC_KEYS if k not in topic]
    if missing:
        raise CurriculumError(f"{where}: missing {missing}")
    if topic["stage"] not in STAGES:
        raise CurriculumError(f"{where}: stage must be one of {STAGES}")
    if len(topic["quiz"]) < 3 or len(topic["diagnostic"]) < 2:
        raise CurriculumError(f"{where}: needs at least 3 quiz and 2 diagnostic questions")
    if not topic["example"].get("code") or not topic["example"].get("steps"):
        raise CurriculumError(f"{where}: the worked example needs code and steps")
    if not topic["practical"].get("task") or not topic["practical"].get("rubric"):
        raise CurriculumError(f"{where}: the practical task needs a task and a rubric")
    for q in topic["quiz"] + topic["diagnostic"]:
        validate_question(q, where)
    validate_enrichment(topic, where)
    return topic


def validate_skill(skill_id, topics):
    if not isinstance(topics, list) or not topics or not all(isinstance(t, dict) for t in topics):
        raise CurriculumError(f"{skill_id}: topics must be a non-empty list of objects")
    for t in topics:                                         # structure first, so malformed (e.g. AI) input is rejected cleanly
        validate_topic(t, skill_id)
    ids = [t["id"] for t in topics]
    if len(ids) != len(set(ids)):
        raise CurriculumError(f"{skill_id}: duplicate topic ids")
    qids = [q["id"] for t in topics for q in t["quiz"] + t["diagnostic"]]
    if len(qids) != len(set(qids)):
        raise CurriculumError(f"{skill_id}: duplicate question ids")
    order = {t: i for i, t in enumerate(ids)}
    for t in topics:
        for r in t["requires"]:
            if r not in order or order[r] >= order[t["id"]]:
                raise CurriculumError(f"{skill_id}/{t['id']}: prerequisite {r} must be an earlier topic of the same skill")
    stages = [STAGES.index(t["stage"]) for t in topics]
    if stages != sorted(stages):
        raise CurriculumError(f"{skill_id}: topics must be ordered Beginner -> Intermediate -> Advanced")
    return topics


ENRICHMENT_KEYS = ("from_zero", "memory_trick", "career_hack", "recall")


def validate_enrichment(topic, where):
    """Optional lecture-style parts (from_zero, memory_trick, career_hack, recall). Checked when present."""
    for key in ("from_zero", "memory_trick", "career_hack"):
        if key in topic and (not isinstance(topic[key], str) or not topic[key].strip()):
            raise CurriculumError(f"{where}: '{key}' must be a non-empty text")
    for item in topic.get("recall") or []:
        if not isinstance(item, dict) or not item.get("q") or not item.get("a"):
            raise CurriculumError(f"{where}: each recall item needs a question 'q' and an answer 'a'")


def load():
    """{skill_id: [topic, ...]} for every curated skill, validated, with the lecture-style parts merged in."""
    bank, ids = {}, set()
    for module in MODULES:
        topics = [dict(t, **ENRICHMENT.get(t["id"], {})) for t in module.TOPICS]
        for t in topics:
            validate_enrichment(t, f"{module.SKILL_ID}/{t['id']}")
        bank[module.SKILL_ID] = validate_skill(module.SKILL_ID, topics)
        ids.update(t["id"] for t in topics)
    unknown = set(ENRICHMENT) - ids
    if unknown:
        raise CurriculumError(f"enrichment for unknown topics: {sorted(unknown)}")
    return bank
