# Owner: Dewmi - Component 04.
"""Read-only link to Component 03: the target career is decided on the server from C03's recommendation for the
signed-in CV candidate. The student cannot choose another career.

  _call_c03                 the ONLY place C04 calls Component 03 (its public service.recommend, unchanged).
                            Tests replace this function with a stub; unit tests never run the real model.
  c3_recommendation         C03's five ranked jobs in a small fixed shape, or a clear C3LinkError.
  selected_career           c3_recommendation + c4_engine.select_career_from_c3 (the single selection rule)
                            -> the selection shown to the student and the c3_snapshot stored with the assessment.

C03 is called with the student's own request, so C03 forwards the same Bearer token to Component 01
(/api/component01/skills/{candidate_id}/details, which checks the token belongs to candidate_id). candidate_id
is always the signed-in owner; C04 never calls C03 with candidate_id=None (that would use C03's sample data).
"""
import asyncio
import logging
import math
from datetime import datetime, timezone

from fastapi import HTTPException

from . import c4_engine
from .c4_engine import NoSupportedCareer, select_career_from_c3

logger = logging.getLogger(__name__)

C3_TIMEOUT_SECONDS = 30.0        # whole C03 call (its own upstream fetches time out after 10 s each)
CAREER_SOURCE_C3 = "c3"
CAREER_SOURCE_LEGACY = "student_selected_legacy"


class C3LinkError(Exception):
    """A clear, student-facing reason why the target career cannot be taken from Component 03."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


async def _call_c03(request, candidate_id):
    # Imported lazily: loading C03 pulls in its model libraries, which C04 needs only at this point.
    from app.component03_career import service as c3_service
    return await c3_service.recommend(request, candidate_id)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


async def c3_recommendation(request, candidate_id):
    """{onet_version, model_type, jobs: [{rank, onet_soc_code, job_title, score}]} for candidate_id (5 jobs)."""
    if not candidate_id:
        raise C3LinkError("Upload your CV in Component 01 first: your target career comes from Component 03's "
                          "recommendation for your CV.", 401)
    try:
        result = await asyncio.wait_for(_call_c03(request, candidate_id), C3_TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, TimeoutError) as exc:          # the same class on Python 3.11+
        raise C3LinkError(f"Component 03 did not answer within {C3_TIMEOUT_SECONDS:g} seconds. Try again in a "
                          "moment.", 504) from exc
    except HTTPException as exc:
        if exc.status_code == 504:
            raise C3LinkError(f"Component 03 timed out: {exc.detail}", 504) from exc
        raise C3LinkError(f"Component 03 could not recommend a career for you: {exc.detail}", 503) from exc
    except Exception as exc:                     # e.g. C03 not started (no career client): never fall back
        logger.exception("Component 03 call failed")
        raise C3LinkError("Component 03 is unavailable, so your target career cannot be set. Try again later.",
                          503) from exc
    try:
        if result.get("candidate_id") not in (None, candidate_id):
            raise ValueError("candidate mismatch")
        jobs = [{"rank": int(j["rank"]), "onet_soc_code": str(j["onet_soc_code"]), "job_title": str(j["job_title"]),
                 "score": float(j["match_score_0_to_100"])}
                for j in [result["best_job"], *result["alternative_jobs"]]]
        if not jobs or not all(_number(j["score"]) for j in jobs):
            raise ValueError("no ranked jobs")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise C3LinkError("Component 03 returned an unexpected result, so your target career cannot be set.",
                          503) from exc
    return {"onet_version": result.get("onet_version"), "model_type": result.get("model_type"),
            "jobs": sorted(jobs, key=lambda j: j["rank"])}


def snapshot_from(recommendation, supported_ids, rule=None, now=None):
    """Selection + the c3_snapshot stored with the assessment. Raises C3LinkError(422) when the rule finds no
    supported career (nothing is saved and there is no manual fallback)."""
    rule = rule or c4_engine.C3_CAREER_RULE
    try:
        selection = select_career_from_c3(recommendation["jobs"], supported_ids, rule)
    except NoSupportedCareer as exc:
        titles = ", ".join(f"#{j['rank']} {j['job_title']}" for j in recommendation["jobs"])
        raise C3LinkError(f"{exc}. Component 03's careers for your CV ({titles}) are outside the 32 IT careers "
                          "this roadmap covers, so no roadmap can be built. Update your CV in Component 01 to get "
                          "new recommendations.", 422) from exc
    snapshot = {
        "onet_version": recommendation.get("onet_version"),
        "model_type": recommendation.get("model_type"),
        "retrieved_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "rule": selection["rule"],
        "jobs": [{k: j[k] for k in ("rank", "onet_soc_code", "job_title", "score")} for j in recommendation["jobs"]],
        "selected_rank": selection["rank"],
        "selected_career_id": selection["career_id"],
        "top1_supported": selection["top1_supported"],
        "fallback_used": selection["fallback_used"],
        "fallback_reason": selection["fallback_reason"],
    }
    return selection, snapshot


async def selected_career(request, candidate_id, supported_ids, rule=None):
    """(selection, c3_snapshot) for the signed-in candidate, decided on the server from Component 03."""
    return snapshot_from(await c3_recommendation(request, candidate_id), supported_ids, rule)


def snapshot_to_c3_json(snapshot, candidate_id):
    """Stored c3_snapshot -> c4_engine's c3_json "top_jobs" shape (only when passed to student_from_json)."""
    return {"top_jobs": {"candidate_id": candidate_id, "jobs": [
        {"ranking": j["rank"], "job": j["job_title"], "score": j["score"], "onet_soc_code": j["onet_soc_code"]}
        for j in snapshot["jobs"]]}}


def public_view(snapshot, supported_ids, career_names):
    """The C03 source shown to the student (recommended-career, analysis, career-check): the selected career,
    the C03 rank/score it came from, C03's #1 and all five jobs with "supported" and "selected"."""
    jobs = [dict(j, supported=j["onet_soc_code"] in supported_ids,
                 selected=j["onet_soc_code"] == snapshot["selected_career_id"]) for j in snapshot["jobs"]]
    selected = next((j for j in jobs if j["selected"]), {"job_title": None, "score": None})
    return {
        "career_id": snapshot["selected_career_id"],
        "career_name": career_names.get(snapshot["selected_career_id"], selected["job_title"]),
        "c3_rank": snapshot["selected_rank"], "c3_score": selected["score"],
        "c3_top1": jobs[0], "top1_supported": snapshot["top1_supported"],
        "fallback_used": snapshot["fallback_used"], "fallback_reason": snapshot["fallback_reason"],
        "rule": snapshot["rule"], "onet_version": snapshot.get("onet_version"),
        "model_type": snapshot.get("model_type"), "retrieved_at": snapshot.get("retrieved_at"),
        "jobs": jobs,
    }
