from typing import Literal
from pydantic import BaseModel, Field


class TechnicalSkill(BaseModel):
    name: str
    level: int = Field(ge=1, le=5)


class SkillProfileResponse(BaseModel):
    schema_version: Literal['1.0'] = '1.0'
    candidate_id: str
    technical_skills: list[TechnicalSkill]


class UploadResponse(BaseModel):
    candidate_id: str
    assessment_id: str
    status: Literal['completed']


class CandidateSession(BaseModel):
    candidate_id: str
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
