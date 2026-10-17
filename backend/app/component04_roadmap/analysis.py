# Owner: Dewmi - Component 04.
"""Explainable C4 analysis built on c4_engine.py and the trained models in trained_models/.

c4_engine.py is left unchanged because the training notebook shares its feature code. This module
reuses its feature builders (gap_frame, priority_frame, readiness_features, make_roadmap) and the
trained models, and adds the student-facing explanation layer:

1. Confidence-aware gap analysis   - trained model A (RandomForest gap + HistGradientBoosting severity)
                                     combined with the transparent CV-evidence rule (see _gap_status).
2. Multi-factor prioritisation     - transparent weighted sum using the weights learned in the notebook
                                     (c4_config.json "B"); the demand factor uses real O*NET flags.
3. Adaptive resources              - learning_resources.csv ranked by the student's learning methods and
                                     current proficiency.
4. Staged roadmap                  - prerequisite-ordered steps from make_roadmap, grouped into
                                     Beginner / Intermediate / Advanced with activities and milestones.
5. Career readiness score          - trained linear model C, shown term by term (intercept + coef x value).
"""
import math
import threading
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .c4_engine import A_FEATURES, C_FEATURES, FIVE, LEVEL_MAX, SEVERITY, STAGES, C4Engine, _clean, band_of
from .errors import ModelsUnavailable

INPUTS_DIR = Path(__file__).with_name("inputs")
MODELS_DIR = Path(__file__).with_name("trained_models")
REQUIRED_MODEL_FILES = ("c4_config.json", "A_gap.joblib", "A_severity.joblib", "C_readiness.joblib")
SCHEMA_VERSION = "c4-analysis-1.0"
PREREQ_TARGET = 0.5            # c4_engine adds a prerequisite to the roadmap when CV proficiency < 0.5
COVERAGE = 0.9                 # c4_engine.readiness_features: a requirement is covered at >= 90% of the required level

# Form learning methods -> resource_type values in learning_resources.csv.
METHOD_RESOURCE_TYPES = {
    "online_courses": ["course", "certification"], "video_tutorials": ["video"], "reading": ["documentation"],
    "hands_on_projects": ["project"], "interactive_exercises": ["project", "course"],
    "instructor_led": ["course"], "group_learning": ["course"], "other": [],
}
RESOURCE_TYPE_LABELS = {"course": "online course", "certification": "certification course", "video": "video",
                        "documentation": "documentation", "project": "hands-on project", "mixed": "mixed format"}

FACTORS = {
    "f_gap_severity": ("proficiency_gap", "Proficiency gap",
                       "(required level - CV proficiency) / required level, capped at 1"),
    "f_demand_velocity": ("labour_market_demand", "Labour-market demand (O*NET)",
                          "average of the O*NET 31.0 Hot Technology and In Demand flags for this career and skill"),
    "f_skill_dependency": ("prerequisite_dependency", "Prerequisite dependency",
                           "share of the other gap skills that need this skill as a prerequisite"),
    "f_career_relevance": ("career_relevance", "Career relevance (O*NET)",
                           "O*NET-derived importance of the skill for the career"),
    "f_user_confidence_inverse": ("low_confidence", "Low self-confidence",
                                  "1 - normalised self-rating (1 if not studied, 0.5 if not rated)"),
}

READINESS_LABELS = {
    "coverage_ratio": ("Required skills at the needed level", "percent"),
    "weighted_proficiency_ratio": ("Importance-weighted proficiency in required skills", "percent"),
    "essential_coverage_ratio": ("Essential skills at the needed level", "percent"),
    "critical_gap_count": ("Skills with a large importance-weighted gap", "count"),
    "hot_technology_coverage": ("O*NET Hot Technologies at the needed level", "percent"),
    "hidden_weakness_count": ("Skills rated well below your CV evidence", "count"),
    "num_projects": ("Relevant projects", "count"),
    "num_certifications": ("Relevant certifications", "count"),
    "num_internships": ("Relevant internships", "count"),
    "academic_year": ("Academic year (not collected; training average used)", "number"),
}
READINESS_GROUPS = {
    "Skill evidence from your CV": ["coverage_ratio", "weighted_proficiency_ratio", "essential_coverage_ratio",
                                    "critical_gap_count", "hot_technology_coverage", "hidden_weakness_count"],
    "Practical experience": ["num_projects", "num_certifications", "num_internships"],
    "Not collected": ["academic_year"],
}

PROJECT_TEMPLATES = {
    "programming": "Write a small command-line application that applies {skill}. It should read a CSV file, process the data and write a summary report. Include unit tests and a README.",
    "web": "Build and deploy a small responsive web page or app that uses {skill}, such as a personal portfolio or task tracker.",
    "data": "Analyse a public dataset using {skill}. Clean the data, answer three questions and publish your findings in a short report or notebook.",
    "data_engineering": "Build a small pipeline with {skill} that extracts data from a public source, transforms it and loads it into a database on a schedule.",
    "ai": "Train and evaluate a simple model using {skill} on a public dataset, and explain its results and limitations in a short report.",
    "security": "Set up a safe practice lab and use {skill} to assess a deliberately vulnerable application. Document your findings and recommended fixes.",
    "infrastructure": "Deploy a sample application using {skill} and document each step so another person can repeat the setup.",
    "design": "Design a clickable prototype for a small app using {skill}, test it with two users and record what you would change.",
    "quality": "Write a test plan for a small open-source project and automate key test cases using {skill}.",
    "management": "Plan a small team project using {skill} practices: define the scope, timeline, risks and a progress report.",
    "general": "Complete a small practical task that applies {skill}, then write a one-page summary of what you built and learned.",
}
CATEGORY_FAMILY = {
    "Programming": "programming", "Tools": "programming", "Blockchain": "programming", "Web": "web",
    "Data Science": "data", "Data": "data", "GIS": "data", "Research": "data", "Health IT": "data",
    "Information Management": "data", "Data Engineering": "data_engineering", "AI": "ai", "Security": "security",
    "Infrastructure": "infrastructure", "Cloud": "infrastructure", "DevOps": "infrastructure",
    "Hardware": "infrastructure", "Support": "infrastructure", "Architecture": "infrastructure",
    "Design": "design", "Quality": "quality", "Management": "management", "Professional": "management",
}
STAGE_ACTIVITIES = {
    "Beginner": ["Learn the core concepts of {skill} with the first recommended resource.",
                 "Complete short practice exercises after each topic.",
                 "Write brief notes that summarise key terms and examples."],
    "Intermediate": ["Study intermediate {skill} topics and apply each one in a small exercise.",
                     "Rebuild an example from a resource without looking at the solution.",
                     "Ask a peer or mentor for feedback on your work."],
    "Advanced": ["Study advanced {skill} patterns and recommended practices.",
                 "Apply {skill} to a realistic end-to-end scenario.",
                 "Document your design decisions and trade-offs."],
}
REVIEW_ACTIVITIES = ["Build a small piece of work that demonstrates {skill}.",
                     "Describe this work clearly in your CV or portfolio so the evidence is visible."]

LIMITATIONS = [
    "The trained models (skill gap, gap severity and readiness) were trained on synthetic data for 800 simulated students, "
    "as recorded in c4_config.json. They have not been validated with real students, so no accuracy is claimed.",
    "The readiness score summarises the available evidence for the selected career. It is not a probability of getting a job "
    "and it is not an assessment by an employer.",
    "Skill proficiency comes only from the evidence Component 01 found in your CV. Skills you have but did not describe in your CV are treated as missing.",
    "Self-reported confidence is used to flag possible over- or under-estimation and to rank priorities. It never increases your measured proficiency.",
    "Required levels and importance come from O*NET 31.0 and describe typical U.S. job requirements; local employers may differ.",
    "The labour-market demand factor uses O*NET Hot Technology and In Demand flags. The job_postings_monthly.csv trend file is synthetic, so it is not used for students.",
    "ESCO identifiers are empty in the current datasets, so ESCO data is not used.",
    "Study durations use fixed hour estimates per skill level (40, 60 and 80 hours to go from no proficiency to full proficiency) and your weekly hours. They are planning estimates only.",
    "Academic year is not collected in the form, so the readiness model uses the training average for it.",
]

_load_lock = threading.Lock()


@contextmanager
def _numpy2_pickle_compat():
    """The models were saved with NumPy 2.x and scikit-learn 1.6.1; this backend pins NumPy 1.26 and
    scikit-learn 1.5.2 for Component 03. NumPy 2 pickles random generators in a format NumPy 1.26
    cannot rebuild. Only the unused training RNG state is affected; predictions were checked to be
    identical to a scikit-learn 1.6.1 / NumPy 2 environment. The patch is active only while loading."""
    import numpy.random._pickle as npk
    original_bit, original_gen = npk.__bit_generator_ctor, npk.__generator_ctor
    compatible = {}

    def bit_generator_ctor(name="MT19937"):
        if isinstance(name, np.random.BitGenerator):
            return name
        name = name.__name__ if isinstance(name, type) else name
        if name not in compatible:
            def setstate(self, state):
                self.state = state[0] if isinstance(state, tuple) else state
            compatible[name] = type(name, (npk.BitGenerators[name],), {"__setstate__": setstate})
        return compatible[name]()

    npk.__bit_generator_ctor = bit_generator_ctor
    npk.__generator_ctor = lambda name="MT19937", bit_generator_ctor=None: original_gen(name, npk.__bit_generator_ctor)
    try:
        yield
    finally:
        npk.__bit_generator_ctor, npk.__generator_ctor = original_bit, original_gen


def _lower_first(text):
    return text[:1].lower() + text[1:]


def _to_level(value):
    """0-1 proficiency -> Component 01 rubric level (0-5)."""
    return int(round(float(value) * LEVEL_MAX))


def _target_level(value):
    return int(math.ceil(float(value) * LEVEL_MAX - 1e-9))


def _resource_level(proficiency):
    return "Beginner" if proficiency < 0.4 else "Intermediate" if proficiency < 0.7 else "Advanced"


class C4Analyzer(C4Engine):
    def __init__(self, inputs_dir=INPUTS_DIR, models_dir=MODELS_DIR):
        super().__init__(str(inputs_dir), None)          # models are loaded lazily, see ensure_models
        self.models_dir = Path(models_dir)
        self.category = self.cat.set_index("skill_id").category.to_dict()
        r = self.req
        self.onet_flags = {(c, s): (int(h), int(d)) for c, s, h, d in zip(r.career_id, r.skill_id, r.hot_technology, r.in_demand)}

    # ------------------------------------------------------------------ models
    def models_available(self):
        return all((self.models_dir / name).exists() for name in REQUIRED_MODEL_FILES)

    def ensure_models(self):
        if self.cfg:
            return
        with _load_lock:
            if self.cfg:
                return
            missing = [name for name in REQUIRED_MODEL_FILES if not (self.models_dir / name).exists()]
            if missing:
                raise ModelsUnavailable(f"Trained model files are missing from {self.models_dir.name}/: {', '.join(missing)}")
            try:
                from sklearn.exceptions import InconsistentVersionWarning
                with warnings.catch_warnings(), _numpy2_pickle_compat():
                    warnings.simplefilter("ignore", InconsistentVersionWarning)
                    self.load_models(str(self.models_dir))
            except Exception as exc:
                self.cfg, self.models = {}, {}
                raise ModelsUnavailable(f"The trained models could not be loaded: {exc}") from exc

    # ------------------------------------------------------------------ factor 2: real O*NET demand
    def priority_frame(self, g, st):
        pf = super().priority_frame(g, st)
        # job_postings_monthly.csv is synthetic, so the demand factor uses O*NET 31.0 flags instead.
        pf["f_demand_velocity"] = [sum(self.onet_flags.get((st["career_id"], s), (0, 0))) / 2 for s in pf.skill_id]
        return pf

    # ------------------------------------------------------------------ feature 3: adaptive resources
    def recommend_resources(self, skill_id, proficiency, resource_types, k=3):
        r = self.res[self.res.skill_id == skill_id]
        if r.empty:
            return []
        target = _resource_level(proficiency)
        adjacent = {"Beginner": "Intermediate", "Intermediate": "Advanced", "Advanced": "Intermediate"}[target]
        preferred = set(resource_types)
        score = (r.resource_type.isin(preferred) * 3.0 + (r.level == target) * 1.5 + (r.level == adjacent) * 0.5
                 + r.is_free * 0.3 + r.rating.fillna(4.0) / 10)
        ranked = r.assign(_score=score).sort_values(["_score", "resource_id"], ascending=[False, True])
        picks, per_type = [], {}
        for x in ranked.itertuples():                   # at most two resources of the same type
            if per_type.get(x.resource_type, 0) < 2:
                picks.append(x)
                per_type[x.resource_type] = per_type.get(x.resource_type, 0) + 1
            if len(picks) == k:
                break
        out = []
        for x in picks:
            why = []
            if x.resource_type in preferred:
                why.append(f"matches your preference for {RESOURCE_TYPE_LABELS.get(x.resource_type, x.resource_type)} learning")
            why.append(f"{x.level.lower()} level" + (" suits your current proficiency" if x.level == target else ""))
            if x.is_free:
                why.append("free to access")
            out.append(dict(resource_id=x.resource_id, title=x.title, type=x.resource_type, level=x.level,
                            duration_hours=None if np.isnan(x.duration_hours) else float(x.duration_hours),
                            rating=None if np.isnan(x.rating) else float(x.rating), is_free=bool(x.is_free),
                            provider=str(x.provider_type).replace("–", "-"), url=x.url, source=x.source,
                            why=why[0][0].upper() + "; ".join(why)[1:] + "."))
        return out

    # ------------------------------------------------------------------ feature 1: gap status
    def _gap_status(self, g):
        """Model A and the transparent evidence rule, combined:
        gap    - CV proficiency is below the O*NET required level (severity from the trained severity model);
        review - CV evidence meets the level but model A still flags the skill (for example a large
                 confidence/evidence mismatch), so the student should confirm it with practical work;
        met    - evidence meets the level and the model does not flag it."""
        X = g[A_FEATURES]
        g["gap_probability"] = self.models["A_gap"].predict_proba(X)[:, 1]
        flagged = g.gap_probability >= float(self.cfg["A"]["threshold"])
        severity = [SEVERITY[int(s)] for s in self.models["A_severity"].predict(X)]
        below = g.current_proficiency < COVERAGE * g.required_level - 1e-9
        g["status"] = np.where(below, "gap", np.where(flagged, "review", "met"))
        g["severity"] = [("minor" if s == "none" else s) if st == "gap" else "none" for s, st in zip(severity, g.status)]
        g["is_deficient"] = (g.status != "met").astype(int)
        return g

    # ------------------------------------------------------------------ feature 5: readiness
    def _readiness(self, g, activity):
        cm = self.models["C_readiness"]
        model = cm["model"]
        coef = dict(zip(C_FEATURES, model.coef_))
        mean = dict(zip(C_FEATURES, cm["train_mean"]))
        rf = self.readiness_features(g, {**activity, "academic_year": 0})
        rf["academic_year"] = float(mean["academic_year"])
        intercept = float(model.intercept_)
        terms = {f: dict(feature=f, label=READINESS_LABELS[f][0], unit=READINESS_LABELS[f][1], value=float(rf[f]),
                         coefficient=float(coef[f]), points=float(coef[f] * rf[f])) for f in C_FEATURES}
        raw = intercept + sum(t["points"] for t in terms.values())
        score = float(np.clip(raw, 0, 100))
        groups = [dict(name=name, points=sum(terms[f]["points"] for f in fs), terms=[terms[f] for f in fs])
                  for name, fs in READINESS_GROUPS.items()]
        ranked = sorted((t for f, t in terms.items() if f != "academic_year"), key=lambda t: t["points"])
        helped = [_lower_first(t["label"]) for t in ranked[::-1] if t["points"] > 0.5][:2]
        held = [_lower_first(t["label"]) for t in ranked if t["points"] < -0.5][:2]
        summary = f"Your readiness score is {score:.0f}/100 ({band_of(score)})."
        if helped:
            summary += f" It is mainly supported by {' and '.join(helped)}."
        if held:
            summary += f" It is reduced by {' and '.join(held)}."
        return dict(score=round(score, 1), band=band_of(score), raw_score=raw, intercept=intercept, groups=groups,
                    summary=summary, bands=[{"band": "Not ready", "range": "0-39"}, {"band": "Developing", "range": "40-59"},
                                            {"band": "Nearly ready", "range": "60-79"}, {"band": "Job ready", "range": "80-100"}],
                    formula="score = intercept + sum(coefficient x value), limited to 0-100. Coefficients come from the "
                            "trained linear readiness model (c4_config.json 'C').")

    # ------------------------------------------------------------------ feature 4: roadmap
    def _roadmap(self, st, g, prio):
        rows = {r.skill_id: r for r in g.itertuples()}
        types = st["preferences"].get("resource_types", [])
        steps = []
        for step in self.make_roadmap(st, g, prio):
            sid, name, stage = step["skill_id"], step["skill_name"], step["stage"]
            current = float(st["proficiencies"].get(sid, 0.0))
            row = rows.get(sid)
            status = row.status if row is not None else "prerequisite"
            target = COVERAGE * float(row.required_level) if row is not None else PREREQ_TARGET
            reason = {"gap": "Required for the career and below the required level",
                      "review": "Required for the career; your CV evidence meets the level but should be confirmed"}.get(
                status, step["reason"][0].upper() + step["reason"][1:])
            activities = [a.format(skill=name) for a in (REVIEW_ACTIVITIES if status == "review" else STAGE_ACTIVITIES[stage])]
            project = PROJECT_TEMPLATES[CATEGORY_FAMILY.get(self.category.get(sid), "general")].format(skill=name)
            milestones = [f"Reach Component 01 evidence level {max(_target_level(target), _to_level(current))}/5 in {name} "
                          f"(currently {_to_level(current)}/5), confirmed by uploading your updated CV.",
                          "Complete the practical project and add it to your CV or portfolio.",
                          f"Rate your confidence in {name} as 4 (Confident) or higher in your next assessment."]
            steps.append(dict(step=step["step"], skill_id=sid, skill_name=name, stage=stage, status=status, reason=reason,
                              prerequisites=step["prerequisites"], estimated_hours=step["estimated_hours"],
                              start_week=step["start_week"], end_week=step["end_week"],
                              current_level=_to_level(current), target_level=max(_target_level(target), _to_level(current)),
                              activities=activities, project=project, milestones=milestones,
                              resources=self.recommend_resources(sid, current, types)))
        stages = []
        for stage in STAGES:
            items = [s for s in steps if s["stage"] == stage]
            if not items:
                continue
            end = max(s["end_week"] for s in items)
            stages.append(dict(stage=stage, steps=items, start_week=min(s["start_week"] for s in items), end_week=end,
                               estimated_hours=round(sum(s["estimated_hours"] for s in items), 1),
                               milestone=f"By week {end}: reach the target evidence level in {len(items)} "
                                         f"{'skill' if len(items) == 1 else 'skills'} "
                                         f"({', '.join(s['skill_name'] for s in items)}) and complete "
                                         f"{len(items)} practical {'project' if len(items) == 1 else 'projects'}."))
        hours_pw = max(float(st["preferences"].get("weekly_study_hours", 6)), 1.0)
        return dict(weekly_hours=hours_pw, total_steps=len(steps),
                    total_hours=round(sum(s["estimated_hours"] for s in steps), 1),
                    total_weeks=max((s["end_week"] for s in steps), default=0), stages=stages)

    # ------------------------------------------------------------------ public entry point
    def analyze_assessment(self, c1, form):
        """c1: {"candidate_id", "skills": [{"name", "level", "confidence"}]} (may be empty);
        form: the stored C4 form (c4_engine form_json format plus learning_methods)."""
        self.ensure_models()
        st = self.student_from_json(c1, {}, form, form["career_id"])
        methods = (form.get("preferences") or {}).get("learning_methods") or []
        st["preferences"]["resource_types"] = list(dict.fromkeys(t for m in methods for t in METHOD_RESOURCE_TYPES.get(m, [])))
        ratings = {c["skill_id"]: c.get("rating") for c in form.get("confidence", [])}

        g = self._gap_status(self.gap_frame(st))
        gaps = g[g.is_deficient == 1]
        weights = self.cfg["B"]["weights"]
        priorities = []
        if len(gaps):
            pf = self.priority_frame(gaps, st)
            pf["priority_score"] = sum(pf[f] * weights[f] for f in FIVE)
            pf = pf.sort_values(["priority_score", "skill_name"], ascending=[False, True])
            status = g.set_index("skill_id").status.to_dict()
            for rank, r in enumerate(pf.to_dict("records"), 1):
                factors = [dict(key=FACTORS[f][0], label=FACTORS[f][1], definition=FACTORS[f][2], value=float(r[f]),
                                weight=float(weights[f]), points=float(r[f] * weights[f])) for f in FIVE]
                top = [_lower_first(x["label"]) for x in sorted(factors, key=lambda x: -x["points"])[:2]]
                priorities.append(dict(rank=rank, skill_id=r["skill_id"], skill_name=r["skill_name"],
                                       status=status[r["skill_id"]], priority_score=float(r["priority_score"]),
                                       factors=factors, why=f"Ranked by {top[0]} and {top[1]}."))
        prio = {p["skill_id"]: p["priority_score"] for p in priorities}
        rank_of = {p["skill_id"]: p["rank"] for p in priorities}

        evidence = {m["skill_id"]: m for m in st["skill_mapping"] if m["skill_id"]}
        evidence_label = {1: "low", 2: "medium", 3: "high"}
        skills = []
        for r in g.itertuples():
            rating = ratings.get(r.skill_id, "not_asked")
            notes = []
            if r.overconfidence_flag:
                notes.append("Your self-rating is higher than the evidence in your CV. Self-ratings are not counted as "
                             "proficiency, so show this skill in a project or certification and add it to your CV.")
            if r.hidden_weakness_flag:
                notes.append("Your CV evidence is stronger than your self-rating. You may be underestimating this skill.")
            if r.not_studied:
                notes.append("You reported that you have not studied this skill.")
            if rating == "not_asked":
                notes.append("No self-rating was collected for this skill.")
            source = evidence.get(r.skill_id)
            skills.append(dict(
                skill_id=r.skill_id, skill_name=r.skill_name, category=self.category.get(r.skill_id),
                skill_level=r.skill_level, is_essential=bool(r.is_essential), importance=r.importance,
                hot_technology=bool(self.onet_flags.get((st["career_id"], r.skill_id), (0, 0))[0]),
                in_demand=bool(self.onet_flags.get((st["career_id"], r.skill_id), (0, 0))[1]),
                required_proficiency=r.required_level, required_level=_target_level(COVERAGE * r.required_level),
                current_proficiency=r.current_proficiency, current_level=_to_level(r.current_proficiency),
                evidence_source=("derived from your programming languages" if source and source["c1_name"] == "(derived)"
                                 else "CV" if source else "none"),
                evidence_strength=evidence_label.get(st["evidence"].get(r.skill_id)),
                self_rating=None if rating == "not_asked" else rating, not_studied=bool(r.not_studied),
                status=r.status, severity=r.severity, gap_probability=r.gap_probability,
                overconfident=bool(r.overconfidence_flag), underconfident=bool(r.hidden_weakness_flag),
                priority_rank=rank_of.get(r.skill_id), notes=notes))
        order = {"gap": 0, "review": 1, "met": 2}
        skills.sort(key=lambda s: (order[s["status"]], s["priority_rank"] or 999, s["skill_name"]))

        unmapped = [m["c1_name"] for m in st["skill_mapping"] if not m["skill_id"]]
        warnings_ = [w for w in st["warnings"] if not w.startswith("C1 skills not in")]
        if not c1.get("skills"):
            warnings_.append("No CV skills were found for this assessment, so every required skill is treated as missing. "
                             "Upload your CV in Component 01 for a personalised analysis.")
        out = dict(
            schema_version=SCHEMA_VERSION, generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            candidate_id=st["candidate_id"],
            target_career=dict(career_id=st["career_id"], career_name=self.career_name[st["career_id"]]),
            inputs=dict(cv_skills_found=len(c1.get("skills", [])), cv_skills_matched=len({m["skill_id"] for m in st["skill_mapping"] if m["skill_id"]}),
                        cv_skills_not_in_catalogue=unmapped, self_ratings=len(ratings),
                        weekly_study_hours=st["preferences"].get("weekly_study_hours"), learning_methods=methods,
                        activity={k: st["activity"][k] for k in ("num_projects", "num_certifications", "num_internships")}),
            readiness=self._readiness(g, st["activity"]),
            skill_gaps=dict(summary=dict(required=len(skills), met=sum(s["status"] == "met" for s in skills),
                                         review=sum(s["status"] == "review" for s in skills),
                                         gaps=sum(s["status"] == "gap" for s in skills),
                                         critical=sum(s["severity"] == "critical" for s in skills)),
                            skills=skills),
            priorities=priorities,
            roadmap=self._roadmap(st, g, prio),
            method=dict(
                gap_analysis="Each O*NET requirement is compared with your CV proficiency (Component 01 level / 5). "
                             "A requirement is met when the proficiency reaches 90% of the O*NET required level (the coverage rule used by the "
                             "readiness model); otherwise it is a gap and the trained severity model "
                             "rates it minor, moderate or critical. When the evidence meets the level but the trained gap model "
                             f"(probability >= {float(self.cfg['A']['threshold']):.2f}) still flags it, it is marked for review.",
                priority_formula="priority = " + " + ".join(f"{weights[f]:.4f} x {_lower_first(FACTORS[f][1])}" for f in FIVE),
                priority_factors=[dict(key=FACTORS[f][0], label=FACTORS[f][1], definition=FACTORS[f][2], weight=weights[f]) for f in FIVE],
                priority_weights_source="Weights learned in the C4 training notebook (c4_config.json 'B') and used as a transparent weighted sum.",
                resource_ranking="Resources are ranked by your preferred learning methods, a level that suits your current proficiency, "
                                 "free access and rating (when available). At most two resources of the same type are shown.",
                roadmap_ordering="Skills are ordered so that prerequisites come first, then by level (Beginner, Intermediate, Advanced) "
                                 "and by priority. Missing prerequisites with CV proficiency below 0.5 are added automatically.",
                data_sources=["O*NET 31.0 occupation requirements, Hot Technology and In Demand flags (occupation_skill_requirements.csv)",
                              "C4 skills catalogue and prerequisite graph (skills_catalog.csv, skill_prerequisites.csv)",
                              "Learning resources from roadmap.sh and the Coursera dataset on Kaggle (learning_resources.csv)",
                              "Component 01 CV skill assessment and your C4 assessment answers"],
                limitations=LIMITATIONS),
            model_info=dict(versions=self.cfg.get("versions", {}), gap_model=self.cfg["A"]["model"],
                            readiness_model=self.cfg["C"]["model"]),
            warnings=warnings_,
        )
        return _clean(out)
