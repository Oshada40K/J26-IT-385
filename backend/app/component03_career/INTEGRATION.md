# Component 3 runtime integration

Run from `backend/`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The exported matcher and catalogue are loaded once per application process at
startup. CPU inference and SHAP run in a worker thread. The exported inference
helper, preprocessing, deterministic ranking, and score semantics are unchanged.
No model training or O*NET downloads occur.

Optional `backend/.env` configuration:

```dotenv
CAREER_UPSTREAM_BASE_URL=http://127.0.0.1:8000
CAREER_UPSTREAM_TIMEOUT_SECONDS=10
```

The default upstream is the same running app. If its port changes, update the
upstream URL too. Separate services can use the base URL of the service exposing
both profile endpoints. Docker's default port 8000 works with the loopback URL
inside the container.

GET endpoints:

- `/api/skill/profile`: Component 1's technical profile JSON, without a wrapper.
- `/api/personality/profile`: Component 2's soft profile JSON, without a wrapper.
- `/api/career/best-job`: `candidate_id`, `onet_version`, `model_type`, `score_meaning`,
  `eligible_occupations`, `unrecognised_skills`, and `best_job` as the job name.
- `/api/career/top-jobs`: the six requested metadata fields followed by exactly five entries
  in `jobs`, each containing `ranking`, `job`, and `score` in model-ranked order.
- `/api/career/explanation`: only `candidate_id`, `onet_version`, `model_type`,
  `score_meaning`, `eligible_occupations`, and the top job's `explanation` text.

All career APIs fetch both upstream profiles for each request and apply the same
inference function with four alternatives. Identical inputs produce identical
rankings and explanations. The displayed score is a prototype skill-evidence
match score, not a hiring probability. SHAP explains the raw score; baseline plus
**all** contributions reconstructs it. Positive/negative lists contain the
exporter's top five factors of each sign and need not alone reconstruct the score.

Swagger contracts and errors are available at `/docs`. Upstream errors/invalid
profiles return 502, upstream timeouts return 504, and inference failures return
500. Missing/corrupt model artifacts fail startup rather than serving fake results.

Verification from `backend/`:

```powershell
python -m unittest discover -s tests -v
```

Tests use profile API responses and the real saved model. An HTTP mock transport
covers successful profile retrieval, invalid contracts and upstream failures.
The exported `job_matching_training_output/` files must be included when deploying
or sharing this integration; they are not generated at runtime.
