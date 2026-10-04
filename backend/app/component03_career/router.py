from fastapi import APIRouter, Request

from . import service
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
async def best_job(request: Request):
    result = await service.recommend(request)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations", "unrecognised_skills"]
    return {**{key: result[key] for key in fields}, "best_job": result["best_job"]["job_title"]}

@router.get("/top-jobs", response_model=TopJobsResponse, responses=ERRORS,
            summary="Get exactly five ranked jobs including the best match")
async def top_jobs(request: Request):
    result = await service.recommend(request)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations", "unrecognised_skills"]
    jobs = [result["best_job"], *result["alternative_jobs"]]
    return {
        **{key: result[key] for key in fields},
        "jobs": [{"ranking": job["rank"], "job": job["job_title"], "score": job["match_score_0_to_100"]} for job in jobs],
    }

@router.get("/explanation", response_model=ExplanationResponse, responses=ERRORS,
            summary="Get the top job's SHAP-based explanation",
            description="Returns five model metadata fields and the exported explanation text for the highest-ranked job.")
async def explanation(request: Request):
    result = await service.recommend(request)
    fields = ["candidate_id", "onet_version", "model_type", "score_meaning", "eligible_occupations"]
    return {**{key: result[key] for key in fields}, "explanation": result["best_job"]["explanation"]}
