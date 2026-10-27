"""Response contracts preserve the exported score and SHAP fields.

Pydantic models that validate every input and output. Bad data (e.g. a skill level
outside 0-5, or an empty candidate ID) is rejected with an error instead of producing
a wrong recommendation. They also generate the API documentation at /docs.
"""
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

class AssessmentSkill(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    level: Annotated[float, Field(strict=True, ge=1, le=5, allow_inf_nan=False)]
    confidence: Literal['low', 'medium', 'high']
    status: str
    reason: str
    evidence: list[dict]

class TechnicalAssessment(BaseModel):
    assessment_method: Literal['cv_evidence_rubric_v1']
    model_version: Annotated[str, Field(min_length=1)]
    candidate_id: Annotated[str, Field(min_length=1)]
    assessment_id: Annotated[str, Field(min_length=1)]
    status: Literal['completed']
    skills: Annotated[list[AssessmentSkill], Field(min_length=1)]

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

class ExplanationFactor(BaseModel):
    label: str
    points: float
    effect: Literal["positive", "negative"]

class ExplanationResponse(BaseModel):
    candidate_id: str
    onet_version: str
    model_type: str
    score_meaning: str
    eligible_occupations: int
    explanation: str = Field(description="Exported SHAP-based explanation for the highest-ranked job only.")
    friendly_explanation: list[str] = Field(description="Plain-language reasons for the highest-ranked job, derived from the same SHAP output.")
    key_reasons: list[str] = Field(description="The SHAP-derived reasons only, without the summary, matched-skill and learning sentences.")
    match_score: float = Field(description="Displayed 0-100 match score of the highest-ranked job.")
    matched_technologies: list[str] = Field(description="Candidate technologies used in the highest-ranked job, strongest first.")
    skills_to_learn: list[str] = Field(description="In-demand technologies for the job that the candidate has not shown.")
    factors: list[ExplanationFactor] = Field(description="Top SHAP contributions with plain-language labels.")

class ErrorResponse(BaseModel):
    detail: str
