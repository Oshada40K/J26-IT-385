# TODO (Owner: Oshada - Component 03):
# Implement Component 03 logic only in this component folder.

from fastapi import APIRouter

router = APIRouter(prefix="/api/c03", tags=["Component 03 - Explainable Career Recommendation"])


@router.get("")
def component_status():
    return {"component": "Explainable Career Recommendation", "status": "not implemented"}
