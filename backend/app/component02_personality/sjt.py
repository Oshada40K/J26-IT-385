"""Situational judgement test (SJT) encoding: chosen options -> Big Five trait-tendency vector.

Scenarios, options and the option-to-trait scoring key live in config/sjt_key.json (FR-17).
Each option carries weights of +1 / -1 per trait (missing = 0). A trait's score is the sum
of the chosen options' weights, rescaled to 0-1 between the lowest and highest sum the
scenarios allow for that trait. The key is a draft until expert raters agree on it, which
``key_agreement`` measures with pairwise Cohen's kappa.
"""
import json
from functools import lru_cache
from itertools import combinations
from pathlib import Path

TRAITS = ["OPN", "CON", "EXT", "AGR", "NEU"]
CONFIG_PATH = Path(__file__).parent / "config" / "sjt_key.json"


@lru_cache(maxsize=1)
def load_key(path: Path = CONFIG_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def presented_scenarios(key: dict) -> list[dict]:
    """Scenarios as shown to the student: no weights."""
    return [{"id": s["id"], "topic": s["topic"], "text": s["text"],
             "options": [{"id": o["id"], "text": o["text"]} for o in s["options"]]}
            for s in key["scenarios"]]


def trait_ranges(key: dict) -> dict[str, tuple[int, int, int]]:
    """Per trait: (lowest possible sum, highest possible sum, number of scenarios that measure it)."""
    out = {}
    for t in TRAITS:
        lo = hi = n = 0
        for s in key["scenarios"]:
            w = [o["weights"].get(t, 0) for o in s["options"]]
            lo, hi = lo + min(w), hi + max(w)
            n += min(w) != max(w)
        out[t] = (lo, hi, n)
    return out


def score_responses(responses: dict[str, str], key: dict) -> dict:
    """Score one student. ``responses`` maps every scenario id to the chosen option id."""
    scenarios = {s["id"]: s for s in key["scenarios"]}
    missing = [sid for sid in scenarios if sid not in responses]
    if missing:
        raise ValueError(f"Missing answers for: {', '.join(missing)}")
    unknown = sorted(set(responses) - set(scenarios))
    if unknown:
        raise ValueError(f"Unknown scenario ids: {', '.join(unknown)}")

    sums = dict.fromkeys(TRAITS, 0)
    for sid, choice in responses.items():
        option = next((o for o in scenarios[sid]["options"] if o["id"] == choice), None)
        if option is None:
            raise ValueError(f"Scenario {sid} has no option '{choice}'")
        for t, w in option["weights"].items():
            sums[t] += w

    traits, coverage = {}, {}
    for t, (lo, hi, n) in trait_ranges(key).items():
        traits[t] = round((sums[t] - lo) / (hi - lo), 4) if hi > lo else None
        coverage[t] = n
    return {"traits": traits, "coverage": coverage}


# ----------------------------------------------------------------- expert scoring-key agreement
def key_ratings(key: dict) -> list[int]:
    """Flatten a scoring key into one -1/0/+1 rating per (scenario, option, trait)."""
    return [o["weights"].get(t, 0) for s in key["scenarios"] for o in s["options"] for t in TRAITS]


def cohen_kappa(a: list, b: list) -> float:
    """Cohen's kappa for two raters' categorical ratings of the same items."""
    if len(a) != len(b) or not a:
        raise ValueError("Both raters must rate the same, non-empty set of items.")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    expected = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def key_agreement(keys: dict[str, dict]) -> dict:
    """Pairwise and mean Cohen's kappa between raters' versions of the scoring key {rater: key}."""
    ratings = {name: key_ratings(k) for name, k in keys.items()}
    if len(ratings) < 2:
        raise ValueError("Need at least two raters.")
    pairwise = {f"{a} vs {b}": round(cohen_kappa(ratings[a], ratings[b]), 3) for a, b in combinations(ratings, 2)}
    return {"pairwise": pairwise, "mean_kappa": round(sum(pairwise.values()) / len(pairwise), 3)}
