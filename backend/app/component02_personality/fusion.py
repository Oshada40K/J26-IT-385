"""Confidence-weighted late fusion and the Personality Consistency Score (PCS).

Inputs are the per-trait scores of each source, all on 0-1:
    T_psy  questionnaire trait level          (psychometric.score_responses)
    T_sjt  situational judgement tendency     (sjt.score_responses)
    T_txt  text model P(high trait)           (text_trait predictor)

1. Each source gets a confidence from response-quality indicators (attention checks,
   scenario coverage of the trait, amount of text).
2. T_beh = confidence-weighted mean of T_sjt and T_txt (the behavioural estimate).
3. Fused profile = confidence-weighted mean of T_psy and T_beh. Both inputs are kept in
   the output, so disagreement is exposed rather than averaged away.
4. Per trait divergence d = |T_psy - T_beh|; PCS = 1 - mean(d); traits with d >= threshold
   are flagged. All settings come from config/fusion.json.
"""
import json
from functools import lru_cache
from pathlib import Path

TRAITS = ["OPN", "CON", "EXT", "AGR", "NEU"]
CONFIG_PATH = Path(__file__).parent / "config" / "fusion.json"


@lru_cache(maxsize=1)
def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _weighted(pairs):
    """Confidence-weighted mean of (value, confidence) pairs; None if nothing to combine."""
    pairs = [(v, c) for v, c in pairs if v is not None and c > 0]
    total = sum(c for _, c in pairs)
    return (sum(v * c for v, c in pairs) / total, min(1.0, total)) if pairs else (None, 0.0)


def source_confidence(cfg: dict, questionnaire=None, sjt=None, text=None) -> dict:
    c = cfg["confidence"]
    out = {}
    if questionnaire:
        out["questionnaire"] = c["questionnaire_valid"] if questionnaire["valid"] else c["questionnaire_invalid"]
    if sjt:
        out["situational_judgement"] = {
            t: round(c["sjt_base"] * min(1.0, sjt["coverage"][t] / c["sjt_full_coverage_scenarios"]), 3) for t in TRAITS}
    if text:
        out["text"] = round(c["text_base"] * min(1.0, text["word_count"] / c["text_full_confidence_words"]), 3)
    return out


def band_for(score: float, cfg: dict) -> dict:
    return next({"label": b["label"], "meaning": b["meaning"]}
                for b in cfg["consistency"]["bands"] if score >= b["min"])


def combine(questionnaire=None, sjt=None, text=None, cfg: dict | None = None) -> dict:
    """Fuse the available sources. Each argument is that source's scoring result (or None)."""
    cfg = cfg or load_config()
    if not (questionnaire or sjt or text):
        raise ValueError("At least one source is needed.")
    conf = source_confidence(cfg, questionnaire, sjt, text)

    behavioural, fused, per_trait = {}, {}, {}
    for t in TRAITS:
        beh, c_beh = _weighted([
            (sjt["traits"][t] if sjt else None, conf.get("situational_judgement", {}).get(t, 0)),
            (text["traits"][t] if text else None, conf.get("text", 0)),
        ])
        psy = questionnaire["traits"][t] if questionnaire else None
        value, _ = _weighted([(psy, conf.get("questionnaire", 0)), (beh, c_beh)])
        behavioural[t] = None if beh is None else round(beh, 4)
        fused[t] = round(value, 4)
        if psy is not None and beh is not None:
            d = abs(psy - beh)
            per_trait[t] = {"questionnaire": psy, "behavioural": round(beh, 4), "divergence": round(d, 4),
                            "consistency": round(1 - d, 4),
                            "flagged": d >= cfg["consistency"]["flag_divergence"],
                            "direction": "self-report higher" if psy > beh else "behaviour higher"}

    consistency = None
    if len(per_trait) == len(TRAITS):
        score = round(1 - sum(p["divergence"] for p in per_trait.values()) / len(TRAITS), 4)
        consistency = {
            "score": score,
            "band": band_for(score, cfg),
            "threshold": cfg["consistency"]["flag_divergence"],
            "flagged_traits": [t for t, p in per_trait.items() if p["flagged"]],
            "per_trait": per_trait,
        }

    notes = []
    if not questionnaire:
        notes.append("No questionnaire: the consistency score needs it as the self-report reference.")
    if not (sjt or text):
        notes.append("No behavioural source yet: the profile is the questionnaire alone.")
    if questionnaire and not questionnaire["valid"]:
        notes.append("Questionnaire answers failed a quality check, so they were given half weight.")
    return {
        "fusion_version": cfg["version"],
        "traits": fused,
        "behavioural": behavioural,
        "confidence": conf,
        "consistency": consistency,
        "notes": notes,
    }
