# Owner: Dewmi - Component 04.
# Career Readiness Assessment: chooses the skills to ask about, stores submissions and builds the
# explainable analysis (gap analysis, priorities, resources, roadmap, readiness) from the latest
# Component 01 CV assessment and the stored form. See analysis.py for the methods.
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from . import repository
from .errors import ModelsUnavailable

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


@lru_cache(maxsize=1)
def engine():
    # Imported lazily so a data problem only affects C4 endpoints, never app startup.
    # Trained models are loaded on the first analysis, not here.
    from .analysis import C4Analyzer
    return C4Analyzer()


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


def c1_profile(candidate_id):
    """Latest Component 01 CV assessment in c4_engine's c1_json format (read-only)."""
    empty = {"candidate_id": candidate_id, "skills": [], "assessment_id": None, "created_at": None}
    if not candidate_id:
        return empty
    from app.component01_skill.repository import latest_assessment
    details = latest_assessment(candidate_id)
    if not details:
        return empty
    skills = [{"name": s["name"], "level": s.get("level", 0), "confidence": s.get("confidence")}
              for s in details.get("skills", []) if s.get("name")]
    return {"candidate_id": candidate_id, "skills": skills,
            "assessment_id": details.get("assessment_id"), "created_at": details.get("created_at")}


def _readiness_snapshot(c1, form):
    try:
        return engine().analyze_assessment(c1, form)["readiness"]["score"]
    except ModelsUnavailable:
        return None


def save_assessment(submission, candidate_id):
    eng = engine()
    unknown = [c.skill_id for c in submission.confidence if c.skill_id not in eng.name]
    if unknown:
        raise ValueError(f"Unknown skill IDs: {unknown}")
    career_id, career_name = resolve_career(submission.career_id)
    prefs = submission.preferences
    preferred, secondary = _resource_preferences(prefs.learning_methods)
    # Same shape as c4_engine's form_json, plus the raw form answers.
    form = {
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
    }
    c1 = c1_profile(candidate_id)
    previous = repository.latest_for(candidate_id) if candidate_id else None
    record = {
        "assessment_id": uuid4().hex,
        "candidate_id": candidate_id,
        "career_id": career_id,
        "career_name": career_name,
        "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "previous_assessment_id": previous["assessment_id"] if previous else None,
        "c1_assessment_id": c1["assessment_id"],
        "readiness_score": _readiness_snapshot(c1, form),
        "form": form,
    }
    repository.save(record)
    return {**record, "status": "submitted"}


def analysis(record):
    """Recomputed on every request from the latest CV assessment, so the roadmap updates when the
    student's CV skills change (Component 01) or when they submit an updated assessment."""
    c1 = c1_profile(record["candidate_id"])
    out = engine().analyze_assessment(c1, record["form"])
    previous = repository.get(record["previous_assessment_id"]) if record.get("previous_assessment_id") else None
    changes = []
    if record.get("c1_assessment_id") and c1["assessment_id"] and c1["assessment_id"] != record["c1_assessment_id"]:
        changes.append("Your CV assessment was updated after you submitted this form. The analysis uses your latest CV evidence.")
    out["assessment"] = {
        "assessment_id": record["assessment_id"], "submitted_at": record["submitted_at"],
        "readiness_at_submission": record.get("readiness_score"),
        "previous": None if not previous else {
            "assessment_id": previous["assessment_id"], "submitted_at": previous["submitted_at"],
            "career_name": previous["career_name"], "readiness_score": previous.get("readiness_score")},
        "cv_assessment_id": c1["assessment_id"], "cv_assessed_at": c1["created_at"],
        "history": repository.history(record["candidate_id"]),
        "changes": changes,
    }
    return out
