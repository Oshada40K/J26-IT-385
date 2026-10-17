# Owner: Dewmi - Component 04.
# Career Readiness Assessment: chooses the skills to ask about, stores submissions and builds the
# explainable analysis (gap analysis, priorities, resources, roadmap, readiness) from the latest
# Component 01 CV assessment and the stored form. See analysis.py for the methods.
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import httpx

from . import evidence_check, repository
from .errors import EvidenceError, ModelsUnavailable

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


def cv_levels(c1):
    """{skill_id: highest Component 01 level (0-5)} for the CV skills in the C4 catalogue."""
    eng, levels = engine(), {}
    for skill in c1.get("skills", []):
        sid, _ = eng.map_skill(skill["name"])
        if sid:
            levels[sid] = max(levels.get(sid, 0.0), float(skill.get("level") or 0))
    return levels


# Evidence status shown for a skill with several items (best wins) and source labels for the UI.
EVIDENCE_STATUS_ORDER = {"rejected": 0, "pending": 1, "provisional": 2, "verified": 3}
EVIDENCE_SOURCE = {"github": "GitHub (provisional)", "certificate_link": "Certificate (provisional)",
                   "certificate_file": "Certificate (pending review)"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_file_name(name):
    """Display name only (the stored file is named after the evidence ID)."""
    return re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name or "certificate").name)[:100]


def public_evidence(item):
    """Evidence as returned to the student (the private file path is never exposed)."""
    out = {k: v for k, v in item.items() if k not in ("file_path", "verified_by_c1_assessment_id")}
    out["proof_type"] = item.get("proof_type") or item["type"]
    out["created_at"] = item.get("created_at") or item["submitted_at"]
    out["skill_name"] = engine().name.get(item["skill_id"], item["skill_id"])
    return out


def submit_evidence(submission, candidate_id, upload=None):
    """Store optional proof for a skill, run the simple checks (evidence_check.py), send it to
    Component 01 when connected, and regenerate the roadmap. upload = (file_name, bytes) for
    certificate_file. Proof is optional and never blocks the roadmap."""
    eng = engine()
    if submission.skill_id not in eng.name:
        raise EvidenceError(f"Unknown skill_id '{submission.skill_id}'. Use a skill from the C4 skills catalogue.")
    proof_type = submission.proof_type or submission.type
    file_name, content = upload or (None, None)
    url = evidence_check.validate_submission(proof_type, submission.url, file_name, content, submission.description)
    evidence_id, now, stored = uuid4().hex, _now(), None
    if proof_type == "certificate_file":                     # private folder, never a public/static one
        folder = repository.evidence_dir()
        folder.mkdir(parents=True, exist_ok=True)
        stored = evidence_id + evidence_check.file_extension(file_name, content)
        (folder / stored).write_bytes(content)
    record = {
        "evidence_id": evidence_id, "candidate_id": candidate_id, "skill_id": submission.skill_id,
        "type": proof_type, "proof_type": proof_type, "url": url or "", "file_path": stored,
        "file_name": _safe_file_name(file_name) if stored else None,
        "description": (submission.description or "").strip() or None,
        **evidence_check.check(proof_type, url, eng.name[submission.skill_id]),
        "submitted_at": now, "created_at": now,
        "cv_level_at_submission": cv_levels(c1_profile(candidate_id)).get(submission.skill_id, 0.0),
    }
    repository.save_evidence(record)
    send_to_component01(record)
    return {**public_evidence(repository.get_evidence(evidence_id)), "analysis": regenerate(candidate_id)}


def list_evidence(candidate_id):
    return [public_evidence(item) for item in repository.evidence_list(candidate_id)]


def delete_evidence(evidence_id, owner):
    """Students can remove their own evidence; the roadmap is regenerated without it."""
    item = repository.get_evidence(evidence_id)
    if not item:
        raise EvidenceError("Evidence not found.", 404)
    if item["candidate_id"] != owner:
        raise EvidenceError("You can only remove your own evidence.", 403)
    repository.delete_evidence(evidence_id)
    return {"deleted": True, "evidence_id": evidence_id, "analysis": regenerate(owner)}


def send_to_component01(evidence):
    """Ask Component 01 (the main verifier) to verify the proof.

    TODO(C1 integration): agree the contract with the Component 01 owner, then set the env var
    C1_EVIDENCE_ENDPOINT to the Component 01 URL. The evidence metadata (not the private file) is
    POSTed as JSON; a reply {"level": 0-5} marks the evidence "verified" at that level. When the
    variable is not set this is skipped silently and the provisional checks still apply.
    Returns the verified level or None."""
    endpoint = os.getenv("C1_EVIDENCE_ENDPOINT", "").strip()
    if not endpoint:
        return None
    payload = {k: evidence.get(k) for k in ("evidence_id", "candidate_id", "skill_id", "proof_type", "url",
                                            "file_name", "description")}
    try:
        response = httpx.post(endpoint, json=payload, timeout=5)
        response.raise_for_status()
        level = response.json().get("level")
    except (httpx.HTTPError, ValueError, AttributeError):
        return None                                          # Component 01 unavailable: keep the C4 result
    if isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 <= level <= 5:
        return None
    repository.update_evidence(evidence["evidence_id"], status="verified", verified_level=float(level),
                               verified_at=_now(), check_details="Verified by Component 01.")
    return float(level)


def _usable_level(item):
    """Level (0-5) this evidence may add. C4's own checks never go above the provisional level."""
    proof_type = item.get("proof_type") or item["type"]
    if item["status"] == "verified":
        return item.get("verified_level")                   # from Component 01 (None: the CV already shows it)
    if item["status"] == "provisional":
        return min(item.get("provisional_level") or 0, evidence_check.PROVISIONAL_LEVEL_LINK)
    if item["status"] == "pending" and proof_type == "certificate_file":
        return evidence_check.PROVISIONAL_LEVEL_FILE
    return None                                              # rejected, or a pending link/repository


def evidence_summary(candidate_id):
    """{skill_id: {status, level, source, detail, evidence_id}} using the best evidence per skill."""
    out = {}
    for item in repository.evidence_list(candidate_id):     # oldest first, so later items win ties
        proof_type = item.get("proof_type") or item["type"]
        entry = out.setdefault(item["skill_id"], {"status": "none", "level": None, "source": None,
                                                  "detail": None, "evidence_id": None, "rank": -1})
        rank = EVIDENCE_STATUS_ORDER.get(item["status"], 0)
        if rank >= entry["rank"]:
            entry.update(status=item["status"], detail=item.get("check_details"),
                         evidence_id=item["evidence_id"], rank=rank)
        level = _usable_level(item)
        if level is not None and (entry["level"] is None or level > entry["level"]):
            entry["level"] = float(level)
            entry["source"] = "Component 01 (verified)" if item["status"] == "verified" else EVIDENCE_SOURCE[proof_type]
    for entry in out.values():
        entry.pop("rank")
    return out


def regenerate(candidate_id):
    """Regenerated analysis for the candidate's latest assessment (None if there is none yet)."""
    record = repository.latest_for(candidate_id)
    if not record:
        return None
    try:
        return analysis(record)
    except ModelsUnavailable:
        return None


def sync_evidence(candidate_id, c1=None):
    """Pending or provisional proof becomes "verified" when the latest Component 01 CV level for that
    skill is higher than when the proof was submitted. Returns the newly verified skill IDs."""
    open_items = [e for e in repository.evidence_list(candidate_id) if e["status"] in ("pending", "provisional")]
    if not open_items:
        return []
    c1 = c1 or c1_profile(candidate_id)
    levels, now, verified = cv_levels(c1), _now(), []
    for item in open_items:
        if levels.get(item["skill_id"], 0.0) > item["cv_level_at_submission"]:
            repository.set_evidence_status(item["evidence_id"], "verified", now, c1["assessment_id"])
            verified.append(item["skill_id"])
    return verified


def on_c1_assessment_updated(candidate_id):
    """Call when Component 01 saves new CV results for candidate_id: verifies pending proof and
    regenerates the roadmap with analysis() (the existing regeneration path).

    TODO(C1 integration): Component 01 should call this right after
    `repository.save_assessment(...)` in app/component01_skill/services/profile_service.py.
    Component 01 belongs to another team member, so it is not connected here. Until it is,
    analysis() runs sync_evidence() before every C4 analysis, so verification still happens the
    next time the student opens their roadmap."""
    verified = sync_evidence(candidate_id)
    record = repository.latest_for(candidate_id)
    return {"verified_skills": verified, "analysis": analysis(record) if record else None}


def analysis(record):
    """Recomputed on every request from the latest CV assessment, so the roadmap updates when the
    student's CV skills change (Component 01) or when they submit an updated assessment.
    Evidence is optional: with none uploaded the roadmap is built from CV evidence + the form."""
    c1 = c1_profile(record["candidate_id"])
    sync_evidence(record["candidate_id"], c1)        # fallback until Component 01 calls on_c1_assessment_updated
    evidence = evidence_summary(record["candidate_id"])
    out = engine().analyze_assessment(c1, record["form"], evidence)
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
