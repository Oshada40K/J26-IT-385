import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from . import psychometric
from .schemas import (QuestionnaireResponse, QuestionnaireScoreRequest, QuestionnaireScoreResponse,
                      TextTraitRequest, TextTraitResponse)

TRAIT_NAMES = {"OPN": "Openness", "CON": "Conscientiousness", "EXT": "Extraversion",
               "AGR": "Agreeableness", "NEU": "Neuroticism"}

router = APIRouter(prefix="/api/personality", tags=["Personality Profile"])


@router.get("/test")
def test_component():
    return {"component": "Personality Profile", "status": "working"}


@router.get("/profile", summary="Get the sample skill profile")
def get_profile():
    return json.loads(Path(__file__).with_name("soft_skills.json").read_text(encoding="utf-8"))


@router.post("/text-traits", response_model=TextTraitResponse,
             summary="Big Five estimate from free-text answers (behavioural text model)")
def text_traits(body: TextTraitRequest):
    # Imported here so the app still starts if the model's packages are missing.
    from .text_trait import get_predictor

    try:
        traits = get_predictor().predict(body.answers)
    except ValueError as exc:  # fewer than 20 words
        raise HTTPException(422, str(exc)) from exc
    words = sum(len(a.split()) for a in body.answers)
    return TextTraitResponse(word_count=words, traits=traits, trait_names=TRAIT_NAMES)


@router.get("/questionnaire", response_model=QuestionnaireResponse,
            summary="Big Five questionnaire items (IPIP-50) in display order")
def questionnaire():
    instrument = psychometric.load_instrument()
    return QuestionnaireResponse(name=instrument["name"], version=instrument["version"],
                                 scale_labels=instrument["scale"]["labels"],
                                 items=psychometric.presented_items(instrument))


@router.post("/questionnaire/score", response_model=QuestionnaireScoreResponse,
             summary="Score questionnaire answers into normalised Big Five traits (T_psy)")
def score_questionnaire(body: QuestionnaireScoreRequest):
    try:
        result = psychometric.score_responses(body.responses, psychometric.load_instrument())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return QuestionnaireScoreResponse(**result, trait_names=TRAIT_NAMES)
