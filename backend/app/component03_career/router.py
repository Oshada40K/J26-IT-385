"""Component 3 REST APIs (see all of them at /docs).

All three endpoints run the SAME recommendation (service.recommend) and return a
different part of it, so the results are always consistent with each other:
  GET /api/career/best-job     -> the best job title
  GET /api/career/top-jobs     -> exactly 5 ranked jobs with 0-100 match scores
  GET /api/career/explanation  -> why the best job was chosen (SHAP + plain language)
Pass ?candidate_id=... with the user's login token to use their real CV profile.
"""
from fastapi import APIRouter, Query, Request

from . import service
from .explanation_text import explanation_details
from .schemas import BestJobResponse, ErrorResponse, ExplanationResponse, TopJobsResponse

router = APIRouter(prefix="/api/career", tags=["Explainable Career Recommendation"])
ERRORS = {502: {"model": ErrorResponse, "description": "Invalid or unavailable upstream profile"},
          504: {"model": ErrorResponse, "description": "Upstream profile timeout"},
          500: {"model": ErrorResponse, "description": "Inference failure"}}

@router.get("/test")
def test_component():
    return {"component": "Explainable Career Recommendation", "status": "working"}

@router.get("/best-job", response_model=BestJobResponse, responses=ERRORS,
            summary="Get the highest-ranked job name and model metadata")
async def best_job(request: Request, candidate_id: str | None = Query(default=None, min_length=1)):
    result = await service.recommend(request, candidate_id)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations", "unrecognised_skills"]
    return {**{key: result[key] for key in fields}, "best_job": result["best_job"]["job_title"]}

@router.get("/top-jobs", response_model=TopJobsResponse, responses=ERRORS,
            summary="Get exactly five ranked jobs including the best match")
async def top_jobs(request: Request, candidate_id: str | None = Query(default=None, min_length=1)):
    result = await service.recommend(request, candidate_id)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations", "unrecognised_skills"]
    jobs = [result["best_job"], *result["alternative_jobs"]]
    return {
        **{key: result[key] for key in fields},
        "jobs": [{"ranking": job["rank"], "job": job["job_title"], "score": job["match_score_0_to_100"]} for job in jobs],
    }

@router.get("/explanation", response_model=ExplanationResponse, responses=ERRORS,
            summary="Get the top job's SHAP-based explanation",
            description="Returns five model metadata fields and the exported explanation text for the highest-ranked job.")
async def explanation(request: Request, candidate_id: str | None = Query(default=None, min_length=1)):
    result = await service.recommend(request, candidate_id)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations"]
    return {**{key: result[key] for key in fields}, "explanation": result["best_job"]["explanation"],
            **explanation_details(result["best_job"], result["eligible_occupations"])}
