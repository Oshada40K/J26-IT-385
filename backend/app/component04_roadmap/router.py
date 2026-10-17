from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from . import repository, service
from .errors import EvidenceError, ModelsUnavailable
from .evidence_check import MAX_FILE_BYTES
from .schemas import (AnalysisResponse, AssessmentRecord, AssessmentSaved, AssessmentSubmission, Career, EvidenceDeleted,
                      EvidenceRecord, EvidenceSubmission, QuestionRequest, QuestionResponse)

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


@router.post("/assessment/questions", response_model=QuestionResponse,
             summary="Choose 10-15 skills to rate for the selected career")
async def assessment_questions(body: QuestionRequest):
    await run_in_threadpool(_engine_or_503)
    try:
        career_id, career_name = service.resolve_career(body.career_id, body.career_name)
    except service.CareerNotSupported as exc:
        raise HTTPException(404, str(exc)) from exc
    skills = service.assessment_skills(career_id, [s.model_dump() for s in body.c1_skills])
    return {"career_id": career_id, "career_name": career_name, "skills": skills}


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


@router.post("/assessment", response_model=AssessmentSaved, status_code=201,
             summary="Submit the Career Readiness Assessment form")
async def submit_assessment(body: AssessmentSubmission, owner: Annotated[str | None, Depends(_candidate)]):
    if body.candidate_id and body.candidate_id != owner:
        raise HTTPException(403, "You cannot submit an assessment for another candidate.")
    await run_in_threadpool(_engine_or_503)
    try:
        return await run_in_threadpool(service.save_assessment, body, owner)
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


@router.get("/assessment/{assessment_id}", response_model=AssessmentRecord, summary="Stored assessment answers")
async def get_assessment(assessment_id: str, owner: Annotated[str | None, Depends(_candidate)]):
    return await run_in_threadpool(_owned_record, assessment_id, owner)


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
