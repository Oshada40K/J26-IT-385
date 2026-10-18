"""
Component 4 – Learning Roadmap & Skill Gap Analyzer: the engine used in TRAINING and in the LIVE system.

    from c4_engine import C4Engine
    eng = C4Engine("inputs", "models")                 # models folder written by the training notebook
    out = eng.run(c1_json, c3_json, form_json)         # -> dict, ready to return as JSON to the frontend
    out2 = eng.update(out["_student"], {"confidence": {"SK018": 4}})   # dynamic regeneration

Inputs (same formats as the team's components):
  c1_json   Component 1 output: {"candidate_id", "skills": [{"name", "level" 0–5, "confidence" low/medium/high}, ...]}
  c3_json   Component 3 output: {"top_jobs": {"candidate_id", "jobs": [{"ranking", "job", "score"}, ...]}}
  form_json C4 frontend form:   {"candidate_id", "career_id" (optional, the student's chosen career),
                                 "confidence": [{"skill_id", "rating": 1–5 | null = not studied}],
                                 "preferences": {...}, "activity": {...}}
Training and live use share the same feature code, so the models see identical inputs in both.
"""
import difflib, heapq, json, math, os, re, time
import numpy as np
import pandas as pd

LEVEL_MAX = 5                                   # C1 rubric levels 0–5 (confirmed by the C1 owner)
EVIDENCE = {"low": 1, "medium": 2, "high": 3}
LEVEL_ORD = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
STAGES = ["Beginner", "Intermediate", "Advanced"]
BASE_HOURS = {"Beginner": 40, "Intermediate": 60, "Advanced": 80}   # hours to go from 0 to 1 proficiency
BANDS = [(40, "Not ready"), (60, "Developing"), (80, "Nearly ready"), (101, "Job ready")]
SEVERITY = ["none", "moderate", "critical"]

A_FEATURES = ["current_proficiency", "required_level", "importance", "is_essential", "skill_level_ord",
              "confidence_norm", "confidence_missing", "not_studied", "competency_distance",
              "confidence_proficiency_gap", "hidden_weakness_flag", "overconfidence_flag",
              "skill_in_c1_profile", "c1_evidence_strength", "prereqs_met_ratio"]
FIVE = ["f_gap_severity", "f_demand_velocity", "f_skill_dependency", "f_career_relevance", "f_user_confidence_inverse"]
B_FEATURES = FIVE + ["f_hidden_weakness", "f_unmet_prereq_count", "f_is_essential", "f_demand_level"]
C_FEATURES = ["coverage_ratio", "weighted_proficiency_ratio", "essential_coverage_ratio", "critical_gap_count",
              "hot_technology_coverage", "hidden_weakness_count", "num_projects",
              "num_certifications", "num_internships", "academic_year"]
C_LABELS = {"coverage_ratio": "required skills already at the needed level",
            "weighted_proficiency_ratio": "overall proficiency in the career's skills",
            "essential_coverage_ratio": "essential skills already covered",
            "critical_gap_count": "critical skill gaps", "hot_technology_coverage": "in-demand technologies covered",
            "mean_confidence_norm": "your confidence in the career's skills", "hidden_weakness_count": "hidden weaknesses",
            "num_projects": "projects completed", "num_certifications": "certifications",
            "num_internships": "internships", "academic_year": "academic year"}
FACTOR_LABELS = {"f_gap_severity": "large gap", "f_demand_velocity": "rising job demand",
                 "f_skill_dependency": "unlocks other skills", "f_career_relevance": "important for the career",
                 "f_user_confidence_inverse": "low confidence"}

ALIASES = {
    "github": "Git", "gitlab": "Git", "bitbucket": "Git", "version control": "Git", "html": "HTML and CSS",
    "css": "HTML and CSS", "html5": "HTML and CSS", "css3": "HTML and CSS", "mysql": "SQL", "sql server": "SQL",
    "t-sql": "SQL", "pl/sql": "SQL", "sqlite": "SQL", "postgres": "PostgreSQL", "bash": "Bash Scripting",
    "shell scripting": "Bash Scripting", "shell": "Bash Scripting", "unix": "Linux", "ubuntu": "Linux",
    "js": "JavaScript", "ts": "TypeScript", "reactjs": "React", "react.js": "React", "node": "Node.js",
    "nodejs": "Node.js", "springboot": "Spring Boot", "spring": "Spring Boot", "asp.net": ".NET", "dotnet": ".NET",
    "c sharp": "C#", "cpp": "C++", "amazon web services": "AWS", "azure": "Microsoft Azure", "k8s": "Kubernetes",
    "excel": "Microsoft Excel", "powerbi": "Power BI", "scikit-learn": "Machine Learning", "sklearn": "Machine Learning",
    "tensorflow": "Deep Learning", "pytorch": "Deep Learning", "keras": "Deep Learning",
    "oop": "Object-Oriented Programming", "dsa": "Data Structures and Algorithms", "rest": "REST API Design",
    "rest api": "REST API Design", "restful api": "REST API Design", "jenkins": "CI/CD", "github actions": "CI/CD",
    "scrum": "Agile and Scrum", "agile": "Agile and Scrum", "unity3d": "Unity", "llm": "Generative AI and LLMs",
    "chatgpt": "Generative AI and LLMs", "nlp": "Natural Language Processing", "ux": "UI/UX Design",
    "ui/ux": "UI/UX Design", "ui design": "UI/UX Design", "mongo": "MongoDB", "jsp servlets": "Java",
    "mern stack": "Node.js", "jupiter notebook": "Python", "jupyter notebook": "Python", "pandas": "Pandas",
}
LANGUAGE_IDS = {"SK002", "SK003", "SK004", "SK005", "SK006", "SK007", "SK082", "SK083", "SK084", "SK085"}
RESOURCE_TYPES = {"video", "project", "documentation", "course", "certification", "mixed"}

# Gap severity from CV evidence only, and "claimed but unverified" skills.
GAP_TOLERANCE = 0.05            # distance <= 0.05 counts as no gap
CLAIM_CONFIDENCE = 0.75         # self-rating 4-5/5 ((rating - 1) / 4 >= 0.75)
CLAIM_MAX_PROFICIENCY = 0.2     # CV level 0-1/5
VERIFY_REASON = "verify claimed skill"
VERIFY_HOURS = 10.0
VERIFY_TYPES = ("project", "certification")   # preferred resources for verifying a claim
# The student may already know this skill, so real gaps come first.
UNVERIFIED_PRIORITY_FACTOR = 0.6


def cv_severity(distance, importance):
    """Severity from the CV gap only; self-rated confidence can never make a gap smaller."""
    if distance <= GAP_TOLERANCE + 1e-9:
        return "none"
    return "critical" if distance * (0.5 + 0.5 * importance) >= 0.25 else "moderate"


def is_unverified(confidence_missing, confidence_norm, proficiency):
    """Rated 4-5/5 by the student, but CV level 0-1/5."""
    return (not confidence_missing) and confidence_norm >= CLAIM_CONFIDENCE and proficiency <= CLAIM_MAX_PROFICIENCY + 1e-9


def gap_message(status, confidence_norm, proficiency, required_level):
    """Short plain-English text for the UI."""
    cv_level = int(round(proficiency * LEVEL_MAX))
    if status == "unverified":
        rating = int(round(confidence_norm * 4 + 1))
        evidence = "no evidence" if cv_level == 0 else "very little evidence"
        return f"You rated yourself {rating}/5, but your CV shows {evidence}. Add a project or certificate to verify it."
    if status == "gap":
        needed = int(math.ceil((required_level - GAP_TOLERANCE) * LEVEL_MAX - 1e-9))
        return f"Your CV shows level {cv_level}/5, but this career needs about {needed}/5."
    return "Your CV evidence meets the required level."


def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def band_of(score):
    for upper, name in BANDS:
        if score < upper:
            return name
    return BANDS[-1][1]


class C4Engine:
    def __init__(self, inputs_dir, models_dir=None):
        rd = lambda f: pd.read_csv(os.path.join(inputs_dir, f))
        self.cat = rd("skills_catalog.csv")
        self.occ = rd("occupations.csv")
        self.req = rd("occupation_skill_requirements.csv")
        self.res = rd("learning_resources.csv")
        self.postings = rd("job_postings_monthly.csv")
        pre = rd("skill_prerequisites.csv")
        self.name = self.cat.set_index("skill_id").skill_name.to_dict()
        self.level = self.cat.set_index("skill_id").skill_level.to_dict()
        self.hot = set(self.cat.loc[self.cat.is_hot_technology == 1, "skill_id"])
        self.pre = {s: set() for s in self.cat.skill_id}
        for r in pre.itertuples():
            self.pre[r.skill_id].add(r.prerequisite_skill_id)
        self.anc = {}
        for s in self.pre:
            self._ancestors(s)
        self.by_name = {_norm(n): s for s, n in self.name.items()}
        self.title_to_code = {_norm(t): c for c, t in zip(self.occ.career_id, self.occ.career_name)}
        self.career_name = self.occ.set_index("career_id").career_name.to_dict()
        self.req_by_career = {c: g.reset_index(drop=True) for c, g in self.req.groupby("career_id")}
        self.demand = self.demand_table()
        self.models, self.cfg = {}, {}
        if models_dir and os.path.exists(os.path.join(models_dir, "c4_config.json")):
            self.load_models(models_dir)

    def _ancestors(self, s, stack=()):
        if s in stack:
            raise ValueError(f"Cycle in skill prerequisites at {s}")
        if s not in self.anc:
            a = set(self.pre[s])
            for p in self.pre[s]:
                a |= self._ancestors(p, stack + (s,))
            self.anc[s] = a
        return self.anc[s]

    # ------------------------------------------------------------------ demand velocity (formula)
    def demand_table(self, window=6):
        j = self.postings
        last = sorted(j.period.unique())[-window:]
        rows = []
        for sk, g in j[j.period.isin(last)].sort_values("period").groupby("skill_id"):
            slope = np.polyfit(np.arange(len(g)), np.log(g.posting_share.clip(lower=1e-6)), 1)[0]
            rows.append(dict(skill_id=sk, slope_6m_log=slope, latest_share=g.posting_share.iloc[-1]))
        d = pd.DataFrame(rows)
        mm = lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else x * 0
        d["demand_velocity"] = mm(d.slope_6m_log).round(4)
        d["demand_level"] = mm(d.latest_share).round(4)
        d["trend"] = np.where(d.slope_6m_log > 0.01, "rising", np.where(d.slope_6m_log < -0.01, "declining", "stable"))
        return d.set_index("skill_id")

    # ------------------------------------------------------------------ input adapter (C1 + C3 + form)
    def map_skill(self, name):
        n = _norm(name)
        if n in self.by_name:
            return self.by_name[n], "exact"
        if n in ALIASES and _norm(ALIASES[n]) in self.by_name:
            return self.by_name[_norm(ALIASES[n])], "alias"
        best = difflib.get_close_matches(n, list(self.by_name), n=1, cutoff=0.88)
        if best:
            return self.by_name[best[0]], "fuzzy"
        return None, "unmapped"

    def student_from_json(self, c1, c3, form=None, target_career_id=None):
        form = form or {}
        cid = c1.get("candidate_id") or form.get("candidate_id")
        c3_cid = (c3.get("top_jobs") or {}).get("candidate_id") or (c3.get("best_job") or {}).get("candidate_id")
        warnings = []
        if c3_cid and cid and c3_cid != cid:
            raise ValueError("C1 and C3 outputs belong to different candidates")
        if form.get("candidate_id") and cid and form["candidate_id"] != cid:
            raise ValueError("Form and C1 output belong to different candidates")
        prof, evid, mapping = {}, {}, []
        for s in c1.get("skills", []):
            sid, method = self.map_skill(s["name"])
            p = float(np.clip(float(s.get("level", 0)) / LEVEL_MAX, 0, 1))
            mapping.append(dict(c1_name=s["name"], level=s.get("level"), skill_id=sid,
                                skill_name=self.name.get(sid), method=method))
            if sid:
                if p >= prof.get(sid, -1):
                    evid[sid] = EVIDENCE.get(str(s.get("confidence", "")).lower(), 1)
                prof[sid] = max(prof.get(sid, 0.0), p)
        langs = [prof[s] for s in prof if s in LANGUAGE_IDS]
        if langs and "SK001" not in prof:
            prof["SK001"], evid["SK001"] = max(langs), 1
            mapping.append(dict(c1_name="(derived)", level=None, skill_id="SK001",
                                skill_name=self.name["SK001"], method="derived from programming languages"))
        unmapped = [m["c1_name"] for m in mapping if m["skill_id"] is None]
        if unmapped:
            warnings.append(f"C1 skills not in the C4 catalogue: {unmapped}")
        jobs = (c3.get("top_jobs") or {}).get("jobs") or []
        if not jobs and (c3.get("best_job") or {}).get("best_job"):
            jobs = [{"ranking": 1, "job": c3["best_job"]["best_job"], "score": None}]
        options = []
        for j in sorted(jobs, key=lambda x: x.get("ranking", 99)):
            code = j.get("onet_code") or self.title_to_code.get(_norm(j.get("job", "")))
            options.append(dict(rank=j.get("ranking"), career_name=j.get("job"), career_id=code,
                                c3_score=j.get("score"), supported=code in self.req_by_career))
        chosen = target_career_id or form.get("career_id")
        if chosen and chosen not in self.req_by_career:
            raise ValueError(f"Career {chosen} is not one of C4's {len(self.req_by_career)} occupations")
        if not chosen:
            sup = [o for o in options if o["supported"]]
            if not sup:
                raise ValueError("None of Component 3's careers is supported by Component 4")
            chosen = sup[0]["career_id"]
            if options and not options[0]["supported"]:
                warnings.append(f"C3's top job '{options[0]['career_name']}' is outside C4's IT occupations; "
                                f"using '{sup[0]['career_name']}'")
        conf, asked = {}, set()
        for c in form.get("confidence", []):
            sid = c.get("skill_id")
            if sid in self.name:
                asked.add(sid)
                r = c.get("rating")
                conf[sid] = None if r is None else float(np.clip((float(r) - 1) / 4, 0, 1))
        act = dict(academic_year=3, num_projects=0, num_certifications=0, num_internships=0)
        act.update({k: int(v) for k, v in (form.get("activity") or {}).items() if k in act and v is not None})
        prefs = dict(preferred_resource_type="project", secondary_resource_type="video",
                     weekly_study_hours=6.0, prefers_free_resources=1)
        prefs.update({k: v for k, v in (form.get("preferences") or {}).items() if k in prefs and v is not None})
        if not form:
            warnings.append("No C4 form submitted: confidence, activity and preferences use defaults")
        return dict(candidate_id=cid, career_id=chosen, career_options=options, proficiencies=prof,
                    evidence=evid, confidence=conf, confidence_asked=sorted(asked), activity=act,
                    preferences=prefs, skill_mapping=mapping, warnings=warnings)

    def confidence_questions(self, career_id, c1=None):
        """Skills the frontend form should ask about: the career's required skills + C1 skills."""
        sk = list(self.req_by_career[career_id].skill_id)
        if c1:
            for s in c1.get("skills", []):
                sid, _ = self.map_skill(s["name"])
                if sid and sid not in sk:
                    sk.append(sid)
        return [dict(skill_id=s, skill_name=self.name[s], skill_level=self.level[s]) for s in sk]

    # ------------------------------------------------------------------ features (shared with training)
    def gap_frame(self, st):
        req = self.req_by_career[st["career_id"]]
        P, C = st["proficiencies"], st["confidence"]
        rows = []
        for r in req.itertuples():
            p = float(P.get(r.skill_id, 0.0))
            asked = r.skill_id in C
            c = C.get(r.skill_id)
            not_studied = int(asked and c is None)
            cn = 0.0 if not_studied else (0.5 if c is None else c)
            pres = self.pre[r.skill_id]
            rows.append(dict(
                skill_id=r.skill_id, skill_name=r.skill_name, current_proficiency=p,
                required_level=float(r.required_level), importance=float(r.importance), is_essential=int(r.is_essential),
                skill_level=self.level[r.skill_id], skill_level_ord=LEVEL_ORD[self.level[r.skill_id]],
                confidence_norm=cn, confidence_missing=int(not asked), not_studied=not_studied,
                competency_distance=max(float(r.required_level) - p, 0.0),
                confidence_proficiency_gap=p - cn, hidden_weakness_flag=int(asked and p - cn > 0.25),
                overconfidence_flag=int(asked and cn - p > 0.25), skill_in_c1_profile=int(r.skill_id in P),
                c1_evidence_strength=st["evidence"].get(r.skill_id, 0),
                prereqs_met_ratio=float(np.mean([P.get(q, 0) >= 0.5 for q in pres])) if pres else 1.0))
        return pd.DataFrame(rows)

    def priority_frame(self, g, st):
        gaps = set(g.skill_id)
        dv = self.demand
        rows = []
        for r in g.itertuples():
            unlocks = sum(1 for o in gaps if o != r.skill_id and r.skill_id in self.anc[o])
            rows.append(dict(
                skill_id=r.skill_id, skill_name=r.skill_name,
                f_gap_severity=min(r.competency_distance / max(r.required_level, 1e-6), 1.0),
                f_demand_velocity=float(dv.demand_velocity.get(r.skill_id, 0.5)),
                f_skill_dependency=unlocks / max(len(gaps) - 1, 1),
                f_career_relevance=r.importance, f_user_confidence_inverse=1 - r.confidence_norm,
                f_hidden_weakness=r.hidden_weakness_flag,
                f_unmet_prereq_count=len(self.anc[r.skill_id] & gaps), f_is_essential=r.is_essential,
                f_demand_level=float(dv.demand_level.get(r.skill_id, 0.5))))
        return pd.DataFrame(rows, columns=["skill_id", "skill_name"] + B_FEATURES)

    def readiness_features(self, g, activity):
        cov = lambda z: float((z.current_proficiency >= 0.9 * z.required_level).mean()) if len(z) else 1.0
        ess, hot = g[g.is_essential == 1], g[g.skill_id.isin(self.hot)]
        f = dict(coverage_ratio=cov(g),
                 weighted_proficiency_ratio=float((np.minimum(g.current_proficiency / g.required_level, 1) * g.importance).sum()
                                                  / g.importance.sum()),
                 essential_coverage_ratio=cov(ess),
                 critical_gap_count=int(((g.required_level - g.current_proficiency) * g.importance > 0.25).sum()),
                 hot_technology_coverage=cov(hot), mean_confidence_norm=float(g.confidence_norm.mean()),
                 hidden_weakness_count=int(g.hidden_weakness_flag.sum()))
        f.update({k: int(activity[k]) for k in ("num_projects", "num_certifications", "num_internships", "academic_year")})
        return f

    # ------------------------------------------------------------------ models
    def load_models(self, models_dir):
        import joblib
        self.cfg = json.load(open(os.path.join(models_dir, "c4_config.json")))
        for k in ("A_gap", "A_severity", "C_readiness", "D_forecast", "B_ranker"):
            p = os.path.join(models_dir, f"{k}.joblib")
            if os.path.exists(p):
                self.models[k] = joblib.load(p)

    def _require_models(self):
        if not self.cfg:
            raise RuntimeError("No trained models loaded – run the training notebook first")

    # ------------------------------------------------------------------ analysis
    def analyze(self, st):
        self._require_models()
        t0 = time.perf_counter()
        g = self.gap_frame(st)
        X = g[A_FEATURES]
        g["p_deficient"] = self.models["A_gap"].predict_proba(X)[:, 1]
        g["is_deficient"] = (g.p_deficient >= self.cfg["A"]["threshold"]).astype(int)
        # Severity from CV evidence only; a CV gap > 0.05 is always deficient, whatever the model says.
        g["severity"] = [cv_severity(d, imp) for d, imp in zip(g.competency_distance, g.importance)]
        g.loc[g.severity != "none", "is_deficient"] = 1
        g["unverified"] = self.claimed_mask(g, st)
        g["status"] = np.where(g.unverified, "unverified", np.where(g.is_deficient == 1, "gap", "ok"))

        # ---- priorities (transparent learned weighted score)
        gaps = g[g.is_deficient == 1]
        pf = self.priority_frame(gaps, st)
        w = self.cfg["B"]["weights"]
        priorities = []
        if len(pf):
            contrib = pd.DataFrame({f: pf[f] * w[f] for f in FIVE})
            pf["priority_score"] = contrib.sum(axis=1)
            claimed = set(g.loc[g.status == "unverified", "skill_id"])
            pf["priority_score"] *= [UNVERIFIED_PRIORITY_FACTOR if s in claimed else 1.0 for s in pf.skill_id]
            pf = pf.join(contrib.add_prefix("contrib_")).sort_values("priority_score", ascending=False)  # re-rank
            pf["priority_rank"] = np.arange(1, len(pf) + 1)
            for r in pf.itertuples():
                top = sorted(FIVE, key=lambda f: -getattr(r, "contrib_" + f))[:2]
                priorities.append(dict(priority_rank=r.priority_rank, skill_id=r.skill_id, skill_name=r.skill_name,
                                       priority_score=r.priority_score,
                                       factor_contributions={f.replace("f_", ""): getattr(r, "contrib_" + f) for f in FIVE},
                                       why=" + ".join(FACTOR_LABELS[f] for f in top)))
        prio = {p["skill_id"]: p["priority_score"] for p in priorities}

        # ---- readiness (explainable linear model)
        rf = self.readiness_features(g, st["activity"])
        cm = self.models["C_readiness"]
        x = np.array([rf[f] for f in C_FEATURES], float)
        score = float(np.clip(cm["model"].predict(pd.DataFrame([rf])[C_FEATURES])[0], 0, 100))
        contrib = cm["coef"] * (x - cm["train_mean"])
        order = np.argsort(contrib)
        expl = [dict(feature=C_FEATURES[i], label=C_LABELS[C_FEATURES[i]], value=rf[C_FEATURES[i]],
                     average=float(cm["train_mean"][i]), points=float(contrib[i]))
                for i in list(order[::-1][:3]) + list(order[:3])]

        roadmap = self.make_roadmap(st, g, prio)
        out = dict(
            schema_version="c4-2.0", candidate_id=st["candidate_id"],
            target_career=dict(career_id=st["career_id"], career_name=self.career_name[st["career_id"]]),
            career_options=st["career_options"],
            career_readiness=dict(score=score, band=band_of(score), base_score=float(cm["base"]),
                                  features=rf, explanation=expl,
                                  summary=self._readiness_text(score, expl),
                                  **self.potential_readiness(g, st["activity"], score, lambda f: float(np.clip(
                                      cm["model"].predict(pd.DataFrame([f])[C_FEATURES])[0], 0, 100)))),
            skill_gap_report=[dict(skill_id=r.skill_id, skill_name=r.skill_name, current_proficiency=r.current_proficiency,
                                   required_level=r.required_level, importance=r.importance, is_essential=r.is_essential,
                                   confidence=None if r.confidence_missing else r.confidence_norm,
                                   p_deficient=r.p_deficient, is_deficient=r.is_deficient, severity=r.severity,
                                   hidden_weakness=bool(r.hidden_weakness_flag), overconfident=bool(r.overconfidence_flag),
                                   status=r.status,
                                   message=gap_message(r.status, r.confidence_norm, r.current_proficiency, r.required_level),
                                   evidence_status=st.get("evidence_status", {}).get(r.skill_id, "none"),
                                   evidence_source=st.get("evidence_source", {}).get(r.skill_id)
                                   or ("CV" if r.skill_in_c1_profile else "none"))
                              for r in g.sort_values("p_deficient", ascending=False).itertuples()],
            priorities=priorities, roadmap=roadmap,
            skill_mapping=st["skill_mapping"], warnings=st["warnings"],
            model_versions=self.cfg.get("versions", {}))
        out["latency_seconds"] = time.perf_counter() - t0
        out = _clean(out)
        out["_student"] = st
        return out

    def claimed_mask(self, g, st):
        """Unverified (claimed) skills; a skill whose proof was verified is no longer claimed."""
        verified = set(st.get("verified_skills", []))
        return [is_unverified(m, c, p) and s not in verified for s, m, c, p in
                zip(g.skill_id, g.confidence_missing, g.confidence_norm, g.current_proficiency)]

    def potential_readiness(self, g, activity, score, score_fn):
        """Readiness with the SAME model if each unverified skill were verified at min(confidence, required level).
        Returned only when it is at least 1 point above the real (CV-only) score."""
        mask = (g.status == "unverified").to_numpy()
        if not mask.any():
            return {}
        claimed = np.minimum(g.confidence_norm, g.required_level)
        g2 = g.copy()
        g2.loc[mask, "current_proficiency"] = claimed[mask]
        potential = score_fn(self.readiness_features(g2, activity))
        if round(potential) < round(score) + 1:
            return {}
        skills = [r.skill_name for r, c, m in zip(g.itertuples(), claimed, mask) if m and c > r.current_proficiency]
        return dict(potential_score=int(round(potential)), potential_skills=skills)

    def _readiness_text(self, score, expl):
        up = [e for e in expl if e["points"] > 0.5][:2]
        down = [e for e in expl if e["points"] < -0.5][:2]
        t = f"Readiness {score:.0f}/100 ({band_of(score)})."
        if up:
            t += " Helped by: " + "; ".join(f"{e['label']} {e['value']:.2g} vs average {e['average']:.2g} "
                                            f"(+{e['points']:.1f})" for e in up) + "."
        if down:
            t += " Held back by: " + "; ".join(f"{e['label']} {e['value']:.2g} vs average {e['average']:.2g} "
                                               f"({e['points']:.1f})" for e in down) + "."
        return t

    def make_roadmap(self, st, g, prio):
        P = st["proficiencies"]
        steps = {r.skill_id: dict(skill_id=r.skill_id, distance=max(r.competency_distance, 0.1), reason="career gap",
                                  priority=prio.get(r.skill_id, 0.0))
                 for r in g[g.is_deficient == 1].itertuples()}
        deficient = g[g.is_deficient == 1]                                  # claimed but not shown in the CV
        claimed = {s for s, c in zip(deficient.skill_id, self.claimed_mask(deficient, st)) if c}
        for sid in claimed:
            steps[sid]["reason"] = VERIFY_REASON
        for sid in list(steps):                                     # add missing prerequisites (proficiency < 0.5)
            for q in self.anc[sid]:
                if q not in steps and P.get(q, 0) < 0.5:
                    steps[q] = dict(skill_id=q, distance=0.5 - P.get(q, 0), priority=steps[sid]["priority"],
                                    reason=f"prerequisite for {self.name[sid]}")
                elif q in steps:
                    steps[q]["priority"] = max(steps[q]["priority"], steps[sid]["priority"])
        ids = set(steps)
        indeg = {s: len(self.pre[s] & ids) for s in ids}
        heap = [(LEVEL_ORD[self.level[s]], -steps[s]["priority"], s) for s in ids if indeg[s] == 0]
        heapq.heapify(heap)
        order = []
        while heap:
            _, _, s = heapq.heappop(heap)
            order.append(s)
            for t in ids:
                if s in self.pre[t]:
                    indeg[t] -= 1
                    if indeg[t] == 0:
                        heapq.heappush(heap, (LEVEL_ORD[self.level[t]], -steps[t]["priority"], t))
        hours_pw = max(float(st["preferences"].get("weekly_study_hours", 6)), 1.0)
        week, out = 0.0, []
        for i, s in enumerate(order, 1):
            lvl = self.level[s]
            hours = VERIFY_HOURS if s in claimed else max(4.0, steps[s]["distance"] * BASE_HOURS[lvl])
            start = week
            week += hours / hours_pw
            out.append(dict(step=i, skill_id=s, skill_name=self.name[s], stage=lvl, reason=steps[s]["reason"],
                            prerequisites=sorted(self.name[q] for q in self.pre[s] & ids),
                            estimated_hours=round(hours, 1), start_week=int(math.floor(start)) + 1,
                            end_week=int(math.ceil(week)),
                            resources=self.pick_resources(s, lvl, st["preferences"],
                                                          first_types=VERIFY_TYPES if s in claimed else ())))
        return out

    def pick_resources(self, sid, stage, prefs, k=2, first_types=()):
        """first_types: resource types ranked before the student's preference (in order)."""
        r = self.res[self.res.skill_id == sid]
        if r.empty:
            return []
        pt, st2 = prefs.get("preferred_resource_type"), prefs.get("secondary_resource_type")
        free = int(prefs.get("prefers_free_resources", 0))
        s = ((r.resource_type == pt) * 3.0 + (r.resource_type == st2) * 1.5 + (pt == "mixed") * 1.0
             + (r.level == stage) * 0.7 + (r.is_free * free) * 0.8 + r.rating.fillna(4.0) / 10)
        for i, t in enumerate(first_types):                         # e.g. project +20, certification +10
            s = s + (r.resource_type == t) * (20.0 / (i + 1))
        r = r.assign(_s=s).sort_values("_s", ascending=False)
        picks = r.drop_duplicates("resource_type").head(k) if pt == "mixed" else r.head(k)
        return [dict(resource_id=x.resource_id, title=x.title, type=x.resource_type, level=x.level,
                     duration_hours=x.duration_hours, is_free=int(x.is_free), provider=x.provider_type, url=x.url)
                for x in picks.itertuples()]

    # ------------------------------------------------------------------ public API
    def run(self, c1, c3, form=None, target_career_id=None):
        return self.analyze(self.student_from_json(c1, c3, form, target_career_id))

    def update(self, st, changes):
        """Dynamic regeneration. changes: {"proficiencies": {sid: 0–1}, "confidence": {sid: 1–5 | None},
        "activity": {...}, "preferences": {...}, "career_id": "..."}"""
        st = json.loads(json.dumps(st))
        for sid, v in (changes.get("proficiencies") or {}).items():
            st["proficiencies"][sid] = float(v)
        for sid, r in (changes.get("confidence") or {}).items():
            st["confidence"][sid] = None if r is None else float(np.clip((float(r) - 1) / 4, 0, 1))
        st["activity"].update(changes.get("activity") or {})
        st["preferences"].update(changes.get("preferences") or {})
        if changes.get("career_id"):
            if changes["career_id"] not in self.req_by_career:
                raise ValueError("Unknown career_id")
            st["career_id"] = changes["career_id"]
        out = self.analyze(st)
        out["trigger"] = ", ".join(k for k in changes)
        return out


def to_json(out):
    return json.dumps({k: v for k, v in out.items() if not k.startswith("_")}, indent=2, ensure_ascii=False)
