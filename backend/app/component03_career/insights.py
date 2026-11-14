"""Trustworthy, actionable insights computed on top of the UNCHANGED exported matcher.

Three research additions to Component 3, all derived by re-running the saved
model (never by editing it):

1. Counterfactual "what-if" explanations.
   SHAP says WHY the score is what it is. A counterfactual says WHAT TO DO:
   "learn Docker at level 3 -> Software Developers rises from 42 to 47 and stays
   rank 1", or "raise SQL from 2 to 3 -> Web Developers becomes your best match".
   Each action is a single, concrete skill change evaluated by re-scoring all
   occupations with the real model, so the numbers are exact, not estimates.

2. Confidence-aware uncertainty.
   Component 1 attaches an evidence confidence (low / medium / high) to every CV
   skill. Confidence must never change a proficiency level, but it does tell us
   how SURE we are of that level. We sample plausible level perturbations whose
   spread depends on confidence, re-score every sample, and report a score range
   and rank-stability probability per recommended job instead of a bare point score.

3. Explanation stability.
   An explanation that flips when the input moves slightly is not trustworthy.
   We re-explain the best job for every sampled profile and measure how often the
   top SHAP factor and the top-3 factor set stay the same.

Identical inputs always give identical insights (fixed random seed).
The soft-skill profile is held fixed: Component 2 supplies a fixed sample profile
without per-skill confidence, so only CV evidence uncertainty is modelled.

Speed: the insights need about 80 extra scoring passes. The exporter builds its 21
features in a Python loop over all occupations (about 40 ms per pass), so this module
uses a vectorised equivalent of the exporter's THREE technology features and reuses the
18 soft-skill features, which never change here. The equivalence is asserted against
`inference.pair_features` in the test suite; the exported helper itself is untouched.
"""
import copy

import numpy as np
import pandas as pd
from scipy import sparse

from .job_matching_training_output import inference

LEARN_LEVEL = 3                      # "working proficiency" assumed for a newly learned tool
MAX_LEARN_ACTIONS = 8                # missing in-demand tools evaluated for the best job
MAX_IMPROVE_ACTIONS = 6              # matched tools evaluated for a +1 level upgrade
ALTERNATIVE_ACTIONS = 5              # learn actions evaluated per alternative job
PATH_STEPS = 3                       # greedy steps searched for the runner-up
MC_SAMPLES = 30
SEED = 20261114
CONFIDENCE_SD = {"high": 0.25, "medium": 0.5, "low": 1.0}   # level perturbation spread (0-5 scale)
MIN_PERTURBED_LEVEL = 0.25           # keep a perturbed skill present but weak, never deleted
STABILITY_LEVELS = [(0.8, "high"), (0.5, "moderate"), (0.0, "low")]
N_SOFT = 18


def _label(share):
    return next(name for threshold, name in STABILITY_LEVELS if share >= threshold)


# ---------------------------------------------------------------- fast scorer
class _FastScorer:
    """Vectorised twin of the technology part of `inference.pair_features`, built once per model load."""

    def __init__(self):
        keys = list(inference.IDF)
        self.col = {k: i for i, k in enumerate(keys)}
        dummy = len(keys)                      # column for job tools outside the IDF catalogue (always 0)
        self.width = len(keys) + 1
        self.idf = np.append(np.asarray([inference.IDF[k] for k in keys], dtype=float), 0.0)
        self.codes = np.asarray([job["code"] for job in inference.jobs])
        n_jobs = len(inference.jobs)
        rows, cols = [], []
        groups = {"all": ([], [], []), "demand": ([], [], [])}     # tech indices, segment starts, job per segment
        for j, job in enumerate(inference.jobs):
            categories = {"all": {}, "demand": {}}
            for k, item in job["tech"].items():
                column = self.col.get(k, dummy)
                rows.append(j)
                cols.append(column)
                for category in item["categories"]:
                    categories["all"].setdefault(category, []).append(column)
                    if item["in_demand"]:
                        categories["demand"].setdefault(category, []).append(column)
            for name, (idx, starts, owner) in groups.items():
                for members in categories[name].values():
                    starts.append(len(idx))
                    idx.extend(members)
                    owner.append(j)
        self.membership = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_jobs, self.width))
        self.groups = {name: tuple(np.asarray(part, dtype=int) for part in parts) for name, parts in groups.items()}
        self.n_jobs = n_jobs

    def vector(self, levels):
        """Candidate technology vector on the 0-1 scale from {catalogue key: level 0-5}."""
        v = np.zeros(self.width)
        for k, level in levels.items():
            v[self.col[k]] = level / 5.0
        return v

    def _category_mean(self, name, v):
        idx, starts, owner = self.groups[name]
        if len(idx) == 0:
            return np.zeros(self.n_jobs), np.zeros(self.n_jobs)
        segment_max = np.maximum.reduceat(v[idx], starts)
        sums = np.bincount(owner, weights=segment_max, minlength=self.n_jobs)
        counts = np.bincount(owner, minlength=self.n_jobs)
        return np.where(counts > 0, sums / np.maximum(counts, 1), 0.0), counts

    def tech_features(self, v):
        weighted = self.idf * v
        relevance = self.membership @ weighted / max(float(weighted.sum()), 1e-8)
        coverage, _ = self._category_mean("all", v)
        demand, demand_counts = self._category_mean("demand", v)
        demand = np.where(demand_counts > 0, demand, coverage)
        return np.column_stack([relevance, coverage, demand])

    def matrix(self, soft_block, v):
        features = np.hstack([soft_block, self.tech_features(v).astype(np.float32)])
        return pd.DataFrame(features, columns=inference.FEATURE_NAMES)

    def score(self, soft_block, v):
        matrix = self.matrix(soft_block, v)
        raw = np.asarray(inference.model.predict(matrix), dtype=float)
        return matrix, raw, np.clip(raw, 0, 100)

    def ranks(self, raw, scores):
        """Rank every occupation with the exporter's exact tie-breaking (score, raw, SOC code)."""
        order = np.lexsort((self.codes, -raw, -scores))
        ranks = np.empty(len(order), dtype=int)
        ranks[order] = np.arange(1, len(order) + 1)
        return ranks


_scorer = None
_scorer_model = None


def scorer():
    global _scorer, _scorer_model
    if _scorer is None or _scorer_model is not inference.model:
        _scorer = _FastScorer()
        _scorer_model = inference.model
    return _scorer


class _Session:
    """One candidate's fixed soft-skill block plus helpers shared by all insight passes."""

    def __init__(self, soft_input, tech_input):
        self.fast = scorer()
        candidate, _ = inference.parse_candidate(soft_input, tech_input)
        base = inference.candidate_matrix(candidate)
        self.soft_block = base.iloc[:, :N_SOFT].to_numpy(dtype=np.float32)
        self.levels = {k: v * 5.0 for k, v in candidate["tech"].items()}   # recognised CV skills only
        self.names = {inference.tech_key(item["name"]): item["name"] for item in tech_input["technical_skills"]}

    def score(self, levels):
        return self.fast.score(self.soft_block, self.fast.vector(levels))

    def ranks(self, raw, scores):
        return self.fast.ranks(raw, scores)


def _job_index(code):
    return next(i for i, job in enumerate(inference.jobs) if job["code"] == code)


def _learn_name(key):
    """A skill name the catalogue maps back to `key`, or None if no safe name exists."""
    for name in (inference.TECH_LABELS.get(key, key), key):
        if inference.tech_key(name) == key:
            return name
    return None


def apply_action(tech_input, action):
    """Copy of a technical profile INPUT with one counterfactual change applied (used for verification)."""
    changed = copy.deepcopy(tech_input)
    if action["action"] == "learn":
        changed["technical_skills"].append({"name": action["technology"], "level": action["to_level"]})
    else:
        for item in changed["technical_skills"]:
            if inference.tech_key(item["name"]) == action["key"]:
                item["level"] = action["to_level"]
    return changed


def _apply(levels, action):
    return {**levels, action["key"]: float(action["to_level"])}


def _candidate_actions(levels, job, learn_limit, improve_limit):
    actions = []
    for key, item in job["tech"].items():
        if len(actions) >= learn_limit:
            break
        if item["in_demand"] and levels.get(key, 0) == 0 and key in inference.IDF:
            name = _learn_name(key)
            if name:
                actions.append({"action": "learn", "key": key, "technology": name,
                                "from_level": 0, "to_level": LEARN_LEVEL})
    matched = sorted(((key, level) for key, level in levels.items() if key in job["tech"] and level < 5),
                     key=lambda kv: (kv[1], kv[0]))
    for key, level in matched[:improve_limit]:
        actions.append({"action": "improve", "key": key, "technology": inference.TECH_LABELS.get(key, key),
                        "from_level": round(level, 2), "to_level": round(min(level + 1, 5), 2)})
    return actions


def _evaluate(session, levels, action, job_index, baseline_score, baseline_rank):
    _, raw, scores = session.score(_apply(levels, action))
    ranks = session.ranks(raw, scores)
    new_score = round(float(scores[job_index]), 2)
    return {
        "action": action["action"],
        "technology": action["technology"],
        "from_level": action["from_level"],
        "to_level": action["to_level"],
        "new_score": new_score,
        "score_gain": round(new_score - baseline_score, 2),
        "new_rank": int(ranks[job_index]),
        "rank_change": int(baseline_rank - ranks[job_index]),
        "becomes_best": bool(ranks[job_index] == 1),
    }


# ------------------------------------------------------------- 1. counterfactuals
def counterfactuals(session, result):
    levels = session.levels
    _, raw, scores = session.score(levels)
    ranks = session.ranks(raw, scores)
    best = result["best_job"]
    best_index = _job_index(best["onet_soc_code"])

    actions = _candidate_actions(levels, inference.jobs[best_index], MAX_LEARN_ACTIONS, MAX_IMPROVE_ACTIONS)
    evaluated = [_evaluate(session, levels, a, best_index, best["match_score_0_to_100"], 1) for a in actions]
    evaluated.sort(key=lambda a: (-a["score_gain"], a["technology"]))

    alternatives = []
    for alternative in result["alternative_jobs"]:
        index = _job_index(alternative["onet_soc_code"])
        base_score, base_rank = alternative["match_score_0_to_100"], int(ranks[index])
        options = _candidate_actions(levels, inference.jobs[index], ALTERNATIVE_ACTIONS, 0)
        scored = sorted((_evaluate(session, levels, a, index, base_score, base_rank) for a in options),
                        key=lambda a: (-a["score_gain"], a["technology"]))
        alternatives.append({
            "ranking": alternative["rank"], "job": alternative["job_title"], "score": base_score,
            "gap_to_best": round(best["match_score_0_to_100"] - base_score, 2),
            "best_action": scored[0] if scored else None,
            "reaches_rank_1": bool(scored and scored[0]["becomes_best"]),
        })

    return {
        "target": best["job_title"],
        "baseline_score": best["match_score_0_to_100"],
        "learn_level": LEARN_LEVEL,
        "actions": evaluated,
        "alternatives": alternatives,
        "path_to_runner_up": _greedy_path(session, result) if result["alternative_jobs"] else None,
        "meaning": ("Each action re-scores every occupation with the saved model after one skill change. "
                    "Gains are model deltas for a prototype match score, not guaranteed outcomes."),
    }


def _greedy_path(session, result):
    """Greedy sequence of learn actions that makes the runner-up the best match, if any within PATH_STEPS."""
    runner = result["alternative_jobs"][0]
    index = _job_index(runner["onet_soc_code"])
    job = inference.jobs[index]
    current = dict(session.levels)
    steps = []
    for _ in range(PATH_STEPS):
        _, raw, scores = session.score(current)
        ranks = session.ranks(raw, scores)
        if ranks[index] == 1:
            break
        options = _candidate_actions(current, job, ALTERNATIVE_ACTIONS, 0)
        if not options:
            break
        scored = [_evaluate(session, current, a, index, float(scores[index]), int(ranks[index])) for a in options]
        step = max(scored, key=lambda a: (a["becomes_best"], a["score_gain"], a["technology"]))
        action = next(a for a in options if a["technology"] == step["technology"])
        current = _apply(current, action)
        steps.append(step)
        if step["becomes_best"]:
            break
    return {"job": runner["job_title"], "steps": steps, "reaches_rank_1": bool(steps and steps[-1]["becomes_best"])}


# ------------------------------------------------------------- 2 + 3. uncertainty and stability
def _perturbed_levels(levels, sd_by_key, rng, samples):
    keys = list(levels)
    base = np.asarray([levels[k] for k in keys])
    sd = np.asarray([sd_by_key[k] for k in keys])
    for _ in range(samples):
        drawn = np.clip(base + rng.normal(0.0, 1.0, size=len(keys)) * sd, MIN_PERTURBED_LEVEL, 5.0)
        yield dict(zip(keys, drawn.tolist()))


def uncertainty_and_stability(session, confidence_by_name, result):
    rng = np.random.default_rng(SEED)
    top = [result["best_job"], *result["alternative_jobs"]]
    indices = [_job_index(job["onet_soc_code"]) for job in top]
    best_index = indices[0]
    best = result["best_job"]

    confidence_by_key = {k: confidence_by_name.get(session.names.get(k), "medium") for k in session.levels}
    sd_by_key = {k: CONFIDENCE_SD[c] for k, c in confidence_by_key.items()}
    counts = {level: sum(1 for c in confidence_by_key.values() if c == level) for level in CONFIDENCE_SD}

    baseline_points = np.asarray([f["shap_score_points"] for f in best["all_shap_factors"]])
    baseline_top3 = {f["feature"] for f in best["positive_shap_factors"][:3]}
    baseline_top1 = best["positive_shap_factors"][0]["feature"] if best["positive_shap_factors"] else None

    sampled_scores, sampled_ranks = [], []
    top1_agree, jaccards, point_changes = 0, [], []
    for levels in _perturbed_levels(session.levels, sd_by_key, rng, MC_SAMPLES):
        matrix, raw, scores = session.score(levels)
        ranks = session.ranks(raw, scores)
        sampled_scores.append(scores[indices])
        sampled_ranks.append(ranks[indices])
        contributions = np.asarray(inference.explainer(matrix.iloc[[best_index]]).values[0], dtype=float)
        positive = [inference.FEATURE_NAMES[i] for i in np.argsort(-contributions) if contributions[i] > 1e-6]
        top3 = set(positive[:3])
        jaccards.append(len(top3 & baseline_top3) / max(len(top3 | baseline_top3), 1))
        top1_agree += int(bool(positive) and positive[0] == baseline_top1)
        point_changes.append(float(np.mean(np.abs(contributions - baseline_points))))

    S = np.asarray(sampled_scores)           # samples x 5
    R = np.asarray(sampled_ranks)
    top1_probability = float(np.mean(R[:, 0] == 1))
    jobs = [{
        "ranking": job["rank"], "job": job["job_title"], "score": job["match_score_0_to_100"],
        "mean": round(float(S[:, column].mean()), 2), "sd": round(float(S[:, column].std()), 2),
        "low": round(float(np.percentile(S[:, column], 5)), 2),
        "high": round(float(np.percentile(S[:, column], 95)), 2),
        "top1_probability": round(float(np.mean(R[:, column] == 1)), 3),
        "top5_probability": round(float(np.mean(R[:, column] <= 5)), 3),
    } for column, job in enumerate(top)]
    uncertainty = {
        "samples": MC_SAMPLES,
        "method": ("Monte Carlo over recognised CV skill levels: each level is perturbed with a spread set by "
                   "Component 1 evidence confidence (high 0.25, medium 0.5, low 1.0 levels, clipped to 0.25-5). "
                   "Soft skills are held fixed. Levels themselves are never changed by confidence."),
        "confidence_counts": counts,
        "confidence_source": "component01" if confidence_by_name else "assumed medium (legacy profile without confidence)",
        "jobs": jobs,
        "stability": _label(top1_probability),
        "stability_meaning": f"{best['job_title']} stayed the best match in {top1_probability:.0%} of {MC_SAMPLES} plausible profiles.",
    }
    top1_rate = top1_agree / MC_SAMPLES
    mean_jaccard = float(np.mean(jaccards))
    stability = {
        "samples": MC_SAMPLES,
        "top_factor_agreement": round(top1_rate, 3),
        "mean_top3_overlap": round(mean_jaccard, 3),
        "mean_abs_point_change": round(float(np.mean(point_changes)), 3),
        "label": _label(min(top1_rate, mean_jaccard)),
        "meaning": ("How often the SHAP explanation of the best job keeps its leading factor and its top-3 factor set "
                    "when the CV skill levels move within their evidence confidence."),
    }
    return uncertainty, stability


def compute_insights(soft_input, tech_input, confidence_by_name, result):
    """All three insight blocks for one already-computed recommendation (same validated inputs)."""
    session = _Session(soft_input, tech_input)
    unc, stab = uncertainty_and_stability(session, confidence_by_name, result)
    return {
        "counterfactuals": counterfactuals(session, result),
        "uncertainty": unc,
        "explanation_stability": stab,
    }
