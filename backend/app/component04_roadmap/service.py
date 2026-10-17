# Owner: Dewmi - Component 04.
# Career Readiness Assessment form: chooses the skills to ask about and stores submissions.
# Roadmap generation, gap analysis and readiness scoring are not implemented here.
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

INPUTS_DIR = Path(__file__).with_name("inputs")
MIN_SKILLS, MAX_SKILLS = 10, 15

# Form options -> learning_resources.csv resource types used by c4_engine.
RESOURCE_TYPE = {
    "hands_on_projects": "project", "interactive_exercises": "project", "video_tutorials": "video",
    "online_courses": "course", "instructor_led": "course", "reading": "documentation",
    "group_learning": "mixed", "other": "mixed",
}
WEEKLY_HOURS = {"1-3": 2.0, "4-6": 5.0, "7-10": 8.5, "11-15": 13.0, "15+": 18.0}


class CareerNotSupported(ValueError):
    pass


def assessments_dir():
    default = Path(__file__).parents[2] / ".data" / "component04" / "assessments"
    return Path(os.getenv("C4_ASSESSMENT_DIR", str(default)))


@lru_cache(maxsize=1)
def engine():
    # Imported lazily so a data problem only affects C4 endpoints, never app startup.
    # No models are loaded: the form only needs the O*NET catalogue and C1 skill mapping.
    from .c4_engine import C4Engine
    return C4Engine(str(INPUTS_DIR), None)


def careers():
    occ = engine().occ
    return [{"career_id": c, "career_name": n} for c, n in sorted(zip(occ.career_id, occ.career_name), key=lambda x: x[1])]


def resolve_career(career_id=None, career_name=None):
    eng = engine()
    cid = career_id or eng.title_to_code.get(" ".join(str(career_name or "").lower().split()))
    if cid not in eng.req_by_career:
        label = career_name or career_id
        raise CareerNotSupported(f"'{label}' is not one of the {len(eng.req_by_career)} IT careers covered by Component 4.")
    return cid, eng.career_name[cid]


def assessment_skills(career_id, c1_skills):
    """Pick 10-15 unique skills: the career's O*NET requirements first, then other skills from the CV."""
    eng = engine()
    cv_levels = {}
    for skill in c1_skills:
        sid, _ = eng.map_skill(skill["name"])
        if sid:
            cv_levels[sid] = max(cv_levels.get(sid, 0), skill.get("level") or 0)

    req = eng.req_by_career[career_id].sort_values(["is_essential", "importance"], ascending=False)
    # Required skills already in the CV are kept first if the list ever needs trimming.
    required = sorted(dict.fromkeys(req.skill_id), key=lambda s: s not in cv_levels)[:MAX_SKILLS]
    required_set = set(required)
    extra = sorted((s for s in cv_levels if s not in required_set), key=lambda s: -cv_levels[s])
    chosen = required + extra[:MAX_SKILLS - len(required)]
    # Keep the display order by importance for required skills, then CV extras.
    order = {s: i for i, s in enumerate(dict.fromkeys(req.skill_id))}
    chosen.sort(key=lambda s: (s not in required_set, order.get(s, 0)))
    return [dict(skill_id=s, skill_name=eng.name[s], skill_level=eng.level[s],
                 in_cv=s in cv_levels, career_requirement=s in required_set) for s in chosen]


def _resource_preferences(methods):
    types = list(dict.fromkeys(RESOURCE_TYPE[m] for m in methods))
    return types[0], (types[1] if len(types) > 1 else types[0])


def save_assessment(submission, candidate_id):
    eng = engine()
    unknown = [c.skill_id for c in submission.confidence if c.skill_id not in eng.name]
    if unknown:
        raise ValueError(f"Unknown skill IDs: {unknown}")
    career_id, career_name = resolve_career(submission.career_id)
    prefs = submission.preferences
    preferred, secondary = _resource_preferences(prefs.learning_methods)
    record = {
        "assessment_id": uuid4().hex,
        "candidate_id": candidate_id,
        "career_id": career_id,
        "career_name": career_name,
        "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "submitted",
        # Same shape as c4_engine's form_json so the roadmap engine can consume it later.
        "form": {
            "candidate_id": candidate_id,
            "career_id": career_id,
            "confidence": [c.model_dump() for c in submission.confidence],
            "preferences": {
                "learning_methods": prefs.learning_methods,
                "learning_methods_other": (prefs.learning_methods_other or "").strip() or None,
                "weekly_hours": prefs.weekly_hours,
                "weekly_study_hours": WEEKLY_HOURS[prefs.weekly_hours],
                "preferred_resource_type": preferred,
                "secondary_resource_type": secondary,
            },
            "activity": submission.experience.model_dump(),
        },
    }
    folder = assessments_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{record['assessment_id']}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
