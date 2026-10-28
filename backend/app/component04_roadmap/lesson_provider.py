# Owner: Dewmi - Component 04.
"""Where lessons come from.

1. Curated lessons (curriculum/): written for this project, always available, no AI involved.
2. Optional AI-generated lessons for skills without curated lessons. Used ONLY when the backend is configured with
   C4_LLM_API_KEY (or ANTHROPIC_API_KEY). The generated JSON must pass the same checks as the curated lessons
   (curriculum.validate_skill: structure, answer indexes, prerequisites, stage order) before it is saved and shown,
   and it is labelled as AI-generated in the interface. Without a key, the tutor says interactive lessons are not
   available for that skill and the student uses the roadmap resources and practical project instead.
The API key is read on the server only and is never sent to the browser.
"""
import json
import os

from . import curriculum

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"
TIMEOUT_SECONDS = 90


class AIUnavailable(RuntimeError):
    """No provider is configured, or the provider failed, or its output did not pass validation."""


def ai_status():
    key = os.getenv("C4_LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    return dict(configured=bool(key), provider="anthropic" if key else None,
                model=os.getenv("C4_LLM_MODEL", DEFAULT_MODEL) if key else None)


SCHEMA_HINT = """Return ONLY a JSON array of 3 to 5 topic objects, ordered Beginner -> Intermediate -> Advanced. Each topic:
{"id": "<short-unique-id>", "title": str, "stage": "Beginner"|"Intermediate"|"Advanced", "requires": [ids of earlier topics],
 "objective": str, "main_idea": str, "explanation": str (4-6 sentences), "foundation": [3 simple steps],
 "challenge": str, "example": {"title": str, "language": str, "code": str, "steps": [3-4 str]},
 "career_examples": {"software": str, "data": str}, "key_ideas": [3 str], "mistakes": [2 str], "practice": str,
 "practical": {"task": str, "rubric": [3 str]}, "next_link": str,
 "quiz": [3 questions], "diagnostic": [2 questions]}
Question: {"id": "<topic-id>-q1" (diagnostic: "<topic-id>-d1"), "type": "single"|"multi"|"short", "prompt": str,
 "concept": str, "explanation": str, "options": [4 str] (single/multi), "answer": index (single) | [indexes] (multi) |
 [[keyword, synonym], ...] (short), "sample_answer": str (short only)}.
Every answer must be factually correct and unambiguous. Use simple English for university students."""


def _prompt(skill_name, career_name, target_stage):
    return (f"Write a short adaptive course for the skill '{skill_name}' for a student aiming to become a {career_name}. "
            f"Cover Beginner up to {target_stage} level only, focused on what this career needs.\n{SCHEMA_HINT}")


def _parse_topics(text):
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        raise AIUnavailable("The AI response did not contain a JSON list of topics.")
    try:
        topics = json.loads(text[start:end + 1])
    except ValueError as exc:
        raise AIUnavailable(f"The AI response was not valid JSON: {exc}") from exc
    if not isinstance(topics, list) or not 1 <= len(topics) <= 8:
        raise AIUnavailable("The AI response did not contain 1-8 topics.")
    if not all(isinstance(t, dict) for t in topics):
        raise AIUnavailable("Each topic must be a JSON object.")
    return normalise_topics(topics)


def normalise_topics(topics):
    """Mark topics as AI-generated and turn JSON string keys of why_wrong back into option indexes.
    Used for fresh model output and for courses loaded back from the database."""
    for t in topics:
        t["ai_generated"] = True
        t.setdefault("career_examples", {})
        for q in (t.get("quiz") or []) + (t.get("diagnostic") or []):
            if isinstance(q, dict) and isinstance(q.get("why_wrong"), dict):
                try:
                    q["why_wrong"] = {int(k): v for k, v in q["why_wrong"].items()}
                except ValueError:
                    q["why_wrong"] = {}
    return topics


def call_model(prompt, status):
    """Anthropic Messages API call through httpx (already a backend dependency). Isolated so tests can replace it."""
    import httpx
    key = os.getenv("C4_LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    try:
        response = httpx.post(ANTHROPIC_URL, timeout=TIMEOUT_SECONDS,
                              headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                              json={"model": status["model"], "max_tokens": 16000,
                                    "messages": [{"role": "user", "content": prompt}]})
        response.raise_for_status()
        data = response.json()
    except Exception as exc:                                     # network, auth, rate limit or bad JSON
        raise AIUnavailable(f"The AI provider could not be reached: {exc}") from exc
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def generate_topics(skill_id, skill_name, career_name, target_stage):
    """Generate and validate a course for one skill. Raises AIUnavailable when not configured or invalid."""
    status = ai_status()
    if not status["configured"]:
        raise AIUnavailable("No AI provider is configured (set C4_LLM_API_KEY on the backend).")
    topics = _parse_topics(call_model(_prompt(skill_name, career_name, target_stage), status))
    try:
        curriculum.validate_skill(skill_id, topics)
    except curriculum.CurriculumError as exc:
        raise AIUnavailable(f"The generated lesson failed the quality checks: {exc}") from exc
    return topics, status
