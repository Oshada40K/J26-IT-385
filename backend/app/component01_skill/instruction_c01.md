# Component 01 — Technical Skill Profile & Assessment

**Implementation Plan**  
**Owner:** Tharindi  
**Git branch:** `Tharindi-skill-profile`  
**Backend location:** `backend/app/component01_skill/`  
**Frontend location:** `frontend/src/pages/component01/`  
**Shared contract:** `schema_version: "1.0"`  
**Status:** Planned

## 1. Objective

Build a self-contained FastAPI component that accepts a candidate's CV (PDF/DOCX), extracts **technical** skills, estimates provisional skill levels from evidence in the CV, saves the profile, and exposes it to the other project components through a stable **GET API**.

Optional evidence enrichment: detect a candidate-supplied GitHub or LinkedIn username/URL; use **public GitHub API data** where available and consented; accept **authorized or candidate-provided LinkedIn evidence**. External profiles are **not required** for a valid CV-only assessment.

> **Important limitation:** A CV and public online profiles cannot prove a person's actual ability. Output levels are **evidence-based estimates**, not verified competency scores. Record uncertainty internally and avoid penalizing missing profiles.

## 2. Scope and non-goals

### In scope

- Accept and validate PDF/DOCX CV uploads with a candidate ID.
- Extract readable CV text and section-aware evidence from Skills, Projects, Work Experience, Education and Certifications.
- Identify explicit technical skill names/aliases and their relevant contextual evidence.
- Use pretrained SBERT for semantic matching **with validation thresholds and contextual safeguards**.
- Produce a 1–5 **provisional level per technical skill** and save supporting evidence/confidence internally.
- Persist profile and assessment metadata using the existing project database conventions.
- Provide the agreed team-facing JSON via a GET endpoint.
- Provide an internal details endpoint for evidence, confidence and review.
- Add an optional React upload/results screen inside `component01/`.
- Add optional GitHub enrichment after CV-only functionality is stable.

### Out of scope for Component 01

- Industry/occupation skill gaps; ESCO/O*NET mapping.
- Career recommendations, personality assessments, learning roadmaps.
- Mandatory LinkedIn scraping or arbitrary access to private profile data.
- Training a new SBERT model from scratch.
- Claiming the score is a validated measure of real-world skill without evaluation.

## 3. Architecture and processing flow

```text
CV upload (PDF/DOCX) + candidate_id
       |
       v
Validate file -> extract text -> detect CV sections
       |                       |
       |                       +--> GitHub/LinkedIn identifier candidates
       v
Skill taxonomy + spaCy PhraseMatcher (explicit skills)
       |
       +--> SBERT semantic evidence matching (context-aware)
       |
       v
Deduplicate/normalize skills + retain supporting evidence
       |
       +--> [Optional, consented] GitHub API evidence enrichment
       +--> [Optional] authorized LinkedIn / user-provided evidence
       |
       v
Skill-specific evidence scoring + confidence + review status
       |
       v
PostgreSQL (profile, skill assessments, evidence, version metadata)
       |
       +--> GET /api/component01/skills/{candidate_id}  (team JSON)
       +--> GET /api/component01/skills/{candidate_id}/details (internal)
```

**Implementation rule:** Keep model loading and costly inference in a shared service; do not reload SBERT on each request. Prefer asynchronous/background processing if upload latency becomes a problem.

## 4. Proposed folder structure

```text
backend/
├── app/
│   ├── main.py                          # register router once; shared file
│   ├── database.py                      # reuse existing DB setup
│   └── component01_skill/
│       ├── __init__.py
│       ├── router.py                    # API endpoints
│       ├── schemas.py                   # request/response validation
│       ├── models.py                    # DB models if project uses ORM
│       ├── repository.py                # DB queries
│       ├── config.py                    # component settings
│       ├── services/
│       │   ├── __init__.py
│       │   ├── cv_parser.py             # PDF/DOCX and CV sections
│       │   ├── profile_identifier.py    # GitHub/LinkedIn handles
│       │   ├── skill_extractor.py       # spaCy + SBERT
│       │   ├── skill_assessor.py        # evidence-based proficiency
│       │   ├── github_analyzer.py       # optional public GitHub API
│       │   ├── linkedin_evidence.py     # authorized/input evidence only
│       │   └── profile_service.py       # orchestration
│       └── data/
│           ├── technical_skills.json   # skill names, aliases, descriptions
│           └── scoring_rubric.json     # versioned score rules
├── tests/
│   └── component01_skill/
│       ├── test_cv_parser.py
│       ├── test_identifiers.py
│       ├── test_skill_extractor.py
│       ├── test_skill_assessor.py
│       ├── test_api.py
│       └── fixtures/
│           └── README.md
└── requirements.txt                    # modify only as needed

frontend/src/pages/component01/
├── SkillProfile.jsx
├── CVUpload.jsx
├── SkillResults.jsx
└── skillApi.js
```

Adapt filenames and database integration to existing team conventions. **Do not modify** `component02_personality`, `component03_career`, or `component04_roadmap`.

## 5. Shared API contract — agree on this before coding

### A. Upload and assess

`POST /api/component01/skills/upload`

- Content type: `multipart/form-data`
- Required fields: `candidate_id` (string), `file` (PDF/DOCX)
- Optional: `github_username`, `linkedin_username`, `analyze_github` (boolean consent flag)
- Validate candidate identity from the main application's authentication/authorization. **Never trust `candidate_id` alone as permission to write or read someone else's profile.**
- MVP: process synchronously and return the stored assessment ID/status. If slow, switch to `202 Accepted` and a background job with a status endpoint.

Example MVP response:

```json
{
  "candidate_id": "sample_candidate_001",
  "assessment_id": "assessment_123",
  "status": "completed"
}
```

### B. Retrieve shared skill profile

`GET /api/component01/skills/{candidate_id}`

**Response must match the team schema exactly** (no scoring/confidence metadata in this response):

```json
{
  "schema_version": "1.0",
  "candidate_id": "sample_candidate_001",
  "technical_skills": [
    { "name": "Python", "level": 3 },
    { "name": "React", "level": 3 },
    { "name": "SQL", "level": 2 }
  ]
}
```

Contract rules:

- `level`: **integer from 1 through 5**.
- `name`: normalized, unique technical skill label; deterministic sort order.
- A candidate with a completed assessment but no recognized skills gets `technical_skills: []`.
- A candidate with **no stored assessment** gets HTTP `404`.
- Protect endpoints with the project's existing authentication and authorized cross-component access.
- GET reads the latest **successful** saved assessment; it does **not** re-run SBERT or GitHub calls.
- Use `schema_version: "1.0"`; coordinate before breaking changes.

### C. Internal detailed result

`GET /api/component01/skills/{candidate_id}/details`

Example (not exposed as the shared team schema):

```json
{
  "candidate_id": "sample_candidate_001",
  "assessment_method": "cv_evidence_rubric_v1",
  "skills": [
    {
      "name": "React",
      "level": 3,
      "confidence": "medium",
      "status": "provisional",
      "evidence": [
        { "source": "cv_project", "text": "Built a React dashboard." }
      ]
    }
  ]
}
```

The frontend should label results **estimated** and show evidence and low-confidence warnings. Provide a correction/review flow when time permits.

## 6. Skill extraction design

### Phase 1: Explicit extraction (essential)

Create `technical_skills.json` with canonical names, aliases and descriptions. Example:

```json
{
  "React": {
    "aliases": ["React", "React.js", "ReactJS"],
    "description": "Building user interfaces using React"
  },
  "Python": {
    "aliases": ["Python", "Python 3"],
    "description": "Programming and automation using Python"
  },
  "PostgreSQL": {
    "aliases": ["Postgres", "PostgreSQL"],
    "description": "Relational database development using PostgreSQL"
  }
}
```

Implement case-insensitive spaCy `PhraseMatcher` and/or boundary-aware patterns. Recognize ambiguous labels in context (e.g., `Go`, `R`, `C`, `React`, `Java` vs `JavaScript`). For every match, retain section, sentence, source and character positions where practical.

### Phase 2: Semantic evidence (essential, start conservatively)

Use pretrained `sentence-transformers/all-MiniLM-L6-v2` to compare relevant CV sentences with skill descriptions. **Do not** equate cosine similarity with proficiency. Select thresholds using annotated CV samples; reject negative and speculative contexts (e.g., “I want to learn React”, “no Python experience”). Require explicit or strongly supported evidence before adding a skill.

### Phase 3: Section-aware logic

- Skills: self-reported presence, weak evidence of proficiency.
- Projects: link technology to actions and demonstrated implementation.
- Experience: link specific technology to responsibilities and scope.
- Education/certifications: foundational knowledge evidence, not proof of expertise.
- Deduplicate repeated mentions of the **same underlying work** across CV, GitHub and LinkedIn.

## 7. Proficiency scoring and uncertainty

### Initial strategy (before you have labeled data)

Use a **versioned, transparent rubric** with per-skill evidence, rather than directly training on invented level labels. Candidate experience is optional and lack of GitHub/LinkedIn data must not be treated as zero skill.

Suggested evidence dimensions for *each skill*:

| Dimension | Look for | Notes |
| --- | --- | --- |
| Declared knowledge | Named in Skills section | Confirms a claim; not mastery |
| Practical implementation | Substantial attributable project work | Verify the skill is actually used |
| Complexity / independence | Architecture, testing, deployment, debugging | Evidence must be skill-specific |
| Professional application | Responsibility, scope, impact | Years alone do not prove proficiency |
| Supporting learning | Relevant education/certifications | Usually weaker than demonstrated work |

**Proposed ordinal rubric:**

1. **Level 1 — Familiarity:** introductory/basic evidence.
2. **Level 2 — Basic:** simple practical use or a skill-only claim with no demonstrated context; **provisional**.
3. **Level 3 — Intermediate:** independently completed meaningful work using the skill.
4. **Level 4 — Advanced:** substantial complex work, ownership, production operation and/or repeated high-quality contributions.
5. **Level 5 — Expert:** strong sustained evidence of expert contributions, leadership and difficult technical decisions; very hard to justify from CV alone.

Store **separate** `confidence` (low/medium/high), `assessment_status` (provisional/assessed/needs_review) and individual evidence records. If the shared GET API requires every extracted skill to have a number, use a documented **provisional** fallback (e.g., Level 2 for a skill-only claim) and make uncertainty visible in the internal details endpoint. **Do not represent that fallback as actual ability.** Agree on this rule with the other component owners.

A 0–100 internal score is optional. If used, define dimensions, normalization, missing-data behavior and thresholds in `scoring_rubric.json`, then validate the mapping to levels using expert-annotated examples. Avoid treating arbitrary point totals as scientific measurements.

## 8. Optional GitHub enrichment (after CV-only MVP)

1. Detect supplied handles like `TharindiJay2002` or `github.com/TharindiJay2002` from clearly labeled CV fields.
2. Build and validate `https://github.com/{username}`; verify that the profile is real and belongs to the candidate before scoring.
3. After user consent, call official GitHub REST APIs for public repositories and relevant metadata. For private repositories, require appropriate authorized access.
4. Inspect selected repository languages, dependencies, README, test files, actual contributions/ownership and relevant source evidence. Limit API requests and cache results.
5. Never run untrusted repository code. Do not download excessive content or store unnecessary personal data.
6. De-emphasize forked/copied tutorials, auto-generated code, repository counts, stars and followers as evidence of proficiency.
7. If an API request fails, returns no results, or the profile is absent, the CV assessment must still complete.

**LinkedIn:** A handle like `tharindi-jayawickrama-36314a366` may be converted to a URL for user review. **Do not assume LinkedIn profile details are accessible through an API.** Use only permitted, authorized access or candidate-provided exported text. Never depend on scraping inaccessible profiles.

## 9. Persistence and data ownership

Reuse `backend/app/database.py` and team conventions. Proposed logical entities (exact migrations depend on existing models):

| Entity | Core fields |
| --- | --- |
| `skill_assessments` | id, candidate_id, status, source_cv_hash, method_version, model_version, created_at |
| `skill_assessment_items` | assessment_id, normalized_skill_name, level, confidence, assessment_status |
| `skill_evidence` | assessment_item_id, source_type, excerpt, metadata_json |
| `external_profiles` | candidate_id, platform, handle, consent_status, last_checked_at |

- Avoid storing the original CV permanently unless required; follow the main application's retention policy.
- Treat files, profile text, repository descriptions and READMEs as **untrusted input**, never as system instructions.
- Handle uploads with file size/type checks, safe parsers, controlled temporary storage and error handling.
- Persist and retrieve by the main application's candidate ID; use unique assessment IDs for history.
- Migrations must be reviewed before applying to shared databases. Never directly edit production tables without agreement.

## 10. Delivery phases and acceptance criteria

### Milestone 0 — Inspect integration points

- [ ] Review `backend/app/main.py`, `backend/app/database.py` and `backend/requirements.txt`.
- [ ] Confirm the main project candidate ID, auth, database conventions and routing style.
- [ ] Confirm `schema_version: "1.0"` and provisional fallback behavior with team members.
- [ ] Check out `Tharindi-skill-profile`; avoid unrelated component changes.

**Done when:** Router/DB integration points and JSON contract are documented.

### Milestone 1 — CV parser + technical skill extraction

- [ ] Create component structure and install only required packages.
- [ ] Validate PDF/DOCX uploads, file size, text extraction and errors.
- [ ] Add technical skill taxonomy and explicit matching.
- [ ] Add pretrained SBERT semantic evidence matching conservatively.
- [ ] Return normalized skills with source excerpts and prevent duplicate skill names.

**Done when:** Sample CVs reliably produce a list of technical skills with evidence; no skill levels are required yet.

### Milestone 2 — Provisional skill assessment

- [ ] Implement section-aware evidence features.
- [ ] Implement versioned 1–5 rubric, missing-evidence behavior and confidence.
- [ ] Add unit tests for skill-only CVs, projects, experience, negation and unmentioned skills.
- [ ] Compare a small set of predictions with independent human review.

**Done when:** Each extracted skill has a bounded provisional level, explanation/evidence and confidence; lack of GitHub is not penalized.

### Milestone 3 — Database + team API

- [ ] Add DB repository and reviewed migration.
- [ ] Implement POST upload and GET profile endpoints.
- [ ] Implement optional internal details endpoint.
- [ ] Register component router in `main.py` without changing other component paths.
- [ ] Test JSON against `SkillProfileResponse` and test authorization.

**Done when:** A stored assessment is returned via GET with exactly the team's v1.0 JSON shape.

### Milestone 4 — React integration

- [ ] Add CV upload form, errors/loading/results states.
- [ ] Show estimated 1–5 levels and evidence confidence, not definitive expertise.
- [ ] Ensure API integration uses project-wide auth/base URL conventions.

**Done when:** A candidate can upload a CV, review the results and retrieve the same persisted profile via API.

### Milestone 5 — GitHub enrichment (optional)

- [ ] Parse GitHub handle and ask consent.
- [ ] Verify candidate/profile ownership as far as practical.
- [ ] Add API client with timeouts, rate-limit handling and caching.
- [ ] Analyze meaningful attributable code evidence; deduplicate CV projects.
- [ ] Test public, private, empty, invalid and unavailable profiles.

**Done when:** GitHub improves the supporting evidence without blocking CV-only processing.

### Milestone 6 — Research evaluation and optional training

- [ ] Build a human-labeled dataset of resume sentences, detected skills and expert-rated levels.
- [ ] Split train/test data by **candidate**, not sentence, to prevent leakage.
- [ ] Evaluate skill extraction precision, recall and F1.
- [ ] Evaluate level estimation using macro-F1, MAE and/or ordinal agreement against expert labels.
- [ ] Compare CV-only vs CV+GitHub evidence on comparable candidates.
- [ ] Fine-tune SBERT or train a classifier **only if** real labeled data and baseline results justify it.
- [ ] Record dataset versions, model/rubric versions and known failure cases.

**Done when:** Assessment limitations and reproducible evaluation metrics are documented.

## 11. Test matrix

| Input / scenario | Expected behavior |
| --- | --- |
| CV contains `React`, `React.js` and `ReactJS` | One `React` entry |
| CV lists Python without any projects | Detect Python; mark level provisional/low confidence |
| CV explicitly states “no Python experience” | Do not count as positive skill evidence |
| CV describes concrete React implementation | Store evidence; level from documented rubric |
| CV has no technical skills | Successful profile with `technical_skills: []` |
| Scanned PDF with no extractable text | Clear error or OCR-needed response, no invented results |
| Corrupt or unsupported upload | 4xx validation response |
| GitHub username missing/invalid/unreachable | Continue CV-only; record enrichment unavailable |
| GitHub has forks or tutorial repositories | No automatic advanced-level award |
| LinkedIn username supplied | Validate/construct identifier; do not promise restricted API data |
| Unknown candidate GET | HTTP 404 |
| Existing candidate GET | Valid v1.0 response; no new inference triggered |
| Unauthorized user requests another candidate | Access denied |
| Same project appears in CV and GitHub | Evidence deduplicated |

## 12. Dependencies and environment

Start with the project's existing requirements and add as needed:

```text
fastapi
python-multipart
pymupdf
python-docx
spacy
sentence-transformers
scikit-learn
httpx
```

Database/ORM dependencies should match the existing backend. Pin tested versions before deployment. Pretrained model files may be downloaded on first launch; cache or package them appropriately for Railway/Docker deployment. Check server RAM, startup time and model licensing.

## 13. Deliverables

1. `backend/app/component01_skill/` implementation with services, schemas, routes and tests.
2. `frontend/src/pages/component01/` upload and results UI (if within assigned scope).
3. Reviewed DB migration/integration with existing database.
4. Documented and tested `GET /api/component01/skills/{candidate_id}` response.
5. A set of CV fixtures and expected extraction results.
6. A short accuracy/limitations report and model/rubric version note.
7. Optional GitHub enrichment and authorized LinkedIn evidence integration.

## 14. Suggested immediate next task

**Implement Milestones 0 and 1 first.** Request or inspect the existing `backend/app/main.py`, `backend/app/database.py`, and `backend/requirements.txt`; then build `cv_parser.py`, `technical_skills.json`, `skill_extractor.py`, and extraction tests inside Component 01. **No Colab training is required to begin.**
