import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/personality", tags=["Personality Profile"])


@router.get("/test")
def test_component():
    return {"component": "Personality Profile", "status": "working"}


@router.get("/profile", summary="Get the sample skill profile")
def get_profile():
    return json.loads(Path(__file__).with_name("soft_skills.json").read_text(encoding="utf-8"))
