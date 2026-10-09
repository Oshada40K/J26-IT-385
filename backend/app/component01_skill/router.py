import json
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool
from . import repository
from .config import MAX_FILE_BYTES
from .schemas import CandidateSession, SkillProfileResponse, UploadResponse
from .services.cv_parser import CVError
from .services.profile_service import process_cv

# Keep the existing /api/skill sample endpoints for other components.
router = APIRouter(tags=['Technical Skill Profile'])
security = HTTPBearer(auto_error=False)


def current_candidate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
    candidate = repository.candidate_for_token(credentials.credentials) if credentials else None
    if not candidate:
        raise HTTPException(401, 'A valid candidate access token is required.')
    return candidate


def authorize(candidate_id, owner):
    if candidate_id != owner:
        raise HTTPException(403, 'You cannot access another candidate profile.')


@router.get('/api/skill/test')
def test_component():
    return {'component': 'Technical Skill Profile', 'status': 'working'}


@router.get('/api/skill/profile', summary='Legacy sample fixture; not a live candidate assessment')
def get_profile():
    return json.loads(Path(__file__).with_name('technical_skills.json').read_text(encoding='utf-8'))


@router.post('/api/component01/skills/session', response_model=CandidateSession, status_code=201)
def create_session():
    """Create an isolated prototype candidate and credential; replace with app auth later."""
    return repository.create_candidate()


@router.post('/api/component01/skills/upload', response_model=UploadResponse)
async def upload_cv(
    candidate_id: Annotated[str, Form(min_length=1, max_length=100)],
    file: Annotated[UploadFile, File()],
    owner: Annotated[str, Depends(current_candidate)],
    github_username: Annotated[str | None, Form(max_length=200)] = None,
    linkedin_username: Annotated[str | None, Form(max_length=200)] = None,
    analyze_github: Annotated[bool, Form()] = False,
):
    try:
        authorize(candidate_id, owner)
        content = await file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(413, 'CV must be no larger than 10 MB.')
        try:
            return await run_in_threadpool(process_cv, candidate_id, file.filename or '', content, github_username, linkedin_username, analyze_github)
        except CVError as exc:
            raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()


def stored_assessment(candidate_id, owner):
    authorize(candidate_id, owner)
    details = repository.latest_assessment(candidate_id)
    if not details:
        raise HTTPException(404, 'No completed skill assessment found for this candidate.')
    return details


@router.get('/api/component01/skills/{candidate_id}', response_model=SkillProfileResponse)
def shared_profile(candidate_id: str, owner: Annotated[str, Depends(current_candidate)]):
    details = stored_assessment(candidate_id, owner)
    return {'schema_version': '1.0', 'candidate_id': candidate_id, 'technical_skills': [{'name': item['name'], 'level': item['level']} for item in details['skills']]}


@router.get('/api/component01/skills/{candidate_id}/details')
def profile_details(candidate_id: str, owner: Annotated[str, Depends(current_candidate)]):
    return stored_assessment(candidate_id, owner)
