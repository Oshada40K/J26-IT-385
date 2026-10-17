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


class SjtOption(BaseModel):
    id: str
    text: str


class SjtScenario(BaseModel):
    id: str
    topic: str
    text: str
    options: list[SjtOption]


class SjtResponse(BaseModel):
    name: str
    version: str
    status: str
    instruction: str
    scenarios: list[SjtScenario]


class SjtScoreRequest(BaseModel):
    responses: dict[str, str] = Field(..., description="Scenario id -> chosen option id, e.g. {\"S1\": \"A\"}")


class SjtScoreResponse(BaseModel):
    source: str = "situational_judgement"
    score_meaning: str = "Trait tendency from 0 (lowest possible) to 1 (highest possible) across the scenarios"
    key_version: str
    key_status: str
    traits: dict[str, float | None] = Field(description="None if no scenario measures the trait")
    coverage: dict[str, int] = Field(description="Number of scenarios whose options differ on each trait")
    trait_names: dict[str, str]


class AssessRequest(BaseModel):
    questionnaire: dict[str, int] | None = Field(None, description="IPIP-50 answers, item id -> 1..5")
    sjt: dict[str, str] | None = Field(None, description="Scenario id -> chosen option id")
    answers: list[str] | None = Field(None, description="Open-ended written answers (at least 20 words in total)")


class AssessResponse(BaseModel):
    schema_version: str = "c2-profile-0.1"
    generated_at: str
    score_meaning: str = "Fused Big Five profile, 0-1 per trait (confidence-weighted questionnaire + behaviour)"
    traits: dict[str, float]
    trait_names: dict[str, str]
    consistency: dict | None = Field(description="Personality Consistency Score; None until questionnaire and behaviour are both present")
    behavioural: dict[str, float | None]
    confidence: dict
    sources: dict = Field(description="Each source's own scoring result")
    notes: list[str]
    fusion_version: str


class QuestionnaireScoreResponse(BaseModel):
    source: str = "questionnaire"
    score_meaning: str = "Trait level from 0 (lowest possible) to 1 (highest possible), IPIP-50 keyed means"
    traits: dict[str, float]
    raw_means: dict[str, float] = Field(description="Keyed item mean per trait on the 1-5 scale")
    attention_passed: bool
    valid: bool
    warnings: list[str]
    trait_names: dict[str, str]
