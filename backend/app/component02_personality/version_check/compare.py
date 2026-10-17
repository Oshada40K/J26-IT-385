"""Compare two run_model.py outputs and write a Markdown report.

    python compare.py out_1_6_1.json out_1_5_2.json report.md
"""
import json
import sys
from pathlib import Path

import numpy as np

TOLERANCE = 1e-6
TRAITS = ["OPN", "CON", "EXT", "AGR", "NEU"]


def max_diff(a, b):
    return float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))))


def main(ref_path, other_path, report_path):
    ref = json.loads(Path(ref_path).read_text())
    other = json.loads(Path(other_path).read_text())
    rows = [("TF-IDF features", max_diff(ref["tfidf"], other["tfidf"])),
            ("Psycholinguistic features (scaled)", max_diff(ref["psy"], other["psy"]))]
    rows += [(f"{t} decision value", max_diff(ref["decision"][t], other["decision"][t])) for t in TRAITS]
    rows += [(f"{t} P(high)", max_diff(ref["proba"][t], other["proba"][t])) for t in TRAITS]
    same_labels = all(
        (np.asarray(ref["proba"][t]) >= 0.5).tolist() == (np.asarray(other["proba"][t]) >= 0.5).tolist()
        for t in TRAITS)
    passed = all(d <= TOLERANCE for _, d in rows) and same_labels and ref["n_features"] == other["n_features"]

    lines = [
        "# Text model: scikit-learn version check",
        "",
        f"Reference (training version): scikit-learn {ref['sklearn']}, NumPy {ref['numpy']}, Python {ref['python']}",
        f"Serving (shared backend): scikit-learn {other['sklearn']}, NumPy {other['numpy']}, Python {other['python']}",
        "",
        f"{ref['n_texts']} sample student texts, {ref['n_features']} features. Sentence-BERT inputs were fixed "
        "vectors shared by both runs (Sentence-BERT does not use scikit-learn).",
        "",
        "| Output | Max absolute difference |",
        "|---|---|",
        *[f"| {name} | {d:.2e} |" for name, d in rows],
        "",
        f"High/low label identical for every text and trait: {'yes' if same_labels else 'NO'}",
        "",
        f"Version warnings when loading under {other['sklearn']}: "
        + (", ".join(other["version_warnings_on_load"]) or "none"),
        "",
        f"**Result: {'PASS' if passed else 'FAIL'}** (tolerance {TOLERANCE:g}).",
        "",
    ]
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
