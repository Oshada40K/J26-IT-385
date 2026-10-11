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
# Optional overrides; {candidate_id} is replaced by the career query parameter.
# CAREER_TECHNICAL_PROFILE_PATH=/api/component01/skills/{candidate_id}/details
# CAREER_SOFT_PROFILE_PATH=/your/component02/profile/{candidate_id}
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

Without `candidate_id`, the default profile endpoints remain the legacy sample
fixtures. For a live Component 1 assessment, call any career endpoint with
`?candidate_id=<candidate_id>` and `Authorization: Bearer <candidate_access_token>`.
Component 3 then fetches `/api/component01/skills/{candidate_id}/details` and
forwards the authorization header to both configured profile endpoints for that
request. Tokens are not stored on the shared HTTP client.
The Component 3 page reads Component 1's saved candidate session and sends this
query and header automatically. With no saved session, it labels the default
sample recommendations as sample data.
After the home-page CV upload completes, the frontend calls all three career
endpoints concurrently with that candidate session, then navigates to Component
3 with the results. The page displays those responses without making duplicate
requests on mount. Each endpoint has its own result/error state and can be retried;
an unavailable personality profile appears as a prediction error after the
successful CV assessment. Failed or incomplete uploads never start prediction.

Frontend workflow verification from `frontend/`:

```powershell
node --test src/pages/component03/careerApi.test.js
npm run build
```

Component 1's completed `cv_evidence_rubric_v1` JSON is accepted directly. The
adapter maps `skills` to `technical_skills` and supplies matcher schema version
`1.0`. It preserves each skill name and numeric level on the 1–5 assessment scale.
Confidence, provisional status, evidence text, external profiles and warnings
are assessment context, not additional matcher features. Confidence never
replaces, scales or upgrades a proficiency level. Original assessment metadata
remains at Component 1's details endpoint. Canonical alias validation and unknown
skill exclusion still use the saved catalogue; unknown technologies are returned
in `unrecognised_skills` by the best-job and top-jobs APIs.

Component 1's response ID must match the requested `candidate_id`. Component 2
continues to provide its existing hardcoded JSON through `/api/personality/profile`.
For a candidate request or a new-format Component 1 assessment, Component 3
accepts that endpoint's fixed profile regardless of its fixture ID and creates
an in-memory copy with Component 1's validated candidate ID so the saved matcher
can combine the inputs. Absolute endpoint URLs and trailing slashes are supported.
Every soft-skill name,
level and evidence value is preserved; Component 2 and its original payload are
unchanged. This is a prediction using live technical evidence and a fixed sample
personality profile, not a personalized personality assessment. Other soft-profile
identity mismatches still return 502, including mismatches from custom endpoints.
The attached JSON for `candidate_093495d9a2e7460785f1618c623faf50` is stored as the
regression fixture in `tests/component03_career/fixtures/`.

Example live request (the Component 1 candidate access token is required):

```http
GET /api/career/top-jobs?candidate_id=candidate_093495d9a2e7460785f1618c623faf50
Authorization: Bearer <candidate_access_token>
```

The same query and header work for `/api/career/best-job` and
`/api/career/explanation`. Requests without a candidate ID retain the existing
legacy sample behavior for frontend and deployment compatibility.

These checks establish input compatibility, not 100% real career prediction
accuracy. The exported model was trained on synthetic O*NET policy scores;
`evaluation.json` measures agreement with that policy, not real candidate outcomes.

All career APIs fetch both upstream profiles for each request and apply the same
inference function with four alternatives. Identical inputs produce identical
rankings and explanations. The displayed score is a prototype skill-evidence
match score, not a hiring probability. SHAP explains the raw score; baseline plus
**all** contributions reconstructs it. Positive/negative lists contain the
exporter's top five factors of each sign and need not alone reconstruct the score.

Swagger contracts and errors are available at `/docs`. Upstream errors/invalid
profiles return 502, upstream timeouts return 504, and inference failures return
500. A configured path needing a missing candidate ID returns 422.
Missing/corrupt model artifacts fail startup rather than serving fake results.

If the frontend reports that the backend returned a sample recommendation,
verify the backend URL shown in the message. An older Railway deployment ignores
the `candidate_id` query and returns `sample_candidate_001` even after a real CV
upload. Retrying or removing the frontend identity check does not fix that issue.
Deploy the updated backend containing the candidate-aware router, service and
profile adapter through the configured Backend CI/CD - Railway workflow on the
repository's default branch. See `backend/RAILWAY_DEPLOYMENT.md` for setup.
Then reload recommendations. Component 2's existing fixed profile remains in use.

The deployment smoke check now verifies that all three career routes advertise
`candidate_id` and reject an unknown candidate instead of returning sample results:

```powershell
python backend/scripts/smoke_test.py https://j26-it-385-production.up.railway.app
```

Run that command from the repository root after deployment.

Verification from `backend/`:

```powershell
python -m unittest discover -s tests -v
```

Tests use profile API responses and the real saved model. An HTTP mock transport
covers successful profile retrieval, invalid contracts and upstream failures.
The exported `job_matching_training_output/` files must be included when deploying
or sharing this integration; they are not generated at runtime.
