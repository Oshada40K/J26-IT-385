# Component 04 – Learning Roadmap & Skill Gap Analyzer

Owner: Dewmi. Frontend: `frontend/src/pages/component04/`. Route: `/component04`.

## Flow

1. **C1** extracts skills and evidence levels (0–5) from the student's CV.
2. **C3** recommends careers. **The target career is decided by the system on the server from C3's recommendation for the signed-in student** (see [Target career from Component 03](#target-career-from-component-03)); the student sees it read-only with C3's top five and cannot choose another career.
3. **C4 assessment form** collects confidence ratings for 10–15 career skills, learning methods, weekly hours, projects, certifications and internships.
4. **C4 analysis** (`GET /api/roadmap/analysis/{assessment_id}`) is recomputed on every request from the **latest** C1 CV assessment and the stored form, so the roadmap changes when the CV is re-uploaded or the assessment is updated.
5. **C4 learning coach** (`/api/roadmap/learning/...`) teaches the roadmap skills: placement per skill (with a diagnostic when evidence lets the student skip basics or a skill is only claimed), adapted lessons, quizzes, feedback and an adaptive decision. Mastered stages feed back into step 4 as capped C4 evidence, so the roadmap and readiness regenerate.

## Files

| File | Purpose |
|---|---|
| `c4_engine.py` | Engine shared with the training notebook. Feature code unchanged; severity, status/message and verify steps added. |
| `analysis.py` | Student-facing analysis built on the engine and trained models (the five features below). |
| `c3_link.py` | Read-only link to Component 03: calls C03's public `service.recommend` for the signed-in candidate and stores a `c3_snapshot`. |
| `service.py` | Skill selection for the form, C1 integration (read-only), saving assessments. |
| `repository.py` | Component-local SQLite store (`backend/.data/component04.sqlite3`, override with `C4_DATABASE_PATH`). |
| `router.py` | API under `/api/roadmap`. |
| `tutor.py` | Adaptive tutor rules (pure functions): placement, topic states, next activity, grading, decisions, lesson composition. |
| `learning.py` | Tutor service: ownership checks, plan, activities, attempts, roadmap regeneration and history. |
| `curriculum/` | Curated lessons for 9 skills (SK001 Programming Fundamentals, SK002 Python, SK008 OOP, SK009 DSA, SK010 SQL, SK014 Git, SK017 HTML and CSS, SK004 JavaScript, SK003 Java): 43 topics, 215 questions, 129 exercises, validated at load. |
| `lesson_provider.py` | Optional AI lesson generation (server-side key only); output must pass the same validation. |
| `trained_models/` | `A_gap.joblib`, `A_severity.joblib`, `C_readiness.joblib`, `D_forecast.joblib`, `c4_config.json`. |
| `inputs/` | O*NET requirements, skills catalogue, prerequisites, learning resources. |

## Target career from Component 03

The target career is **not** chosen by the student. On every career-dependent request the server calls Component 03 for the signed-in CV candidate and applies one rule. The learning path for that career still adapts to the student (CV level, quick checks, quiz results, learning style); that logic is unchanged.

- **How C03 is called.** `c3_link._call_c03` awaits C03's public `app.component03_career.service.recommend(request, candidate_id)` (read-only; C03 is not changed). `candidate_id` is always the owner of the Bearer token (`router._candidate`), and C03 forwards the same token to C01 `/api/component01/skills/{candidate_id}/details`. C04 refuses before calling C03 when there is no token (401) or no completed C01 CV assessment (409), so C03's sample-data path (`candidate_id=None`) is never used. The whole call is limited to `C3_TIMEOUT_SECONDS = 30` (C03's own upstream fetches time out after 10 s). The C04 handlers are `async` and await C03 on the event loop, so C03's loopback HTTP calls work with a single uvicorn worker.
- **Rule** (`c4_engine.C3_CAREER_RULE`, one pure function `select_career_from_c3`, also used by `student_from_json`):
  - `top5_supported` (default): the highest-ranked C3 job whose O*NET code C4 supports. If C3's #1 is outside C4, the next supported job is used and the fallback is recorded.
  - `strict_top1`: only C3's #1; if C4 does not support it there is no roadmap.
  Jobs are matched by `onet_soc_code`, then `onet_code`, then the normalised title (the training notebook's `c3_json` has titles only and gives the same result as before).
- **Errors** (clear messages, never a fallback to a manual choice): 401 not signed in, 409 no CV assessment yet, 422 no supported career under the rule, 503 C03 unavailable, 504 C03 timed out. A `career_id`/`career_name` in a request body that differs from C03's career is rejected with 409, never silently switched; an unknown one is 404.
- **Snapshot.** Each new assessment stores `career_source = "c3"` and `c3_snapshot` (column `c3_snapshot_json`): `onet_version, model_type, retrieved_at, rule, jobs` (all five: `rank, onet_soc_code, job_title, score`), `selected_rank, selected_career_id, top1_supported, fallback_used, fallback_reason`. The analysis converts it to the engine's `c3_json` shape only when calling `student_from_json`, so C3's warnings (e.g. C3's #1 is outside C4) reach the results, plus the new fields `career_source` and `c3_recommendation`. The analysis uses the stored snapshot and never calls C03, so a roadmap does not change on its own.
- **Legacy assessments** (saved before this change) have no snapshot and are reported as `career_source = "student_selected_legacy"`. They still load and analyse; they are never rewritten. The UI asks the student to generate a roadmap for their recommended career.
- **Endpoints:** `GET /api/roadmap/assessment/recommended-career` (the selected career, its C3 rank and score, C3's #1, the five jobs with `supported`/`selected`, fallback and rule) and `GET /api/roadmap/assessment/{id}/career-check` (`{changed, legacy, saved, current, message}`; read-only, so the UI can offer to regenerate after a new CV).

**Limits of the C3 link.** C3 ranks 889 O*NET 30.0 occupations and C4 covers 32 IT careers; 27 overlap by code (identical titles). C3 can recommend careers C4 cannot build (anything outside those 27). Five C4 careers can never be recommended by C3 because they are not in C3's catalogue: 15-1255.00 Web and Digital Interface Designers, 15-1299.04 Penetration Testers, 15-1299.06 Digital Forensics Analysts, 15-1299.07 Blockchain Engineers, 15-2051.00 Data Scientists. C3's soft-skill input is Component 02's fixed sample profile (`/api/personality/profile`), so C3's ranking (and therefore the C4 career) reflects the student's CV only. C3's scores are prototype match scores, not suitability probabilities. C3 calls the backend over HTTP at `CAREER_UPSTREAM_BASE_URL` (default `http://127.0.0.1:$PORT`, port 8000), which must point at the running server.

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

**3. Level-matched resources.** `learning_resources.csv` (roadmap.sh and the Coursera Kaggle dataset). Resources **below the student's entry stage are excluded** (an Intermediate student never gets Beginner resources). The rest are ranked in this order: verify types first for claimed skills (project, certification) → entry stage, then the next stage up → the student's learning methods → learner-profile type order → free → rating (4.0 if missing); at most two of one type, three in total. If nothing exists at or above the entry stage, no lower-level resource is returned; the step gets `resource_note` = "No <level> resource in the dataset for <skill>; use the practical project" (only 18 of 85 skills have Advanced resources).

**4. Adaptive roadmap.** `make_roadmap` (unchanged) chooses the skills (gap/review skills and missing prerequisites with proficiency < 0.5), their prerequisite order and hours = max(4, distance × 40/60/80 by the skill's catalogue level), or 10 h to verify a claimed skill. `C4Analyzer._roadmap` then places each step for **this student** (see 6) and groups the steps by entry stage, Beginner → Intermediate → Advanced, keeping `make_roadmap`'s order inside each group. A prerequisite is pulled forward into the earliest group of the skills that build on it, so prerequisites always come first (`placement_reason` says so). Steps are renumbered and weeks are recomputed from the student's weekly hours. Each step has level-matched activities (`STAGE_ACTIVITIES[entry_stage]`; the verify and review paths keep their own activities), a practical project, resources and measurable milestones (target C1 level, project, confidence ≥ 4).

**5. Readiness score.** `score = intercept + Σ coefficient × value` from the trained linear model (`C_readiness`), limited to 0–100 and shown term by term. Academic year is not collected, so its training mean is used.

**6. Adaptive learner model** (`analysis.py`; `c4_engine.py` is unchanged).

*Per-skill placement* (`C4Analyzer.entry_level`) uses the student's own evidence only: `E = round(current_proficiency × 5)`, where proficiency is the CV level or usable proof, as in 1.

| Evidence level E | Entry stage | Required level → target level `ceil((required − 0.05) × 5)` | Target stage |
|---|---|---|---|
| 0–1 | Beginner | ≤ 2 | Beginner |
| 2–3 | Intermediate | 3 | Intermediate |
| 4–5 | Advanced | ≥ 4 | Advanced |

If the target stage is below the entry stage, the entry stage is used. Stages below the entry stage are listed in `skipped_stages`. **Self-ratings are never read for placement**, so a 5/5 rating with CV level 0 still starts at Beginner; claimed (unverified) skills keep the "verify claimed skill" path. If E ≥ 2 and the self-rating is ≤ 2, a short refresher activity is added first (`refresher: true`); hours are unchanged.

New step fields: `entry_stage`, `target_stage`, `skipped_stages`, `placement_reason` (plain English, for example "You start at Intermediate because your CV shows level 3/5. Beginner lessons are skipped. Your target is Advanced (level 4/5)."), `skill_level` (catalogue level), `refresher`, `project_level` and `resource_note`. The existing `stage` field is now the roadmap group the step is shown in (its entry stage, or an earlier one if a prerequisite was pulled forward).

*Learner profile* (`C4Analyzer.learner_profile`, returned as `learner_profile` in the analysis and in `roadmap`). Points (maximum 7):

| Input | Points |
|---|---|
| `weighted_proficiency_ratio` (importance-weighted CV proficiency) | ≥ 0.6 → 2, ≥ 0.3 → 1, else 0 |
| `coverage_ratio` (required skills within 90% of the needed level) | ≥ 0.5 → 1 |
| `num_projects` | ≥ 3 → 2, 1–2 → 1 |
| `num_internships` | ≥ 1 → 1 |
| `num_certifications` | ≥ 1 → 1 |

Level: **Novice** 0–2, **Developing** 3–4, **Experienced** 5–7. `reasons` lists each input with its points. The profile is used for three things:
- (a) Resource-type order after the student's own learning methods: Novice course → video → documentation → project → certification; Developing course → project → video → documentation → certification; Experienced project → documentation → certification → course → video.
- (b) Project difficulty, set from the entry stage: Beginner = guided exercise, Intermediate = small end-to-end project, Advanced = realistic capstone. Experienced learners get one stage harder, never above the target stage. Novice learners get an extra "work in small steps, ask for review" line.
- (c) A `pace_note`.

It never changes a skill's entry stage.

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

## Adaptive learning coach

**Endpoints** (new; no existing endpoint or field was renamed). All need the C1 Bearer token and return 403 for another student's assessment.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/roadmap/learning/{assessment_id}` | Plan: per-skill placement, topic states, progress, next activity, events, rules |
| GET | `/api/roadmap/learning/{assessment_id}/activity?skill_id=&kind=lesson\|diagnostic&topic_id=&mode=&scope=` | Lesson adapted to the learner, or diagnostic questions (never with answers) |
| POST | `/api/roadmap/learning/{assessment_id}/attempts` | `{skill_id, kind: quiz\|diagnostic\|practical, topic_id, scope, answers}` → graded feedback, decision, roadmap update, new plan and analysis |
| POST | `/api/roadmap/learning/{assessment_id}/exercises/check` | `{skill_id, topic_id, exercise_id, answer, reveal}` → practice exercise checked on the server: "Correct!" with explanation and answer, or "Not quite" only; `reveal: true` shows the answer. Practice only |
| GET | `/api/roadmap/learning/{assessment_id}/history` | Saved attempts (quizzes, diagnostics, self-checks), practice exercise attempts with a summary, and roadmap-change events |
| POST | `/api/roadmap/learning/{assessment_id}/generate/{skill_id}` | Optional AI lessons for a skill without curated lessons (503 when not configured) |

**Decision rules** (`tutor.DEFAULT_RULES`, override with the `C4_TUTOR_RULES` JSON environment variable). These are starting settings, not validated values.

| Situation | Decision |
|---|---|
| Evidence places the student above Beginner | Checkpoint diagnostic on the skipped topics first; pass (≥ 80 %) → continue at that stage; fail → start from the weakest stage |
| Skill rated 4–5/5 with CV level 0–1 ("claimed") | Claim-check diagnostic before teaching (confidence is never proof) |
| Quiz ≥ 80 % | Topic mastered → advance |
| Quiz 50–79 % | Targeted practice: lesson re-opens in *focused* mode with the missed ideas first |
| Quiz < 50 % | Re-teach in *foundation* (step-by-step) mode |
| Same idea missed in 2 attempts | Repeated mistake → foundation mode |
| 2 low attempts on a topic with a prerequisite | Go back: prerequisite marked *needs revision* |
| "I know this – test me" passed | Topic skipped as mastered |
| All topics of a stage mastered | Demonstrated level (Beginner 2, Intermediate 3, Advanced 4) capped at 3/5 → merged as provisional evidence "C4 lessons and quizzes" only when higher than the CV/proof level → roadmap and readiness regenerate (existing analysis, weights unchanged) |

**Lesson layout** (lecture-notes style): what you will learn, main idea, explain from zero (everyday analogy and steps), real-life career example, how it works, curated video, visual, worked example, practice: interactive exercises, key ideas, memory trick, interview and job hack, common mistakes, practice and practical task, mini summary, memory test (answers revealed on click, not graded), practice questions Q1-Q3 (graded), what comes next. The extra parts live in `curriculum/enrichment.py`. Curated lessons embed one short YouTube video chosen by the lesson author (privacy-enhanced `youtube-nocookie.com` player, with an "Open on YouTube" link); AI-generated lessons never show one. Each video link was verified with YouTube oEmbed (HTTP 200), its title and channel were copied exactly from that response, and `checked_on` records the date. `validate_enrichment` checks the ID format and the required text when the bank loads. oEmbed confirms only the link, title and channel, not the content, so the author must watch each video. Each lesson lists how it was *arranged for* the student: lesson version (profile and last result), video first (prefers video tutorials: the curated video moves right after "What you will learn", or, for a topic without one, a dataset video at that level is added there), further reading (prefers reading), interactive practice first (prefers interactive coding exercises: the exercises move right after "How it works", note "Interactive practice first: you prefer interactive coding exercises."), practical task first (prefers hands-on projects only), career examples.

**Interactive exercises** (`EXERCISES` in `curriculum/enrichment.py`): 3 per curated topic (129), in four types: *predict_output* (choose what the code prints), *fill_blank* (complete one line; a short list of accepted answers compared after normalising spaces, quote style and a trailing `;`, case-insensitive only for SQL keywords), *find_bug* (choose the wrong line) and *order_steps* (arrange shuffled lines with up/down buttons). Code is in the topic's language (Python, SQL, Git commands, HTML, CSS, JavaScript, Java). `validate_enrichment` checks every exercise when the bank loads. Answers, explanations and fixed lines are never sent with the lesson; `POST .../exercises/check` grades on the server. A wrong answer shows only "Not quite" (with "Show hint" and "Try again"); the explanation and correct answer appear after a correct answer or "Show answer". Each check is stored in `c4_learning_attempts` with `kind = 'exercise'`, the attempt number for that exercise, whether the answer was revealed (before) and `solved_without_reveal`; `/history` returns them separately from quiz attempts with a summary (tried, checks, solved, solved without reveal, revealed). The exercises were drafted with an AI coding assistant for the author to review. The tests run every Python, SQL, JavaScript and Java exercise (101): the marked output must equal the real output, every accepted blank must produce the expected output, the fixed line must repair the program while the original does not, and no other line order may give the expected output. Python runs in a separate interpreter; SQL runs on an in-memory sqlite3 database built from the exercise's setup script. JavaScript runs with `node` (one process per program, CommonJS script; a setup starting with `// file: name.mjs` is an ES module imported by `main.mjs`), and Java with `java`: `tests/component04_roadmap/JavaExerciseRunner.java` compiles every program of a check in memory in one JVM, and snippets run inside `Main.main`. Without node or java those checks are skipped with "not verified: node/java not installed". The 13 Git and plain-text exercises and the 15 HTML/CSS exercises are checked by structure only in the tests. The HTML/CSS ones were also checked once in headless Chromium (Playwright): computed sizes and colours, landmarks, label links, form validation and media queries. html-b1-e3 (page skeleton order) cannot be checked by rendering. A CSS exercise's `setup` is the HTML it styles.

**Learning method mapping:** `interactive_exercises` maps to the `course` resource type only (it used to map to `project` and `course`, which made the tutor treat it as hands-on). The dataset has no interactive type, and its interactive lessons are typed `course`. For students who chose only interactive exercises, projects therefore no longer get the "your learning method" boost in resource ranking; they can still appear through the verify path and the learner-profile order. `service.RESOURCE_TYPE` (the `preferred_resource_type` stored with each submitted form and used only by the older `c4_engine.pick_resources` path, shared with the training notebook) is unchanged and still maps `interactive_exercises` to `project`.

Opening a lesson, practical self-checks and interactive exercises are recorded but never count as evidence. The learner profile and learning methods choose the lesson mode and order (project-first learners see the practical task first); the career chooses the worked examples (data vs software).

**Tables** (created automatically in the C4 database): `c4_topic_progress`, `c4_skill_learning`, `c4_learning_attempts`, `c4_learning_events`, `c4_generated_curricula`.

**Optional AI lessons:** set `C4_LLM_API_KEY` (or `ANTHROPIC_API_KEY`) and optionally `C4_LLM_MODEL` on the backend only, never in the frontend or Git. Without a key, skills without curated lessons are shown as *Self-study* and nothing is generated. Generated lessons must pass `curriculum.validate_skill` and are labelled "AI-generated".

## Data provenance and limitations

- The trained models were trained on **synthetic** data (800 simulated students, `c4_config.json`). No real-student validation or accuracy figures exist in this repository, and none are claimed.
- `job_postings_monthly.csv` is labelled **synthetic**, so the demand-trend signal (and `D_forecast`) is not shown to students; real O*NET flags are used instead.
- ESCO URIs are empty in the datasets, so ESCO is not used.
- The readiness score summarises evidence for one career; it is not an employment probability.
- The career comes from Component 03 (see [Target career from Component 03](#target-career-from-component-03) for its limits): careers outside C4's 32, C4 careers C3 cannot recommend, and C3's fixed Component 02 sample input.
- C1 skills not in the 85-skill C4 catalogue are listed in the results and ignored.
- Tutor thresholds are design settings, not validated with real students. Short answers are graded by keywords, not by a person. Curated lessons cover 9 skills (HTML and CSS, JavaScript and Java added as batch 1 of the "Lessons coming soon" skills; Linux, Networking and Cloud are planned as batch 2); others are self-study unless AI lessons are configured. Lesson quizzes are C4's own checks, so they never raise a skill above 3/5; Component 01 (an updated CV) is still needed for verified levels.
- Interactive exercises are practice only: they never change mastery, placement, evidence, the roadmap or readiness, and the exercise endpoint does not check lesson locks. fill_blank accepts only the listed answers after normalisation, so a different but correct line is marked "Not quite". The 13 Git / plain-text exercises and the 15 HTML/CSS exercises are checked by structure only in the tests, not by running them. The HTML/CSS Chromium check was a one-off and is not repeated in CI. The JavaScript and Java checks need node and java installed and are skipped (reported as not verified) without them. JavaScript runs in Node.js, not a browser, so the DOM exercises use Node's built-in EventTarget/Event instead of real page elements. The exercises were drafted with an AI coding assistant and have not been validated with students.

## Model compatibility

The models were saved with scikit-learn 1.6.1 / NumPy 2.x; the backend pins scikit-learn 1.5.2 / NumPy 1.26.4 (Component 03). `analysis._numpy2_pickle_compat` lets NumPy 1.26 rebuild the pickled training RNG state while loading only. Gap and severity predictions were compared with a scikit-learn 1.6.1 / NumPy 2.2 environment on 5,929 feature rows: maximum probability difference 4.4e-16, no class differences.

`*.joblib` is git-ignored at the repository root, so the models are not in Git, CI or Railway. Without them the form still works and the analysis endpoint returns 503 with an explanation; model tests are skipped.

## Tests

```bash
cd backend
.venv\Scripts\python -m unittest tests.component04_roadmap.test_c4 -v   # C4 only
.venv\Scripts\python -m unittest tests.component04_roadmap.test_tutor tests.component04_roadmap.test_learning_api -v   # learning coach
.venv\Scripts\python -m unittest tests.component04_roadmap.test_c3_link -v   # career from Component 03 (stub C03, never the real model)
.venv\Scripts\python -m unittest discover -s tests                   # whole backend (as in CI)
```

The GitHub API is mocked in the tests; no network calls are made.
