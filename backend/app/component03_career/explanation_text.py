"""Turn the exporter's SHAP output into plain-language content for candidates.

The model, its scores and its SHAP values are unchanged; this only rewords them.
"""

SOFT_PREFIX = "soft_alignment__"
TECH_PHRASES = {
    "technology_relevance": "how many of your technical skills this job actually uses",
    "technology_category_coverage": "how many of this job's tool categories you already cover",
    "in_demand_category_coverage": "how well you cover the in-demand tools for this job",
}
TECH_GAPS = {
    "technology_relevance": "only part of your technical skill set is used in this job",
    "technology_category_coverage": "you cover only some of this job's tool categories",
    "in_demand_category_coverage": "you are missing some of this job's in-demand tools",
}
TECH_LABELS = {
    "technology_relevance": "Technical skills used in this job",
    "technology_category_coverage": "Tool category coverage",
    "in_demand_category_coverage": "In-demand tool coverage",
}


def _is_soft(factor):
    return factor["feature"].startswith(SOFT_PREFIX)


def _phrase(factor):
    if _is_soft(factor):
        return factor["meaning"].split(":")[0]
    return TECH_PHRASES.get(factor["feature"], factor["meaning"])


def _gap(factor):
    if _is_soft(factor):
        return f"less evidence of {_phrase(factor)} than this job expects"
    return TECH_GAPS.get(factor["feature"], factor["meaning"])


def _label(factor):
    if _is_soft(factor):
        return _phrase(factor)
    return TECH_LABELS.get(factor["feature"], factor["meaning"])


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _impact(points, total):
    share = points / total if total > 0 else 0
    return "the main reason" if share >= 0.5 else "a strong reason" if share >= 0.15 else "a small boost"


def _key_reasons(job):
    positives = job["positive_shap_factors"]
    total = sum(f["shap_score_points"] for f in positives)
    tech = [f for f in positives if not _is_soft(f)]
    soft = [f for f in positives if _is_soft(f)]
    reasons = [f"{_impact(f['shap_score_points'], total).capitalize()} for this match: {_phrase(f)}."
               for f in tech[:2]]
    if soft:
        reasons.append(f"Your soft skills also fit what this job needs, especially {_join(_phrase(f) for f in soft[:3])}.")
    negatives = job["negative_shap_factors"][:2]
    if negatives:
        reasons.append(f"What lowered your score: {_join(_gap(f) for f in negatives)}.")
    return reasons


def friendly_explanation(job, eligible_occupations):
    title = job["job_title"]
    points = [f"{title} is your best match out of {eligible_occupations} occupations, "
              f"with a match score of {job['match_score_0_to_100']:.0f}/100."]

    matched = sorted(job["matched_technologies"], key=lambda t: -t["candidate_level_0_to_5"])
    if matched:
        names = _join(t["technology"] for t in matched[:4])
        extra = f" and {len(matched) - 4} more" if len(matched) > 4 else ""
        points.append(f"Your technical skills in {names}{extra} are used in this job.")

    points.extend(_key_reasons(job))

    missing = job["unobserved_in_demand_technology_examples"][:5]
    if missing:
        points.append(f"To become a stronger candidate, consider learning {_join(missing)}, "
                      f"which are in demand for {title} roles.")
    return points


def explanation_details(job, eligible_occupations):
    """Structured, plain-language pieces of the same explanation for the UI."""
    matched = sorted(job["matched_technologies"], key=lambda t: -t["candidate_level_0_to_5"])
    factors = [{"label": _label(f), "points": round(f["shap_score_points"], 2), "effect": effect}
               for effect, group, limit in [("positive", job["positive_shap_factors"], 5),
                                            ("negative", job["negative_shap_factors"], 3)]
               for f in group[:limit]]
    return {
        "friendly_explanation": friendly_explanation(job, eligible_occupations),
        "key_reasons": _key_reasons(job),
        "match_score": job["match_score_0_to_100"],
        "matched_technologies": [t["technology"] for t in matched],
        "skills_to_learn": job["unobserved_in_demand_technology_examples"][:8],
        "factors": factors,
    }
