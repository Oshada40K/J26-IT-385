# Component 04 – Learning Roadmap & Skill Gap Analyzer

Owner: Dewmi. Frontend: `frontend/src/pages/component04/`. Route: `/component04`.

## Flow

1. **C1** extracts skills and evidence levels (0–5) from the student's CV.
2. **C3** recommends careers. The C4 page lists C3's top five; careers C4 supports can be selected (32 O*NET IT occupations).
3. **C4 assessment form** collects confidence ratings for 10–15 career skills, learning methods, weekly hours, projects, certifications and internships.
4. **C4 analysis** (`GET /api/roadmap/analysis/{assessment_id}`) is recomputed on every request from the **latest** C1 CV assessment and the stored form, so the roadmap changes when the CV is re-uploaded or the assessment is updated.

## Files

| File | Purpose |
|---|---|
| `c4_engine.py` | Original engine shared with the training notebook (features, roadmap ordering). Not modified. |
| `analysis.py` | Student-facing analysis built on the engine and trained models (the five features below). |
| `service.py` | Skill selection for the form, C1 integration (read-only), saving assessments. |
| `repository.py` | Component-local SQLite store (`backend/.data/component04.sqlite3`, override with `C4_DATABASE_PATH`). |
| `router.py` | API under `/api/roadmap`. |
| `trained_models/` | `A_gap.joblib`, `A_severity.joblib`, `C_readiness.joblib`, `D_forecast.joblib`, `c4_config.json`. |
| `inputs/` | O*NET requirements, skills catalogue, prerequisites, learning resources. |

## Methods

**1. Confidence-aware gap analysis.** CV proficiency = C1 level / 5. A requirement is **met** when proficiency ≥ 90% of the O*NET required level (the coverage rule in `readiness_features`), otherwise it is a **gap** with severity from the trained severity model (`A_severity`, HistGradientBoosting). When evidence meets the level but the trained gap model (`A_gap`, RandomForest, threshold from `c4_config.json`) still flags the skill, it is marked **review**. Self-ratings never change proficiency; they flag over-confidence (rating > evidence + 0.25) and under-confidence (evidence > rating + 0.25).

**2. Prioritisation.** `priority = Σ weight × factor`, weights learned in the notebook (`c4_config.json` "B", sum to 1):

| Factor | Definition | Weight |
|---|---|---|
| Proficiency gap | (required − proficiency) / required, capped at 1 | 0.0712 |
| Labour-market demand | mean of O*NET 31.0 Hot Technology and In Demand flags for the career/skill | 0.0985 |
| Prerequisite dependency | share of the other gap skills that need this skill | 0.3159 |
| Career relevance | O*NET-derived importance | 0.1689 |
| Low self-confidence | 1 − normalised rating (1 = not studied, 0.5 = not rated) | 0.3455 |

**3. Resources.** `learning_resources.csv` (roadmap.sh and the Coursera Kaggle dataset) ranked by the student's learning methods (+3), level suited to current proficiency (+1.5, adjacent +0.5), free (+0.3) and rating/10 (4.0 if missing); at most two of one type.

**4. Roadmap.** `make_roadmap` orders gap/review skills and missing prerequisites (proficiency < 0.5) topologically, then by level and priority. Steps are grouped into Beginner → Intermediate → Advanced (no prerequisite in the data has a higher level than its dependent skill). Hours = max(4, distance × 40/60/80 by level); weeks use the student's weekly hours. Each step has activities, a practical project, resources and measurable milestones (target C1 level, project, confidence ≥ 4).

**5. Readiness score.** `score = intercept + Σ coefficient × value` from the trained linear model (`C_readiness`), limited to 0–100 and shown term by term. Academic year is not collected, so its training mean is used.

## Data provenance and limitations

- The trained models were trained on **synthetic** data (800 simulated students, `c4_config.json`). No real-student validation or accuracy figures exist in this repository, and none are claimed.
- `job_postings_monthly.csv` is labelled **synthetic**, so the demand-trend signal (and `D_forecast`) is not shown to students; real O*NET flags are used instead.
- ESCO URIs are empty in the datasets, so ESCO is not used.
- The readiness score summarises evidence for one career; it is not an employment probability.
- C1 skills not in the 85-skill C4 catalogue are listed in the results and ignored.

## Model compatibility

The models were saved with scikit-learn 1.6.1 / NumPy 2.x; the backend pins scikit-learn 1.5.2 / NumPy 1.26.4 (Component 03). `analysis._numpy2_pickle_compat` lets NumPy 1.26 rebuild the pickled training RNG state while loading only. Gap and severity predictions were compared with a scikit-learn 1.6.1 / NumPy 2.2 environment on 5,929 feature rows: maximum probability difference 4.4e-16, no class differences.

`*.joblib` is git-ignored at the repository root, so the models are not in Git, CI or Railway. Without them the form still works and the analysis endpoint returns 503 with an explanation; model tests are skipped.

## Tests

```bash
cd backend
.venv\Scripts\python -m unittest tests.component04_roadmap.test_c4 -v
```
