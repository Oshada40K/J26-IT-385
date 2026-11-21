"""Compare the model's ranking with expert relevance ratings (the non-circular evaluation).

Run from `backend/` after raters have filled `relevance_1_to_5` in their copies of
rating_sheet.csv:

    python -m app.component03_career.evaluation.expert_agreement \
        --key evaluation_run/model_key.csv \
        --ratings evaluation_run/rater_A.csv evaluation_run/rater_B.csv \
        --out evaluation_run/results.json

Metrics per rater (averaged over candidates), then averaged over raters:

- ndcg_at_5           : how close the model's order is to the rater's ideal order
                        (1.0 = perfect agreement) using the 1-5 rating as the gain.
- precision_at_1 / 3  : share of the model's top-1 / top-3 that the rater marked
                        relevant (rating >= 4).
- spearman            : rank correlation between model rank and rater relevance.
- random_ndcg_at_5    : expected NDCG@5 of a RANDOM ordering of the same five jobs,
                        so the model's NDCG can be read against chance.
- inter_rater_spearman: mean pairwise Spearman between raters on shared items.

Only numpy is required. Items with an empty rating are skipped.
"""
import argparse
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RELEVANT = 4


def dcg(gains):
    gains = np.asarray(gains, dtype=float)
    return float(np.sum(gains / np.log2(np.arange(2, len(gains) + 2))))


def ndcg_at_k(gains_in_model_order, k=5):
    """NDCG@k of a list of gains given in the model's ranked order."""
    gains = list(gains_in_model_order)[:k]
    ideal = dcg(sorted(gains, reverse=True))
    return dcg(gains) / ideal if ideal > 0 else 0.0


def random_ndcg_at_k(gains, k=5):
    """Expected NDCG@k over all orderings of the same gains (chance baseline)."""
    gains = list(gains)[:k]
    values = [ndcg_at_k(order, k) for order in itertools.permutations(gains)]
    return float(np.mean(values)) if values else 0.0


def precision_at_k(gains_in_model_order, k, threshold=RELEVANT):
    gains = list(gains_in_model_order)[:k]
    return sum(1 for g in gains if g >= threshold) / k if gains else 0.0


def spearman(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float('nan')
    rx, ry = _average_ranks(x), _average_ranks(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def _average_ranks(values):
    order = np.argsort(values, kind='mergesort')
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def ratings_by_item(rows):
    out = {}
    for row in rows:
        value = (row.get('relevance_1_to_5') or '').strip()
        if value:
            rating = float(value)
            if not 1 <= rating <= 5:
                raise ValueError(f"{row['item_id']}: relevance must be 1-5, got {value}")
            out[row['item_id']] = rating
    return out


def evaluate_rater(key_rows, ratings):
    """Per-candidate metrics for one rater, using only items that rater scored."""
    per_candidate = defaultdict(list)
    for row in key_rows:
        if row['item_id'] in ratings:
            per_candidate[row['candidate_id']].append((int(row['model_rank']), ratings[row['item_id']]))
    metrics = defaultdict(list)
    for candidate, pairs in per_candidate.items():
        pairs.sort()
        gains = [rating for _, rating in pairs]
        model_ranks = [rank for rank, _ in pairs]
        metrics['ndcg_at_5'].append(ndcg_at_k(gains))
        metrics['random_ndcg_at_5'].append(random_ndcg_at_k(gains))
        metrics['precision_at_1'].append(precision_at_k(gains, 1))
        metrics['precision_at_3'].append(precision_at_k(gains, 3))
        metrics['spearman'].append(spearman([-r for r in model_ranks], gains))
        metrics['mean_rating_of_top1'].append(gains[0])
    summary = {name: float(np.nanmean(values)) for name, values in metrics.items()}
    summary['candidates'] = len(per_candidate)
    summary['items'] = sum(len(p) for p in per_candidate.values())
    return summary


def inter_rater(ratings_per_rater):
    scores = []
    for a, b in itertools.combinations(ratings_per_rater, 2):
        shared = sorted(set(a) & set(b))
        if len(shared) >= 3:
            scores.append(spearman([a[i] for i in shared], [b[i] for i in shared]))
    return float(np.nanmean(scores)) if scores else None


def evaluate(key_rows, rating_files):
    raters = {Path(path).stem: ratings_by_item(read_csv(path)) for path in rating_files}
    per_rater = {name: evaluate_rater(key_rows, ratings) for name, ratings in raters.items()}
    numeric = [k for k in next(iter(per_rater.values())) if k not in {'candidates', 'items'}] if per_rater else []
    overall = {k: float(np.nanmean([r[k] for r in per_rater.values()])) for k in numeric}
    return {
        'evaluation_type': 'Expert relevance agreement on blind rating sheets; independent of the training policy',
        'raters': per_rater,
        'overall': overall,
        'inter_rater_spearman': inter_rater(list(raters.values())),
        'relevant_threshold': RELEVANT,
    }


def markdown_table(report):
    rows = ['| Rater | Candidates | NDCG@5 | Random NDCG@5 | P@1 | P@3 | Spearman |', '|---|---|---|---|---|---|---|']
    for name, r in report['raters'].items():
        rows.append(f"| {name} | {r['candidates']} | {r['ndcg_at_5']:.3f} | {r['random_ndcg_at_5']:.3f} | "
                    f"{r['precision_at_1']:.2f} | {r['precision_at_3']:.2f} | {r['spearman']:.2f} |")
    o = report['overall']
    if o:
        rows.append(f"| **All** | | **{o['ndcg_at_5']:.3f}** | {o['random_ndcg_at_5']:.3f} | {o['precision_at_1']:.2f} | "
                    f"{o['precision_at_3']:.2f} | {o['spearman']:.2f} |")
    irr = report['inter_rater_spearman']
    rows.append('')
    rows.append(f"Inter-rater Spearman: {irr:.2f}" if irr is not None else 'Inter-rater agreement needs at least two raters.')
    return '\n'.join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--key', required=True, help='model_key.csv from export_rating_sheet')
    parser.add_argument('--ratings', nargs='+', required=True, help='one filled rating_sheet.csv per rater')
    parser.add_argument('--out', default=None, help='optional JSON output path')
    args = parser.parse_args(argv)
    report = evaluate(read_csv(args.key), args.ratings)
    print(markdown_table(report))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"Saved {args.out}")


if __name__ == '__main__':
    main()
