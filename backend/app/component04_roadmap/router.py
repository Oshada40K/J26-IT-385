from fastapi import APIRouter

router = APIRouter(prefix="/api/roadmap", tags=["Learning Roadmap & Skill Gap"])


@router.get("/test")
def test_component():
    return {"component": "Learning Roadmap & Skill Gap", "status": "working"}
