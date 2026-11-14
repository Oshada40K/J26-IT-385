# Component 3 expert-agreement study

## Why this exists

The saved matcher was trained on **synthetic policy pseudo-labels** (see
`../job_matching_training_output/evaluation.json`). Its reported R² and NDCG measure
agreement with the labelling rule, not with human judgment. This toolkit provides the
independent check: do IT lecturers, career advisers or senior students agree with the
model's top-5 careers for a given skill profile?

Everything here is offline tooling. It does not change the API, the model or the
training output.

## Protocol

1. **Collect profiles.** Use real Component 1 assessments (saved JSON from
   `/api/component01/skills/{candidate_id}/details`) or schema 1.0 profiles. Aim for
   10 to 20 varied candidates. Remove names and contact details first; the sheet only
   needs the candidate ID and skills.
2. **Export blind sheets** (from `backend/`):

   ```powershell
   python -m app.component03_career.evaluation.export_rating_sheet --technical profile1.json profile2.json --out evaluation_run
   ```

   `rating_sheet.csv` lists five occupations per candidate in **shuffled order with
   no scores**, so raters cannot be anchored by the model. `model_key.csv` holds the
   model ranks and stays with the researcher. `candidate_profiles.md` gives raters the
   skill evidence.
3. **Rate.** Give each rater a copy of `rating_sheet.csv` plus `candidate_profiles.md`.
   They fill `relevance_1_to_5` for every row:

   | Rating | Meaning |
   |---|---|
   | 5 | Excellent fit for this evidence; I would recommend it first |
   | 4 | Good fit; a sensible recommendation |
   | 3 | Plausible but not what I would suggest |
   | 2 | Weak fit |
   | 1 | Unsuitable |

   Recommended: at least 3 raters, rating independently, without discussing.
4. **Score agreement** (from `backend/`):

   ```powershell
   python -m app.component03_career.evaluation.expert_agreement --key evaluation_run/model_key.csv --ratings evaluation_run/rater_A.csv evaluation_run/rater_B.csv evaluation_run/rater_C.csv --out evaluation_run/results.json
   ```

## Reading the results

- **NDCG@5** near 1.0 means the model orders the five jobs the way the rater would.
  Compare it with **Random NDCG@5**, the expected value for a random ordering of the
  same five jobs. The model must clearly beat that baseline to claim anything.
- **P@1** and **P@3**: share of the top-1 / top-3 that raters marked relevant (4 or 5).
- **Spearman**: rank correlation between model rank and rater relevance.
- **Inter-rater Spearman**: how much the raters agree with each other. If this is low,
  the task itself is ambiguous and the model cannot be expected to score higher.

Report the per-rater table, the overall row, the baseline and the inter-rater figure.
State clearly that the personality input was Component 2's fixed sample profile unless
real personality profiles were available at export time.

## Limits

This measures agreement with expert opinion on skill-evidence suitability. It is not
employment outcome data and does not validate the 0-100 score as a probability.
