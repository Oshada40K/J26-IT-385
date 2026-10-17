from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from . import repository, service
from .errors import ModelsUnavailable
from .schemas import AssessmentRecord, AssessmentSaved, AssessmentSubmission, Career, QuestionRequest, QuestionResponse

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


@router.get("/analysis/{assessment_id}",
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
