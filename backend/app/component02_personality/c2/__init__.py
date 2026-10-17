"""Component 2 - Personality Profiling and Consistency Verification (J26-IT-385).

This package currently holds the behavioural *text* trait estimators (T_beh from
free-text responses). The psychometric scorer, SJT encoder, fusion and
consistency modules will be added as separate modules.
"""

TRAITS = ["OPN", "CON", "EXT", "AGR", "NEU"]
TRAIT_NAMES = {
    "OPN": "Openness",
    "CON": "Conscientiousness",
    "EXT": "Extraversion",
    "AGR": "Agreeableness",
    "NEU": "Neuroticism",
}
