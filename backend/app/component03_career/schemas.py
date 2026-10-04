"""Response contracts preserve the exported score and SHAP fields."""
from typing import Annotated, Literal
from pydantic import BaseModel, Field

class Skill(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    level: Annotated[float, Field(strict=True, ge=0, le=5, allow_inf_nan=False)]
    evidence: str | None = None

class Profile(BaseModel):
    schema_version: Literal["1.0"]
    candidate_id: Annotated[str, Field(min_length=1)]

class TechnicalProfile(Profile):
    technical_skills: Annotated[list[Skill], Field(min_length=1)]

class SoftProfile(Profile):
    soft_skills: Annotated[list[Skill], Field(min_length=1)]

class ShapFactor(BaseModel):
    feature: str
    meaning: str
    feature_value: float
    shap_score_points: float

class MatchedTechnology(BaseModel):
    technology: str
    candidate_level_0_to_5: float

class RankedJob(BaseModel):
    rank: int
    recommendation: str
    onet_soc_code: str
    job_title: str
    match_score_0_to_100: float = Field(description="Clipped prototype skill-evidence score; not a hiring probability.")
    raw_model_score: float
    direct_policy_score: float
    score_was_clipped: bool
    onet_url: str
    soft_evidence_importance_coverage: float
    matched_technologies: list[MatchedTechnology]
    unobserved_in_demand_technology_examples: list[str]
    explanation: str
    shap_baseline: float
    positive_shap_factors: list[ShapFactor]
    negative_shap_factors: list[ShapFactor]
    all_shap_factors: list[ShapFactor]

class Metadata(BaseModel):
    candidate_id: str
    onet_version: str
    model_type: str
    score_meaning: str
    eligible_occupations: int
    unrecognised_skills: list[str]
    mapping_audit: list[dict]

class BestJobResponse(BaseModel):
    candidate_id: str
    onet_version: str
    model_type: str
    score_meaning: str
    eligible_occupations: int
    unrecognised_skills: list[str]
    best_job: str = Field(description="Name of the highest-ranked job.")

class TopJob(BaseModel):
    ranking: Annotated[int, Field(ge=1, le=5)]
    job: str
    score: float = Field(ge=0, le=100, description="Prototype skill-evidence match score from 0 to 100; not a hiring probability.")

class TopJobsResponse(BaseModel):
    candidate_id: str
    onet_version: str
    model_type: str
    score_meaning: str
    eligible_occupations: int
    unrecognised_skills: list[str]
    jobs: Annotated[list[TopJob], Field(min_length=5, max_length=5)]

class ExplanationResponse(BaseModel):
    candidate_id: str
    onet_version: str
    model_type: str
    score_meaning: str
    eligible_occupations: int
    explanation: str = Field(description="Exported SHAP-based explanation for the highest-ranked job only.")

class ErrorResponse(BaseModel):
    detail: str
