# Backend CI/CD on Railway

The workflow in `.github/workflows/backend-railway.yml` handles the backend only:

1. Backend changes on pushes and pull requests build the Python 3.11 Docker image.
2. The image runs integration tests using the exported XGBoost model and SHAP.
3. A container starts with `PORT=8090`; a live API check verifies health, profile
   APIs, internal HTTP retrieval, career results, Component 4, and OpenAPI.
4. After checks pass, pushes to the repository's default branch deploy only the
   `backend/` directory. Manual runs deploy only when the default branch is selected.
5. Hosted endpoints are checked after the deployment command finishes.

Changes limited to the frontend do not trigger this workflow. PRs and other
branches run CI without deploying. Production deployments are serialized.

## One-time Railway setup

1. Create a Railway project and an **empty service** for the backend.
2. Use the Dockerfile builder (the uploaded `Dockerfile` is auto-detected).
   Leave build/start overrides empty to use the Dockerfile's CMD.
3. Leave the service Root Directory empty or `/`. This workflow uploads
   `backend/` **as the archive root** via `--path-as-root`, so `/backend` would
   point to a folder that does not exist in that upload.
4. Set the service healthcheck path to `/health`, timeout to 180 seconds,
   and restart policy to On Failure (up to 3 retries).
5. In service Variables, leave `CAREER_UPSTREAM_BASE_URL` unset when both profile
   APIs are in this same backend. Internal requests automatically use
   `http://127.0.0.1:$PORT`. `CAREER_UPSTREAM_TIMEOUT_SECONDS=10` is optional.
   No database service or DATABASE_URL is needed for the current integration.
6. Generate a public domain under service Networking. Use the app's listening
   port (`PORT`); let Railway assign it, or explicitly set `PORT=8000` and use
   target port 8000. Copy the HTTPS base URL.
7. Create a **project token** scoped to the target Railway environment in project
   settings. The token is used through `RAILWAY_TOKEN`, not an account API token.
8. If this service also has a GitHub source, disable its automatic deployments
   or disconnect that source so deployments go through the tests in this workflow.

## One-time GitHub setup

Repository Settings > Secrets and variables > Actions:

| Type | Name | Value |
| --- | --- | --- |
| Secret | `RAILWAY_TOKEN` | Railway project token for the target environment |
| Variable | `RAILWAY_PROJECT_ID` | Railway project UUID |
| Variable | `RAILWAY_SERVICE_ID` | Backend service UUID |
| Variable | `RAILWAY_ENVIRONMENT_ID` | Target environment UUID |
| Variable | `RAILWAY_BACKEND_URL` | Generated HTTPS base URL, without `/docs` |

The pipeline deploys the repository's **default branch**, not the current local
feature branch. Merge reviewed backend changes into that branch to deploy, or
select it when running Actions > Backend CI/CD - Railway > Run workflow.
The workflow requires no repository write permissions and never commits code.

Include all backend code and exported runtime files in the commit you publish,
particularly `app/component03_career/job_matching_training_output/` with its
`inference.py`, model JSON, catalogue JSON, and runtime requirements. These files
are currently untracked in the local workspace; GitHub Actions cannot see files
that have not been included in the repository.

## Verify the hosted API

Replace `<backend-domain>` with the generated Railway domain:

- `https://<backend-domain>/health`
- `https://<backend-domain>/api/skill/profile`
- `https://<backend-domain>/api/personality/profile`
- `https://<backend-domain>/api/career/best-job`
- `https://<backend-domain>/api/career/top-jobs`
- `https://<backend-domain>/api/career/explanation`
- `https://<backend-domain>/docs`

Run the same smoke check locally:

```powershell
python backend/scripts/smoke_test.py https://<backend-domain>
```

Set the separately hosted frontend's API base URL to this HTTPS backend URL.
The pipeline does not build or deploy the frontend.

## Troubleshooting

- Missing GitHub configuration: add the secret/variables listed above.
- Missing model/catalogue at startup: ensure the exported files are committed.
- Career APIs return 502: remove a stale upstream URL pointing to localhost:8000
  when the app actually listens on a different Railway PORT.
- Healthcheck failure: check service logs, model startup, listening port and memory.
- `libgomp.so.1` error: the Dockerfile installs `libgomp1` for XGBoost CPU inference.

Sources: [Railway CLI deployment](https://docs.railway.com/cli/deploying),
[railway up](https://docs.railway.com/cli/up),
[healthchecks](https://docs.railway.com/deployments/healthchecks).
