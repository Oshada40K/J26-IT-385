"""Psychometric trait scoring (T_psy) for the IPIP-50 Big Five questionnaire.

Items, keying and attention checks live in config/ipip50.json, so the instrument can be
changed without code changes. Scores are the mean of the keyed 1-5 answers per trait,
rescaled to 0-1 (0 = lowest possible, 1 = highest possible).
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

TRAITS = ["OPN", "CON", "EXT", "AGR", "NEU"]
CONFIG_PATH = Path(__file__).parent / "config" / "ipip50.json"


@lru_cache(maxsize=1)
def load_instrument(path: Path = CONFIG_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def presented_items(instrument: dict) -> list[dict]:
    """Items in the order the student sees them, attention checks inserted. No keying info."""
    checks = {c["after"]: c for c in instrument["attention_checks"]}
    out = []
    for item in instrument["items"]:
        out.append({"id": item["id"], "text": item["text"]})
        if item["id"] in checks:
            out.append({"id": checks[item["id"]]["id"], "text": checks[item["id"]]["text"]})
    return out


def score_responses(responses: dict[str, int], instrument: dict) -> dict:
    """Score one student. ``responses`` maps every item and attention-check id to 1-5."""
    lo, hi = instrument["scale"]["min"], instrument["scale"]["max"]
    expected_ids = [i["id"] for i in instrument["items"]] + [c["id"] for c in instrument["attention_checks"]]
    missing = [i for i in expected_ids if i not in responses]
    if missing:
        raise ValueError(f"Missing answers for: {', '.join(missing)}")
    unknown = sorted(set(responses) - set(expected_ids))
    if unknown:
        raise ValueError(f"Unknown item ids: {', '.join(unknown)}")
    bad = [i for i, v in responses.items() if not isinstance(v, int) or not lo <= v <= hi]
    if bad:
        raise ValueError(f"Answers must be whole numbers from {lo} to {hi}: {', '.join(bad)}")

    keyed: dict[str, list[int]] = {t: [] for t in TRAITS}
    for item in instrument["items"]:
        v = responses[item["id"]]
        keyed[item["trait"]].append(v if item["key"] == 1 else lo + hi - v)  # reverse-keyed items
    raw_means = {t: float(np.mean(vals)) for t, vals in keyed.items()}
    traits = {t: round((m - lo) / (hi - lo), 4) for t, m in raw_means.items()}

    failed = [c["id"] for c in instrument["attention_checks"] if responses[c["id"]] != c["expected"]]
    item_answers = [responses[i["id"]] for i in instrument["items"]]
    warnings = []
    if failed:
        warnings.append("An attention check was not answered as instructed, so these answers may be careless.")
    if len(set(item_answers)) == 1:
        warnings.append("The same option was chosen for every statement, so these answers may not be reliable.")
    return {
        "traits": traits,
        "raw_means": {t: round(m, 3) for t, m in raw_means.items()},
        "attention_passed": not failed,
        "valid": not warnings,
        "warnings": warnings,
    }


def cronbach_alpha(item_matrix) -> float:
    """Internal consistency of one scale over many respondents (rows) and its keyed items (columns).

    Used for the sample-level reliability check (target alpha >= 0.70 per trait), not per student.
    """
    X = np.asarray(item_matrix, dtype=float)
    k = X.shape[1]
    if X.shape[0] < 2 or k < 2:
        raise ValueError("Need at least 2 respondents and 2 items.")
    total_var = X.sum(axis=1).var(ddof=1)
    if total_var == 0:
        raise ValueError("Total score has zero variance.")
    return float(k / (k - 1) * (1 - X.var(axis=0, ddof=1).sum() / total_var))
