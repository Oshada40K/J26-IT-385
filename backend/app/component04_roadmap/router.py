from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from . import c3_link, repository, service
from .errors import EvidenceError, LearningError, ModelsUnavailable
from .evidence_check import MAX_FILE_BYTES
from .schemas import (AnalysisResponse, AssessmentRecord, AssessmentSaved, AssessmentSubmission, Career, CareerCheck,
                      EvidenceDeleted, EvidenceRecord, EvidenceReview, EvidenceSubmission, LearningAttempt,
                      QuestionRequest, QuestionResponse, RecommendedCareer)

router = APIRouter(prefix="/api/roadmap", tags=["Learning Roadmap & Skill Gap"])
security = HTTPBearer(auto_error=False)


@router.get("/test")
def test_component():
    return {"component": "Learning Roadmap & Skill Gap", "status": "working"}


def _engine_or_503():
    try:
        return service.engine()
    except Exception as exc:  # missing data files or engine module
        raise HTTPException(503, f"Component 4 data is unavailable: {exc}") from exc


@router.get("/assessment/careers", response_model=list[Career],
            summary="IT careers supported by the Career Readiness Assessment")
async def assessment_careers():
    await run_in_threadpool(_engine_or_503)
    return service.careers()


def _candidate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
    if not credentials:
        return None
    # Reuse Component 01's candidate token check (read-only).
    from app.component01_skill.repository import candidate_for_token
    candidate = candidate_for_token(credentials.credentials)
    if not candidate:
        raise HTTPException(401, "Your CV session has expired. Upload your CV again in Component 01.")
    return candidate


def _owned_record(assessment_id, owner):
    record = repository.get(assessment_id)
    if not record:
        raise HTTPException(404, "Assessment not found.")
    # Assessments linked to a CV session are private to that candidate; anonymous ones are
    # reachable only through their unguessable assessment ID.
    if record["candidate_id"] and record["candidate_id"] != owner:
        raise HTTPException(403, "You cannot access another candidate's assessment.")
    return record


# ------------------------------------------------------------------ target career from Component 03
# The career is decided on the server from Component 03's recommendation for the signed-in CV candidate
# (c3_link.py). The student cannot choose another career, and there is no fallback to a manual choice or to
# C03's sample data when C03 has no result.
C3_C01_LINK = "Upload your CV in Component 01 first: your target career comes from Component 03's recommendation for your CV."


def _body_career(career_id=None, career_name=None):
    """A career still sent by an older client: None, or the C4 career it names (404 when C4 does not know it)."""
    if not career_id and not career_name:
        return None
    try:
        return service.resolve_career(career_id, career_name)[0]
    except service.CareerNotSupported as exc:
        raise HTTPException(404, str(exc)) from exc


async def _c3_career(request, owner, body_career=None):
    """(selection, c3_snapshot) from Component 03 for the owner. 401 not signed in, 409 no CV assessment yet,
    503 C03 unavailable, 504 C03 timed out, 422 no supported career, 409 body career differs from C03's."""
    if not owner:
        raise HTTPException(401, C3_C01_LINK)
    c1 = await run_in_threadpool(service.c1_profile, owner)
    if not c1["assessment_id"]:
        raise HTTPException(409, "No CV assessment was found for you yet. " + C3_C01_LINK)
    eng = await run_in_threadpool(_engine_or_503)
    try:
        selection, snapshot = await c3_link.selected_career(request, owner, eng.req_by_career)
    except c3_link.C3LinkError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    if body_career and body_career != snapshot["selected_career_id"]:
        raise HTTPException(409, f"Your target career is set by the system from Component 03's recommendation: "
                                 f"{eng.career_name[snapshot['selected_career_id']]}. A different career "
                                 f"({eng.career_name[body_career]}) cannot be used. Reload the page to continue "
                                 "with your recommended career.")
    return selection, snapshot


@router.post("/assessment/questions", response_model=QuestionResponse,
             summary="Choose 10-15 skills to rate for the career recommended by Component 03",
             description="Needs the CV session (Bearer token). The career comes from Component 03 on the server; "
                         "career_id / career_name in the body are optional and must name that career (409 otherwise).")
async def assessment_questions(body: QuestionRequest, request: Request,
                               owner: Annotated[str | None, Depends(_candidate)]):
    if not owner:
        raise HTTPException(401, C3_C01_LINK)
    await run_in_threadpool(_engine_or_503)
    body_career = _body_career(body.career_id, body.career_name)
    _, snapshot = await _c3_career(request, owner, body_career)
    career_id, career_name = service.resolve_career(snapshot["selected_career_id"])
    skills = service.assessment_skills(career_id, [s.model_dump() for s in body.c1_skills])
    return {"career_id": career_id, "career_name": career_name, "skills": skills}


@router.post("/assessment", response_model=AssessmentSaved, status_code=201,
             summary="Submit the Career Readiness Assessment form (career from Component 03)",
             description="Needs the CV session. Saves the Component 03 result used (c3_snapshot) with "
                         "career_source \"c3\". career_id in the body is optional; a different career -> 409.")
async def submit_assessment(body: AssessmentSubmission, request: Request,
                            owner: Annotated[str | None, Depends(_candidate)]):
    if body.candidate_id and body.candidate_id != owner:
        raise HTTPException(403, "You cannot submit an assessment for another candidate.")
    if not owner:
        raise HTTPException(401, C3_C01_LINK)
    await run_in_threadpool(_engine_or_503)
    body_career = _body_career(body.career_id)
    _, snapshot = await _c3_career(request, owner, body_career)
    try:
        return await run_in_threadpool(service.save_assessment, body, owner, snapshot)
    except service.CareerNotSupported as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/assessment/latest", response_model=AssessmentRecord | None,
            summary="Latest assessment for the signed-in CV candidate (null when there is none yet)")
async def latest_assessment(owner: Annotated[str | None, Depends(_candidate)]):
    if not owner:
        raise HTTPException(401, "Upload your CV in Component 01 to save and reload assessments.")
    return await run_in_threadpool(repository.latest_for, owner)


# Declared before /assessment/{assessment_id} so "recommended-career" is not read as an assessment ID.
@router.get("/assessment/recommended-career", response_model=RecommendedCareer,
            summary="The target career decided from Component 03 for the signed-in CV candidate",
            description="Read-only. Rule c4_engine.C3_CAREER_RULE: top5_supported (highest-ranked C03 job C4 supports) "
                        "or strict_top1. 401 not signed in, 409 no CV assessment yet, 422 no supported career in "
                        "C03's top 5, 503 Component 03 unavailable, 504 Component 03 timed out.")
async def recommended_career(request: Request, owner: Annotated[str | None, Depends(_candidate)]):
    _, snapshot = await _c3_career(request, owner)
    return service.c3_view(snapshot)


@router.get("/assessment/{assessment_id}", response_model=AssessmentRecord, summary="Stored assessment answers")
async def get_assessment(assessment_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    return await run_in_threadpool(_owned_record, assessment_id, owner)


@router.get("/assessment/{assessment_id}/career-check", response_model=CareerCheck,
            summary="Has Component 03's recommended career changed since this assessment? (never changes it)",
            description="Compares the saved career with Component 03's current selection, e.g. after a new CV. "
                        "The UI asks the student to regenerate; nothing is changed automatically.")
async def career_check(assessment_id: str, request: Request, owner: Annotated[str | None, Depends(_candidate)]):
    record = await run_in_threadpool(_owned_record, assessment_id, owner)
    _, snapshot = await _c3_career(request, owner)
    current = service.c3_view(snapshot)
    saved_view = service.c3_view(record.get("c3_snapshot"))
    legacy = record["career_source"] != c3_link.CAREER_SOURCE_C3
    changed = current["career_id"] != record["career_id"]
    message = (f"Component 03 now recommends {current['career_name']} for your CV, but this roadmap was built for "
               f"{record['career_name']}." if changed else None)
    return {"assessment_id": assessment_id, "changed": changed, "legacy": legacy,
            "saved": {"career_id": record["career_id"], "career_name": record["career_name"],
                      "career_source": record["career_source"],
                      "c3_rank": saved_view["c3_rank"] if saved_view else None,
                      "c3_score": saved_view["c3_score"] if saved_view else None},
            "current": current, "message": message}


@router.get("/analysis/{assessment_id}", response_model=AnalysisResponse,
            summary="Skill gaps, priorities, resources, roadmap and readiness score for an assessment")
async def assessment_analysis(assessment_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    record = await run_in_threadpool(_owned_record, assessment_id, owner)
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.analysis, record)
    except ModelsUnavailable as exc:
        raise HTTPException(503, f"{exc}. The assessment was saved; the analysis will be available once the trained "
                                 "models are present in backend/app/component04_roadmap/trained_models/.") from exc
    except service.CareerNotSupported as exc:
        raise HTTPException(404, str(exc)) from exc


async def _evidence_body(request):
    """Reads multipart/form-data (with an optional "file") or JSON. Returns (submission, upload)."""
    upload = None
    if request.headers.get("content-type", "").startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
        form = await request.form()
        data = {k: form.get(k) for k in ("candidate_id", "skill_id", "proof_type", "type", "url", "description")}
        file = form.get("file")
        if hasattr(file, "read"):
            upload = (file.filename or "", await file.read(MAX_FILE_BYTES + 1))   # +1 byte detects oversize files
            await file.close()
    else:
        try:
            data = await request.json()
        except ValueError:
            raise HTTPException(400, "Send the proof as multipart/form-data or JSON.")
        if not isinstance(data, dict):
            raise HTTPException(400, "Send the proof as multipart/form-data or JSON.")
    try:
        return EvidenceSubmission(**{k: v for k, v in data.items() if v not in (None, "")}), upload
    except ValidationError as exc:
        error = exc.errors()[0]
        raise HTTPException(400, f"{'.'.join(str(x) for x in error['loc']) or 'body'}: {error['msg']}") from exc


@router.post("/evidence", response_model=EvidenceRecord, status_code=201,
             summary="Submit optional proof (GitHub repository, certificate link or certificate file) for a skill",
             description="multipart/form-data: candidate_id, skill_id, proof_type (github | certificate_link | "
                         "certificate_file), url or file (PDF/PNG/JPG, max 5 MB), description (optional). JSON with "
                         "the same fields (\"type\" or \"proof_type\") is also accepted. Runs the simple checks and "
                         "returns the evidence with the regenerated roadmap in \"analysis\".")
async def submit_evidence(request: Request, owner: Annotated[str | None, Depends(_candidate)]):
    if not owner:
        raise HTTPException(401, "Upload your CV in Component 01 before adding proof.")
    body, upload = await _evidence_body(request)
    if body.candidate_id and body.candidate_id != owner:
        raise HTTPException(403, "You cannot add proof for another candidate.")
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.submit_evidence, body, owner, upload)
    except EvidenceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.get("/evidence/{candidate_id}", response_model=list[EvidenceRecord], summary="The student's evidence")
async def list_evidence(candidate_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    if not owner or owner != candidate_id:
        raise HTTPException(403 if owner else 401, "You can only see your own evidence.")
    await run_in_threadpool(_engine_or_503)
    return await run_in_threadpool(service.list_evidence, candidate_id)


@router.post("/evidence/{evidence_id}/recheck", response_model=EvidenceRecord,
             summary="Check your own GitHub / certificate link again and return the regenerated roadmap",
             description="Use when GitHub could not be reached, or after adding your GitHub username in Component 01. "
                         "Uploaded files cannot be re-checked (400); decided proof cannot be re-checked (409).")
async def recheck_evidence(evidence_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    if not owner:
        raise HTTPException(401, "Upload your CV in Component 01 to manage your evidence.")
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.recheck_evidence, evidence_id, owner)
    except EvidenceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post("/evidence/{evidence_id}/review", response_model=EvidenceRecord,
             summary="Reviewer: approve or reject proof (only when C4_ALLOW_REVIEW=1)",
             description="Disabled (403) unless the backend runs with C4_ALLOW_REVIEW=1. There is no reviewer login "
                         "yet, so keep it off outside local testing. Approve sets a provisional level (default and "
                         "maximum 3/5); reject removes the proof's level. Returns the regenerated roadmap.")
async def review_evidence(evidence_id: str, body: EvidenceReview):
    if not service.review_allowed():
        raise HTTPException(403, "Reviewing is turned off. Set C4_ALLOW_REVIEW=1 on the backend to enable it.")
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.review_evidence, evidence_id, body.decision, body.level, body.note)
    except EvidenceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.delete("/evidence/{evidence_id}", response_model=EvidenceDeleted,
               summary="Remove your own evidence and return the regenerated roadmap")
async def delete_evidence(evidence_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    if not owner:
        raise HTTPException(401, "Upload your CV in Component 01 to manage your evidence.")
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.delete_evidence, evidence_id, owner)
    except EvidenceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc



# ------------------------------------------------------------------ adaptive learning tutor (new, additive)
async def _learning(fn, assessment_id, owner, *args):
    """Shared wrapper: the assessment must exist and belong to the signed-in candidate (learning progress is
    private, so anonymous assessments cannot use the tutor)."""
    from . import learning                                   # imported lazily, like the engine
    record = await run_in_threadpool(_owned_record, assessment_id, owner)
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(getattr(learning, fn), record, owner, *args)
    except LearningError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except ModelsUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/learning/{assessment_id}", summary="Adaptive learning plan: per-skill placement, progress and next activity")
async def learning_plan(assessment_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    return await _learning("plan", assessment_id, owner)


@router.get("/learning/{assessment_id}/activity",
            summary="Open a personalised lesson or a diagnostic (questions are sent without answers)")
async def learning_activity(assessment_id: str, skill_id: str, owner: Annotated[str | None, Depends(_candidate)],
                            kind: str = "lesson", topic_id: str | None = None, mode: str | None = None,
                            scope: str | None = None):
    if kind not in ("lesson", "diagnostic"):
        raise HTTPException(400, "kind must be 'lesson' or 'diagnostic'.")
    if mode not in (None, "standard", "foundation", "focused", "challenge"):
        raise HTTPException(400, "Unknown lesson mode.")
    if scope not in (None, "checkpoint", "claim", "test_out"):
        raise HTTPException(400, "Unknown diagnostic scope.")
    if kind == "lesson" and not topic_id:
        raise HTTPException(400, "topic_id is required for a lesson.")
    return await _learning("open_activity", assessment_id, owner, skill_id, topic_id, kind, mode, scope)


@router.post("/learning/{assessment_id}/attempts",
             summary="Submit a quiz, diagnostic or practical self-check; returns feedback, the adaptive decision and the regenerated roadmap")
async def learning_attempt(assessment_id: str, body: LearningAttempt, owner: Annotated[str | None, Depends(_candidate)]):
    return await _learning("submit_attempt", assessment_id, owner, body.skill_id, body.kind, body.answers,
                           body.topic_id, body.scope)


@router.get("/learning/{assessment_id}/history", summary="The student's quiz attempts and roadmap-change events")
async def learning_history(assessment_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    return await _learning("history", assessment_id, owner)


@router.post("/learning/{assessment_id}/generate/{skill_id}",
             summary="Optional: create validated AI lessons for a roadmap skill without curated lessons (needs C4_LLM_API_KEY)")
async def learning_generate(assessment_id: str, skill_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    return await _learning("generate_lessons", assessment_id, owner, skill_id)
