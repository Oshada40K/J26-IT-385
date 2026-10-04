from fastapi import APIRouter

router = APIRouter(prefix="/api/skill", tags=["Technical Skill Profile"])


@router.get("/test")
def test_component():
    return {"component": "Technical Skill Profile", "status": "working"}
