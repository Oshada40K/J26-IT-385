# Runtime integration
Install requirements.txt, then load once at server startup:

    import sys
    sys.path.insert(0, "job_matching_training_output")
    import inference
    inference.load_saved_matcher("job_matching_training_output")

Only inside a request handler, use the two supplied dictionaries:

    result, shap_values = inference.recommend_jobs(
        request.soft_skills_input,
        request.technical_skills_input,
        n_alternatives=4,
    )
    top_five = [result["best_job"], *result["alternative_jobs"]]
    best_job = result["best_job"]

Expose three POST APIs accepting the same JSON body:
- /api/career/top-jobs: top_five (five TOTAL including the best)
- /api/career/best-job: best_job
- /api/career/explanation: best_job["explanation"], positive_shap_factors,
  negative_shap_factors, all_shap_factors, shap_baseline, raw_model_score.

Input contract:
soft_skills_input: schema_version "1.0", candidate_id, soft_skills list.
technical_skills_input: schema_version "1.0", same candidate_id,
technical_skills list. Each list item: name and numeric level 0–5.
Both inputs are required. Unknown skills are reported and excluded.
No request must retrain the model or download O*NET.
Scores are prototype skill-evidence match scores, not hiring probabilities.
SHAP explains the raw score; displayed scores may be clipped to 0–100.
