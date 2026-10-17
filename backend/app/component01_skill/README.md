# Technical skill assessment

The supplied PDF is a fictional fixture. Any PDF/DOCX follows the same parser,
extractor, versioned rubric and persistence path; no candidate names or skill
levels are hard-coded. The old `/api/skill/profile` remains a labeled legacy
fixture for existing Component 03 integration. New uploaded profiles use the
candidate-specific endpoints below. Components 02–04 are unchanged.

## Run

From `backend`, install `requirements.txt`, then run `uvicorn app.main:app --reload`.
The frontend Home page accepts a CV; **Analyze my CV** uploads it and opens the
skill assessment page. Results show estimated levels, confidence and expandable
CV evidence. Each later upload replaces the displayed result while retaining
successful assessment history. Invalid uploads leave the previous result intact.

Run the sample (or substitute any file):

```bash
PYTHONPATH=. .venv/bin/python scripts/assess_cv.py app/component01_skill/Tharindi_Jayawickrama_Sample_CV_Usernames_Only.pdf
PYTHONPATH=. .venv/bin/python -m pytest tests/component01_skill -q
```

Install `pytest` and `httpx` for the CLI/test suite.

The CLI uses the real upload/GET API in-process and writes `.data/sample-assessment.json`
and a private session credential file. Neither uploaded documents nor raw CV
text are retained; evidence excerpts, file hashes and results are stored.

## Contract and prototype identity

There is no existing application authentication or configured database in this
repository (`app/database.py` is a placeholder). This component therefore uses
an isolated SQLite database at `backend/.data/skills.sqlite3`, overridable with
`SKILL_DATABASE_PATH`, and server-generated candidate IDs/access tokens. It does
not apply a migration to the shared PostgreSQL schema.

1. `POST /api/component01/skills/session` creates a prototype candidate and bearer
   token. The frontend keeps these in tab session storage.
2. `POST /api/component01/skills/upload` accepts multipart `candidate_id`, `file`,
   optional `github_username`, `linkedin_username`, `analyze_github`.
3. `GET /api/component01/skills/{candidate_id}` returns exactly `schema_version`,
   `candidate_id`, and `technical_skills` containing normalized `name`/integer
   `level`. GET reads the latest successful stored assessment without inference.
4. `GET /api/component01/skills/{candidate_id}/details` returns evidence,
   confidence, provisional/review status, identifiers and method metadata.

Upload and both GETs require `Authorization: Bearer <access_token>`. Missing/invalid
credentials produce 401; accessing a different candidate produces 403; an owned
candidate without an assessment produces 404. Candidate ID alone grants no access.
Tokens are hashed in storage. This is isolated prototype identity, not verified
student/account authentication. Before deployment, integrate the team's account
identity, authorized service-to-service access, credential expiry and retention
policy. Restarting with the same database preserves assessments; losing the tab
session loses access unless its private credentials were retained.

## Extraction and scoring

Boundary-aware aliases normalize technologies (Java differs from JavaScript;
short aliases do not match file-extension-like parts of Node.js). PDF parsing
uses PyMuPDF's sorted text; DOCX includes paragraphs and table cells in order.
Files are limited to 10 MB, PDFs to 50 pages, text to 200,000 characters, and DOCX
expanded contents to 25 MB. Corrupt, encrypted and textless/scanned documents
receive a validation error; OCR is not performed.

Projects keep their technology stack with their action statements. Explicit
negation and learning intentions are rejected. Duplicate excerpts are removed.
Levels use `data/scoring_rubric.json`: introductory evidence 1, skill-only claim
2, attributable implementation 3, repeated complex production ownership 4.
Level 5 requires independent expert review and is never assigned automatically.
All automated levels are provisional or need review. Years, profile absence,
stars and repository counts are not scoring inputs.

## Optional semantic support

Install `requirements-semantic.txt`, cache the pretrained
`sentence-transformers/all-MiniLM-L6-v2` model separately, and set
`SKILL_ENABLE_SBERT=true` plus `SKILL_SBERT_MODEL_PATH` if using a local directory.
The full application loads `backend/.env` through its existing startup lifespan;
standalone CLI/test commands use exported process environment variables. Inference loads a shared cached model under a
lock and does not download models inside requests. Model failures fall back to
explicit extraction and are recorded in details. Semantic similarity annotates
explicitly grounded project/work evidence; it cannot invent unmentioned skills
or raise proficiency. The initial 0.65 support threshold is experimental and
must be calibrated on candidate-separated, human-annotated CVs before enabling
semantic-only expansion. Default runtime does not install the large ML stack.

## External profiles and remaining research

Clearly labeled GitHub/LinkedIn handles and profile URLs are normalized for
review, without asserting ownership. GitHub enrichment is deliberately not
performed until ownership and authorized access are established; consent requests
receive a recorded CV-only warning. LinkedIn is never scraped. Missing external
profiles do not lower the assessment.

Fourteen regression tests cover the fictional sample, unrelated skills, aliases, section evidence,
negation, malformed/scanned/encrypted input, DOCX tables, empty profiles, access
control, persistence/history and semantic fallback. This is a reproducible rubric
baseline, not measured skill accuracy: no human-labeled evaluation dataset has
been supplied. CV layout variation, multi-column reading order, implicit skills,
project attribution and nuanced negation still require human review. Research
milestone 6 (expert labels, precision/recall/F1 and ordinal agreement) remains
pending; no invented accuracy claims or expert scores are reported.

Parser/model reference APIs: [PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
and [SentenceTransformer](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).

Containers create a writable `/app/.data` directory. Mount persistent storage
there (or set `SKILL_DATABASE_PATH` to a mounted path) to preserve assessments
across redeploys. Automatic local SQLite table creation is not a reviewed
PostgreSQL migration; PostgreSQL integration remains pending team conventions.

Sample result: 23 recognized technical skills. React, Python, Selenium, Node.js,
MongoDB and PostgreSQL have project/work evidence and are estimated at level 3.
TypeScript, SQL, HTML and CSS have skill-list evidence and are provisionally
estimated at level 2. These are rubric expectations for fictional test data,
not independent expert ratings. The full expected result is stored in
`backend/tests/component01_skill/fixtures/sample_expected.json`.

Validation: Component 01 regression suite (14 tests), existing career integration
suite (3 tests and 9 subtests), frontend production build, and package dependency
checks pass. Semantic inference is tested with a controlled model stub; the real
SBERT model has not been downloaded or accuracy-validated in this environment.

### Embedded links and profile evidence

Uploads now extract PDF URI annotations via `page.get_links()` and DOCX external
hyperlink relationships across document parts, including drawings/icons and
headers/footers. Links remain separate from CV text; `parse_cv()` still returns
text only. Full and scheme-less profile URLs and clearly labeled plain usernames
are normalized to HTTPS and deduplicated by platform/handle. Unlabeled arbitrary
words are not treated as usernames. Credentials, ports, unsafe schemes, other
hosts, encoded paths, and non-profile paths are rejected before requests.

No GitHub analyzer or authorized LinkedIn workflow previously existed in this
component. The GitHub analyzer now runs automatically for detected profiles,
validates the personal account through the official API, and checks
up to 30 recently updated repositories. Forks, archived repositories, and other
owners are excluded. It uses a fixed API origin, five-second request timeouts,
no redirects, and a bounded five-minute cache. Primary-language metadata supports
existing CV skills. Additional activity analysis samples up to three repositories
and three account-authored commits per repository, plus two authored merged pull
requests (including contributions to other owners' repositories), changed files,
contributors, and peer reviews. It excludes initial/generated commits, forks,
unattributed changes, and generated/dependency files. Activity sampling is bounded
to 24 requests and a 25-second deadline with no redirects and a five-minute cache.
The existing `analyze_github` form field remains accepted for API compatibility;
it no longer gates automatic public analysis. Account existence never sets
`ownership_verified` to true; the account's connection to the CV is unverified.

To connect an authorized LinkedIn workflow, register an application-configured
callable with `services.linkedin_evidence.register_authorized_provider(provider)`.
Its signature is `(candidate_id, canonical_profile_url) -> list[dict]`. It must
enforce candidate-specific authorization. Evidence records contain `skill`,
`text`, `source`, and optional `url` / `project_name`. No LinkedIn scraping occurs.
Without a provider, detected profiles are retained with a warning and analysis
is not performed. Provider failures never block CV assessment.

External language/LinkedIn evidence is attached after the unchanged CV scoring
rubric runs, only to existing CV skills. It cannot raise levels or change confidence.
The exception is the new GitHub skill, assessed separately by `github_activity_v1`:

- Level 1: substantive account-authored documentation/workflow changes.
- Level 2: substantive account-authored source changes.
- Level 3: source changes, distinct commits on separate days, and a merged PR.
- Level 4: Level 3 plus multi-project changes, peer review, other contributors,
  test changes, and workflow automation; requires review.
- Level 5 is not inferred from this limited public sample.

Profile existence and repository counts never award a rating. Missing or
insufficient activity adds no GitHub skill. Separate accounts are assessed
individually; their activity is never pooled to increase proficiency. Skills are
unique and deterministically sorted. API errors retain only evidence already
retrieved. Ratings are provisional estimates of observed account activity, not
validated competency; template/copied work cannot always be identified.
Duplicate excerpts, repository URLs, and identifiable project names are suppressed.
Uncertain project identity is not assumed; external records never enter scoring.
Invalid, absent, or inaccessible profiles leave CV assessment available. The
upload contract, database, and shared GET JSON format remain unchanged.

Run regression tests from `backend/`:

```bash
.venv/bin/python -m pytest app/component01_skill/tests tests/component01_skill -q
```
