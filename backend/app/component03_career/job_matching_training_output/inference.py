"""O*NET XGBoost/SHAP prototype inference. Load the saved catalogue and model first."""
import json, re
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
import shap

def norm(text):
    return re.sub(r"[^a-z0-9+#]+", " ", str(text).lower()).strip()

def tech_key(text):
    return TECH_ALIASES.get(norm(text), norm(text))

def read_input(value):
    if isinstance(value, dict): return value
    if isinstance(value, Path): return json.loads(value.read_text(encoding="utf-8-sig"))
    if isinstance(value, str):
        return json.loads(value) if value.lstrip().startswith("{") else json.loads(Path(value).read_text(encoding="utf-8-sig"))
    raise TypeError("Input must be a dictionary, JSON string, or JSON file path.")

def parse_candidate(soft_input, tech_input):
    soft, tech = read_input(soft_input), read_input(tech_input)
    for obj, field in [(soft, "soft_skills"), (tech, "technical_skills")]:
        if obj.get("schema_version") != "1.0": raise ValueError("schema_version must be '1.0'.")
        if not isinstance(obj.get("candidate_id"), str) or not obj["candidate_id"].strip():
            raise ValueError("A nonempty string candidate_id is required in both files.")
        if not isinstance(obj.get(field), list) or not obj[field]:
            raise ValueError(f"{field} must be a nonempty list.")
    if soft["candidate_id"] != tech["candidate_id"]:
        raise ValueError("The JSON files have different candidate_id values.")
    s = np.zeros(len(SOFT_NAMES), dtype=float)
    observed = np.zeros(len(SOFT_NAMES), dtype=bool)
    t, audit = {}, []
    for obj, field in [(soft, "soft_skills"), (tech, "technical_skills")]:
        seen = set()
        for item in obj[field]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                raise ValueError(f"Each {field} item needs a nonempty name.")
            level = item.get("level")
            if isinstance(level, bool) or not isinstance(level, (int, float)) or not np.isfinite(level) or not 0 <= level <= 5:
                raise ValueError(f"{item['name']}: level must be a number from 0 to 5, not extraction confidence.")
            key = SOFT_ALIASES.get(norm(item["name"])) if field == "soft_skills" else tech_key(item["name"])
            supported = key in SOFT_NAMES if field == "soft_skills" else key in IDF
            if supported and key in seen:
                raise ValueError(f"Duplicate/alias collision: {item['name']}. Keep one level per canonical skill.")
            if supported:
                seen.add(key)
                if field == "soft_skills":
                    i = SOFT_NAMES.index(key); s[i] = level / 5.0; observed[i] = True
                else: t[key] = level / 5.0
            audit.append({"type": field, "input": item["name"], "level": level,
                          "mapped_to": (key if field == "soft_skills" else TECH_LABELS.get(key)) if supported else None,
                          "status": "mapped" if supported else "UNRECOGNISED — excluded"})
    if not observed.any() or not t or not any(v > 0 for v in t.values()):
        raise ValueError("Need at least one recognised soft skill and one recognised technology with a positive level. Review the mapping dictionaries.")
    return {"id": soft["candidate_id"], "soft": s, "observed": observed, "tech": t}, pd.DataFrame(audit)

def pair_features(c, job):
    required = np.asarray(job["soft_level"])
    weights = np.asarray(job["soft_importance"])
    shares = weights / max(weights.sum(), 1e-8)
    alignment = np.minimum(c["soft"] / np.maximum(required, 1e-6), 1.0)
    # A zero required level contributes no evidence credit.
    alignment = np.where(required > 0, alignment, 0.0) * c["observed"] * shares
    evidence_mass = sum(IDF[k] * v for k, v in c["tech"].items())
    relevance = sum(IDF[k] * v for k, v in c["tech"].items() if k in job["tech"]) / max(evidence_mass, 1e-8)
    all_categories, demand_categories = {}, {}
    for k, item in job["tech"].items():
        for category in item["categories"]:
            value = c["tech"].get(k, 0.0)
            all_categories[category] = max(all_categories.get(category, 0.0), value)
            if item["in_demand"]:
                demand_categories[category] = max(demand_categories.get(category, 0.0), value)
    coverage = float(np.mean(list(all_categories.values()))) if all_categories else 0.0
    demand = float(np.mean(list(demand_categories.values()))) if demand_categories else coverage
    return np.asarray([*alignment, relevance, coverage, demand], dtype=np.float32)

def policy_score(X):
    X = np.asarray(X)
    return 100 * (POLICY_WEIGHTS["soft_alignment"] * X[..., :len(SOFT_NAMES)].sum(axis=-1)
        + POLICY_WEIGHTS["technology_relevance"] * X[..., -3]
        + POLICY_WEIGHTS["technology_category_coverage"] * X[..., -2]
        + POLICY_WEIGHTS["in_demand_category_coverage"] * X[..., -1])

def candidate_matrix(c):
    return pd.DataFrame(np.stack([pair_features(c, j) for j in jobs]), columns=FEATURE_NAMES)

def recommend_jobs(soft_input, tech_input, n_alternatives=4):
    if not isinstance(n_alternatives, int) or not 0 <= n_alternatives < len(jobs):
        raise ValueError("n_alternatives must be an integer from 0 to number_of_jobs - 1.")
    c, audit = parse_candidate(soft_input, tech_input)
    matrix = candidate_matrix(c)
    raw = model.predict(matrix)
    scores = np.clip(raw, 0, 100)
    # Raw score breaks clipped-score ties; SOC code is the deterministic final tie breaker.
    order = sorted(range(len(jobs)), key=lambda i: (-float(scores[i]), -float(raw[i]), jobs[i]["code"]))[:n_alternatives + 1]
    sv = explainer(matrix.iloc[order], check_additivity=True)
    np.testing.assert_allclose(sv.base_values + sv.values.sum(axis=1), raw[order], atol=1e-3)
    records = []
    for rank, ji in enumerate(order):
        job = jobs[ji]
        contributions = sv.values[rank]
        positives = [i for i in np.argsort(-contributions) if contributions[i] > 1e-6][:5]
        negatives = [i for i in np.argsort(contributions) if contributions[i] < -1e-6][:5]
        def factor(i):
            return {"feature": FEATURE_NAMES[i], "meaning": FEATURE_LABELS[i],
                    "feature_value": float(matrix.iloc[ji, i]), "shap_score_points": float(contributions[i])}
        matched = [{"technology": job["tech"][k]["label"], "candidate_level_0_to_5": round(v * 5, 2)}
                   for k, v in c["tech"].items() if k in job["tech"] and v > 0]
        missing = [item["label"] for k, item in job["tech"].items()
                   if item["in_demand"] and c["tech"].get(k, 0) == 0][:8]
        coverage = float(np.asarray(job["soft_importance"])[c["observed"]].sum() / max(sum(job["soft_importance"]), 1e-8))
        reasons = [f"{FEATURE_LABELS[i]} raised the model score by {contributions[i]:.2f} points relative to baseline." for i in positives[:3]]
        records.append({"rank": rank + 1, "recommendation": "Best match" if rank == 0 else f"Alternative {rank}",
            "onet_soc_code": job["code"], "job_title": job["title"],
            "match_score_0_to_100": round(float(scores[ji]), 2), "raw_model_score": float(raw[ji]),
            "direct_policy_score": round(float(policy_score(matrix.iloc[ji].values)), 2),
            "score_was_clipped": bool(raw[ji] != scores[ji]),
            "onet_url": "https://www.onetonline.org/link/summary/" + job["code"],
            "soft_evidence_importance_coverage": round(coverage, 4),
            "matched_technologies": matched,
            "unobserved_in_demand_technology_examples": missing,
            "explanation": " ".join(reasons),
            "shap_baseline": float(sv.base_values[rank]),
            "positive_shap_factors": [factor(int(i)) for i in positives],
            "negative_shap_factors": [factor(int(i)) for i in negatives],
            "all_shap_factors": [factor(i) for i in range(len(FEATURE_NAMES))]})
    unknown = audit[audit["status"].str.startswith("UNRECOGNISED")]["input"].tolist()
    return {"candidate_id": c["id"], "onet_version": ONET_VERSION,
            "model_type": "XGBRegressor trained on synthetic O*NET-derived pseudo-labels",
            "score_meaning": "Prototype skill-evidence match score; not a hiring probability or validated suitability score",
            "eligible_occupations": len(jobs), "unrecognised_skills": unknown,
            "mapping_audit": audit.to_dict(orient="records"),
            "best_job": records[0], "alternative_jobs": records[1:]}, sv

def load_saved_matcher(folder="job_matching_output"):
    """Run after importing the exported inference helper, or in this notebook."""
    global model, explainer, jobs, SOFT_NAMES, SOFT_ALIASES, TECH_ALIASES
    global IDF, TECH_LABELS, FEATURE_NAMES, FEATURE_LABELS, POLICY_WEIGHTS, ONET_VERSION
    folder = Path(folder)
    b = json.loads((folder / "preprocessing_catalogue.json").read_text(encoding="utf-8"))
    SOFT_NAMES, SOFT_ALIASES, TECH_ALIASES = b["soft_names"], b["soft_aliases"], b["tech_aliases"]
    IDF, TECH_LABELS, jobs = b["technology_idf"], b["technology_labels"], b["jobs"]
    FEATURE_NAMES, FEATURE_LABELS = b["feature_names"], b["feature_labels"]
    POLICY_WEIGHTS, ONET_VERSION = b["policy_weights"], b["onet_version"]
    model = xgb.XGBRegressor()
    model.load_model(folder / "xgboost_job_matcher.json")
    explainer = shap.TreeExplainer(model, model_output="raw", feature_perturbation="tree_path_dependent")
    return model
