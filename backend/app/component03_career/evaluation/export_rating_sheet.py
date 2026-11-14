"""Export blind rating sheets for the expert study.

Run from `backend/`:

    python -m app.component03_career.evaluation.export_rating_sheet \
        --technical tests/component03_career/fixtures/component01_assessment.json \
        --out evaluation_run

Accepts any number of `--technical` files (Component 1 assessments or schema 1.0
profiles). `--soft` defaults to Component 2's current fixed profile. Writes:

- rating_sheet.csv  : what raters see. The five recommended jobs per candidate are
                      SHUFFLED with a fixed seed and shown WITHOUT model scores or
                      ranks, so ratings cannot be biased by the model's own order.
- model_key.csv     : model rank and score per item, kept by the researcher only.
- candidate_profiles.md : the skill evidence raters need to judge each candidate.

No model training or O*NET downloads occur; the saved matcher is loaded once.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from ..job_matching_training_output import inference
from ..profile_adapter import adapt_technical_profile

SEED = 20261114


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def recommend(soft_input, technical_input):
    soft = {**soft_input, 'candidate_id': technical_input['candidate_id']}
    result, _ = inference.recommend_jobs(soft, technical_input, n_alternatives=4)
    return result


def build_rows(results, seed=SEED):
    """Blind sheet rows and the matching key rows for a list of recommendation results."""
    rng = np.random.default_rng(seed)
    sheet, key = [], []
    for result in results:
        jobs = [result['best_job'], *result['alternative_jobs']]
        order = rng.permutation(len(jobs))
        for shown, index in enumerate(order, start=1):
            job = jobs[index]
            item_id = f"{result['candidate_id']}#{shown}"
            sheet.append({'candidate_id': result['candidate_id'], 'item_id': item_id, 'job_title': job['job_title'],
                          'onet_url': job['onet_url'], 'relevance_1_to_5': ''})
            key.append({'candidate_id': result['candidate_id'], 'item_id': item_id, 'job_title': job['job_title'],
                        'model_rank': job['rank'], 'model_score': job['match_score_0_to_100']})
    return sheet, key


def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def profile_markdown(technical_inputs):
    lines = ['# Candidate skill profiles for raters', '',
             'Levels are CV-evidence estimates on a 1-5 scale. Judge how suitable each listed occupation is '
             'for a candidate with THIS evidence, not for the candidate personally.', '']
    for technical in technical_inputs:
        lines.append(f"## {technical['candidate_id']}")
        lines.extend(f"- {skill['name']}: level {skill['level']:g}" for skill in technical['technical_skills'])
        lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--technical', nargs='+', required=True, help='Component 1 assessment or schema 1.0 profile JSON files')
    parser.add_argument('--soft', default=None, help='Soft profile JSON (default: Component 2 fixed sample)')
    parser.add_argument('--out', required=True, help='Output folder')
    args = parser.parse_args(argv)

    inference.load_saved_matcher(Path(inference.__file__).parent)
    soft_path = args.soft or Path(__file__).resolve().parents[2] / 'component02_personality' / 'soft_skills.json'
    soft_input = load_json(soft_path)
    technical_inputs = [adapt_technical_profile(load_json(path)) for path in args.technical]
    results = [recommend(soft_input, technical) for technical in technical_inputs]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sheet, key = build_rows(results)
    write_csv(out / 'rating_sheet.csv', sheet)
    write_csv(out / 'model_key.csv', key)
    (out / 'candidate_profiles.md').write_text(profile_markdown(technical_inputs), encoding='utf-8')
    print(f"Wrote {len(sheet)} items for {len(results)} candidate(s) to {out}")


if __name__ == '__main__':
    main()
