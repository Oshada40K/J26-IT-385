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
| `c4_engine.py` | Engine shared with the training notebook. Feature code unchanged; severity, status/message and verify steps added. |
| `analysis.py` | Student-facing analysis built on the engine and trained models (the five features below). |
| `service.py` | Skill selection for the form, C1 integration (read-only), saving assessments. |
| `repository.py` | Component-local SQLite store (`backend/.data/component04.sqlite3`, override with `C4_DATABASE_PATH`). |
| `router.py` | API under `/api/roadmap`. |
| `trained_models/` | `A_gap.joblib`, `A_severity.joblib`, `C_readiness.joblib`, `D_forecast.joblib`, `c4_config.json`. |
| `inputs/` | O*NET requirements, skills catalogue, prerequisites, learning resources. |

## Methods

**1. Confidence-aware gap analysis.** CV proficiency = C1 level / 5. `distance = max(required − proficiency, 0)`; severity uses CV evidence only (`c4_engine.cv_severity`): `none` if distance ≤ 0.05, `critical` if distance × (0.5 + 0.5 × importance) ≥ 0.25, otherwise `moderate`. A distance > 0.05 is always a gap, whatever the model or the self-rating says. A skill rated 4–5/5 with CV level 0–1/5 is **unverified** ("Claimed – not verified"); its roadmap step is "verify claimed skill" (10 hours, project and certification resources first). When evidence meets the level but the trained gap model (`A_gap`) still flags the skill, it is marked **review**. Each skill has a `status` and a plain-English `message` (the engine's `skill_gap_report` uses `unverified | gap | ok`). The readiness model's coverage inputs keep their trained 90% rule, so they are labelled "within 90% of the needed level".

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

## Claimed skills and optional proof

- The roadmap is always generated immediately from CV evidence + the C4 form; proof is optional and never awaited.
- Unverified (claimed) skills get `priority x 0.6` (`UNVERIFIED_PRIORITY_FACTOR`) and are re-ranked, so real gaps come first.
- `potential_score` re-runs the same readiness model with each claimed skill at `min(confidence, required level)`;
  it and `potential_skills` appear only when at least 1 point above `score`.

**Endpoints** (C4 is mounted at `/api/roadmap` in the shared `main.py`):

| Method | Path | Notes |
|---|---|---|
| POST | `/api/roadmap/evidence` | multipart/form-data (or JSON): `candidate_id`, `skill_id`, `proof_type` = github \| certificate_link \| certificate_file, `url` or `file` (PDF/PNG/JPG, max 5 MB), `description`. Returns the evidence + regenerated `analysis`. |
| GET | `/api/roadmap/evidence/{candidate_id}` | The student's evidence (own candidate only). |
| DELETE | `/api/roadmap/evidence/{evidence_id}` | Removes own evidence (and its file); returns the regenerated `analysis`. |
| POST | `/api/roadmap/evidence/{evidence_id}/recheck` | "Check again" for own GitHub / certificate links (e.g. GitHub was unreachable). Files: 400; already decided (verified or reviewed): 409. Returns the evidence + `analysis`. |
| POST | `/api/roadmap/evidence/{evidence_id}/review` | Reviewer decision `{"decision": "approve" \| "reject", "level": 1-3, "note": "..."}`. **403 unless `C4_ALLOW_REVIEW=1`.** There is no reviewer login yet, so keep it off outside local testing. Approve: `provisional` at `level` (default and max 3/5); reject: adds nothing. |

Invalid input returns **400** with a clear message (`errors.EvidenceError`). Files are stored in the private folder
`backend/.data/component04_evidence/` (override `C4_EVIDENCE_DIR`), named by evidence ID; the path is never returned.

Each evidence item has `status_reason` (one sentence: why it has this status), `check_details` (a list of
`{check, result: passed | failed | not_checked, detail}`), and `can_recheck`. Older rows whose `check_details` was a
plain string are returned as a one-item list.

**Simple checks** (`evidence_check.py`, run right after upload and on "Check again"):

| Proof | Check | Result |
|---|---|---|
| github | Link cleaned to `https://github.com/<owner>/<repo>` (removes `.git`, trailing `/`, `/tree/...`, `/blob/...`, query). GitHub REST API (`GITHUB_TOKEN` optional but recommended: 60 calls/hour without it; 5 s timeout, follows redirects for renamed repos): **1.** exists and not empty; **2.** ownership: the owner is one of the student's GitHub usernames from the latest C1 assessment (`external_profiles`), or one of them is in the contributors list (a fork alone does not count); **3.** skill usage (`SKILL_RULES`): languages, name/description/topics, README, file names (e.g. `serverless.yml`, `.aws/`), and up to 3 dependency files (e.g. `boto3`, `aws-sdk` in `requirements.txt` / `package.json`). | all pass: `provisional` 3/5; not found / empty / not the student's / no skill signs: `rejected` + reason; no GitHub username in C1: `pending` ("add your GitHub username in Component 01, then Check again"); network error / rate limit: `pending` ("Could not reach GitHub, try again.") |
| certificate_link | URL is never fetched; domain must be on `TRUSTED_CERTIFICATE_DOMAINS` | trusted: `provisional` 3/5; otherwise `pending` |
| certificate_file | cannot be checked automatically | `pending` review, counts as 2/5 until a reviewer decides |

**In the analysis:** proficiency = max(CV level, best usable proof level) / 5. Usable: provisional (capped at
`PROVISIONAL_LEVEL_LINK` = 3), pending file (`PROVISIONAL_LEVEL_FILE` = 2), verified (level from Component 01).
Rejected and pending links add nothing. Each skill has `evidence_status`, `evidence_source`
(`CV` / `GitHub (provisional)` / `Certificate (provisional)` / `Certificate (pending review)` /
`Certificate (reviewer approved)`), `evidence_level` and `evidence_detail` (the evidence's `status_reason`). Provisional proof therefore also raises the readiness score.

**Component 01 (main verifier):**
- `service.send_to_component01(evidence)` POSTs the evidence metadata to `C1_EVIDENCE_ENDPOINT` when that env var
  is set; a reply `{"level": 0-5}` marks it `verified` at that level. Not set: skipped silently. **TODO:** agree the
  contract with the Component 01 owner.
- **TODO:** Component 01 should call `service.on_c1_assessment_updated(candidate_id)` after
  `repository.save_assessment(...)` in `component01_skill/services/profile_service.py`. Until then the same check
  runs before every C4 analysis (pending/provisional proof becomes verified when the CV level rises).

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
.venv\Scripts\python -m unittest tests.component04_roadmap.test_c4 -v   # C4 only
.venv\Scripts\python -m unittest discover -s tests                   # whole backend (as in CI)
```

The GitHub API is mocked in the tests; no network calls are made.
