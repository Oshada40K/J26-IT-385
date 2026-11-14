"""Component 3 expert-agreement evaluation toolkit (see README.md in this folder).

The saved matcher was trained on synthetic policy pseudo-labels, so evaluation.json
in the training output only measures agreement with that policy. This package
provides the NON-circular evaluation: blind rating sheets for human experts and
the ranking metrics (NDCG@5, precision@k, Spearman) that compare the model's order
with their judgments, with a random-ranking baseline for context.
"""
