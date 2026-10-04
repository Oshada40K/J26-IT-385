# TODO (Owner: Dewmi - Component 04):
# Implement Component 04 logic only in this component folder.

from fastapi import APIRouter

router = APIRouter(prefix="/api/c04", tags=["Component 04 - Learning Roadmap & Skill Gap"])


@router.get("")
def component_status():
    return {"component": "Learning Roadmap & Skill Gap", "status": "not implemented"}
