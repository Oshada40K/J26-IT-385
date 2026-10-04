from fastapi import APIRouter

router = APIRouter(prefix="/api/career", tags=["Explainable Career Recommendation"])

# TODO: Integrate XGBoost predictions and SHAP explanations later.

@router.get("/test")
def test_component():
    return {"component": "Explainable Career Recommendation", "status": "working"}
