from fastapi import APIRouter

router = APIRouter(prefix="/api/personality", tags=["Personality Profile"])


@router.get("/test")
def test_component():
    return {"component": "Personality Profile", "status": "working"}
