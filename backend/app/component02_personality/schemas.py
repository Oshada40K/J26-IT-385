# TODO (Owner: Nethmi - Component 02):
# Implement Component 02 logic only in this component folder.

from pydantic import BaseModel, Field


class TextTraitRequest(BaseModel):
    answers: list[str] = Field(
        ..., min_length=1,
        description="The student's open-ended answers. They are joined into one text (at least 20 words).",
        examples=[[
            "When my team disagrees, I usually listen to everyone first and then suggest a plan we can all accept.",
            "I like to finish my assignments early because last-minute deadlines make me anxious and stressed.",
        ]],
    )


class TextTraitResponse(BaseModel):
    source: str = "text"
    score_meaning: str = "Probability that the trait is high (0-1), from free-text answers only"
    word_count: int
    traits: dict[str, float] = Field(description="OPN, CON, EXT, AGR, NEU -> P(high trait)")
    trait_names: dict[str, str]


class QuestionnaireItem(BaseModel):
    id: str
    text: str


class QuestionnaireResponse(BaseModel):
    name: str
    version: str
    scale_labels: list[str] = Field(description="Labels for answers 1..5")
    items: list[QuestionnaireItem] = Field(description="In display order, attention checks included")


class QuestionnaireScoreRequest(BaseModel):
    responses: dict[str, int] = Field(..., description="Item id -> answer from 1 (strongly disagree) to 5 (strongly agree)")


class QuestionnaireScoreResponse(BaseModel):
    source: str = "questionnaire"
    score_meaning: str = "Trait level from 0 (lowest possible) to 1 (highest possible), IPIP-50 keyed means"
    traits: dict[str, float]
    raw_means: dict[str, float] = Field(description="Keyed item mean per trait on the 1-5 scale")
    attention_passed: bool
    valid: bool
    warnings: list[str]
    trait_names: dict[str, str]
