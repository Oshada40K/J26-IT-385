# Owner: Dewmi - Component 04.
# Request/response schemas for the C4 Career Readiness Assessment form.
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LearningMethod = Literal[
    "online_courses", "video_tutorials", "reading", "hands_on_projects",
    "interactive_exercises", "instructor_led", "group_learning", "other",
]
WeeklyHours = Literal["1-3", "4-6", "7-10", "11-15", "15+"]


class Career(BaseModel):
    career_id: str
    career_name: str


class C1Skill(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: float | None = Field(default=None, ge=0, le=5)


class QuestionRequest(BaseModel):
    career_id: str | None = None
    career_name: str | None = None
    c1_skills: list[C1Skill] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def needs_career(self):
        if not self.career_id and not self.career_name:
            raise ValueError("Provide career_id or career_name.")
        return self


class AssessmentSkill(BaseModel):
    skill_id: str
    skill_name: str
    skill_level: str
    in_cv: bool
    career_requirement: bool


class QuestionResponse(BaseModel):
    career_id: str
    career_name: str
    skills: list[AssessmentSkill]


class SkillRating(BaseModel):
    skill_id: str
    # 1-5 confidence rating; null means "Not studied" (the format c4_engine expects).
    rating: int | None = Field(ge=1, le=5)


class Preferences(BaseModel):
    learning_methods: list[LearningMethod] = Field(min_length=1)
    learning_methods_other: str | None = Field(default=None, max_length=200)
    weekly_hours: WeeklyHours

    @model_validator(mode="after")
    def other_needs_text(self):
        if "other" in self.learning_methods and not (self.learning_methods_other or "").strip():
            raise ValueError("Describe your other learning method.")
        return self


class Experience(BaseModel):
    num_projects: int = Field(ge=0, le=1000)
    num_certifications: int = Field(ge=0, le=1000)
    num_internships: int = Field(ge=0, le=1000)


class AssessmentSubmission(BaseModel):
    candidate_id: str | None = None
    career_id: str
    confidence: list[SkillRating] = Field(min_length=1, max_length=15)
    preferences: Preferences
    experience: Experience

    @field_validator("confidence")
    @classmethod
    def unique_skills(cls, value):
        if len({item.skill_id for item in value}) != len(value):
            raise ValueError("Each skill can only be rated once.")
        return value


class AssessmentSaved(BaseModel):
    assessment_id: str
    candidate_id: str | None
    career_id: str
    career_name: str
    submitted_at: str
    readiness_score: float | None = None
    previous_assessment_id: str | None = None
    status: Literal["submitted"] = "submitted"


class AssessmentRecord(BaseModel):
    assessment_id: str
    candidate_id: str | None
    career_id: str
    career_name: str
    submitted_at: str
    readiness_score: float | None = None
    previous_assessment_id: str | None = None
    form: dict


# Analysis response (GET /api/roadmap/analysis/{id}). extra="allow" keeps every existing field;
# only the new skill-gap fields are declared here.
class SkillGapItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill_id: str
    skill_name: str
    status: Literal["unverified", "gap", "review", "met", "ok"] | None = None
    message: str | None = None
    evidence_status: Literal["none", "pending", "provisional", "verified", "rejected"] | None = None
    evidence_source: str | None = None


class SkillGaps(BaseModel):
    model_config = ConfigDict(extra="allow")
    skills: list[SkillGapItem] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill_gaps: SkillGaps | None = None


# Optional proof for a claimed skill (POST /api/roadmap/evidence).
class EvidenceSubmission(BaseModel):
    """Sent as multipart/form-data (with "file" for certificate_file) or JSON. "type" is the original
    field name; "proof_type" is accepted too. Detailed checks (https, GitHub URL, file type/size) are
    in evidence_check.validate_submission and return 400 with a clear message."""
    candidate_id: str | None = None
    skill_id: str = Field(min_length=1, max_length=20)
    type: str | None = None
    proof_type: str | None = None
    url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)


class EvidenceRecord(BaseModel):
    evidence_id: str
    candidate_id: str
    skill_id: str
    type: str
    url: str
    status: Literal["none", "pending", "provisional", "verified", "rejected"]
    submitted_at: str
    proof_type: str | None = None
    skill_name: str | None = None
    file_name: str | None = None
    description: str | None = None
    provisional_level: float | None = None
    verified_level: float | None = None
    check_details: str | None = None
    created_at: str | None = None
    analysis: dict | None = None          # regenerated roadmap after this change (POST only)


class EvidenceDeleted(BaseModel):
    deleted: bool
    evidence_id: str
    analysis: dict | None = None
