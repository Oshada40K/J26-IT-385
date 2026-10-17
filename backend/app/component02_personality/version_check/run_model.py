"""Score fixed sample answers with the saved text model and write every output to JSON.

Run this same script under two environments, then compare with compare.py:
    <python with scikit-learn 1.6.1> run_model.py out_1_6_1.json   (training version, Colab)
    <python with scikit-learn 1.5.2> run_model.py out_1_5_2.json   (shared backend version)

Sentence-BERT does not use scikit-learn, so its embeddings are replaced here by fixed
vectors that are identical in both environments (RandomState is version-stable).
This isolates the parts that scikit-learn computes: TF-IDF, scaling, logistic regression.
"""
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import sklearn

COMPONENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPONENT))  # the saved model expects a top-level package named "c2"

from c2 import TRAITS  # noqa: E402
from c2.features import SbertBlock  # noqa: E402
from c2.text_model import TextTraitModel  # noqa: E402

MODEL_PATH = COMPONENT / "text_model_output" / "text_trait_model.joblib"

ANSWERS = [
    "When my team disagrees, I usually listen to everyone first and then suggest a plan we can all accept. I think it is important that everyone feels heard before we decide.",
    "I like to finish my assignments early because last-minute deadlines make me anxious and stressed. I make a checklist and work through it every evening.",
    "In my free time I read about new technologies and enjoy trying creative projects with my friends, like building small games and drawing digital art.",
    "Honestly I get nervous when I have to present in front of people. I prepare a lot but I still worry that I will forget something or that people will judge me.",
    "I love meeting new people and I am usually the one who starts conversations in a new group. Parties and events give me energy and I hate working alone for long.",
    "When I face a difficult bug I break the problem into small parts, test each part, and search for similar issues online. I do not give up until I understand the cause.",
    "If someone criticises my work I try not to take it personally. I ask them for examples so I can understand what to improve, and then I fix it the next time.",
    "I prefer to learn something unfamiliar by watching a tutorial first and then experimenting on my own. I take notes and revisit them when I get stuck later on.",
    "Under deadline pressure I stay calm and focus on the most important tasks first. I tell my team early if something will be late so that we can adjust the plan.",
    "Sometimes I feel sad and tired and it is hard to start working. I procrastinate and then I feel guilty, which makes me even more stressed about my studies.",
    "I enjoy helping my classmates when they do not understand a lesson. I explain it in a simple way and I am patient, because everyone learns at a different speed.",
    "Requirements that are not clear annoy me. I would rather ask the lecturer or the client many questions at the start than build the wrong thing and waste time.",
    "I am curious about philosophy, music and art, and I often think about big questions. I like ideas that are new and unusual even if they are not practical.",
    "I keep my desk organised and I plan my week every Sunday. Being on time and keeping my promises is very important to me, and I dislike messy group work.",
    "i dont really like group projects. people dont do their part and i end up doing everything myself. i just want to get it done and move on to my own stuff.",
]


def fixed_vectors(chunks, dim):
    out = []
    for c in chunks:
        seed = int(hashlib.md5(c.encode("utf-8")).hexdigest()[:8], 16)
        out.append(np.random.RandomState(seed).standard_normal(dim))
    v = np.asarray(out, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def main(out_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = TextTraitModel.load(MODEL_PATH)
    version_warnings = sorted({str(w.message).split(" from version")[0]
                               for w in caught if w.category.__name__ == "InconsistentVersionWarning"})

    blocks = dict(model.features.transformer_list)
    sbert = blocks["sbert"]
    sbert.cache_dir = ""
    dim = sbert.dim_
    SbertBlock._encode_chunks = lambda self, chunks: fixed_vectors(chunks, dim)

    texts = [" ".join([ANSWERS[i], ANSWERS[(i + 1) % len(ANSWERS)]]) for i in range(len(ANSWERS))]
    tfidf = blocks["tfidf"].transform(texts)
    psy = blocks["psy"].transform(texts)
    X = model.transform(texts)
    proba = model.predict_proba(texts)
    decision = {t: model.classifiers[t].decision_function(X).tolist() for t in TRAITS}

    def dense(m):
        return (m.toarray() if sp.issparse(m) else np.asarray(m)).tolist()

    Path(out_path).write_text(json.dumps({
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "python": sys.version.split()[0],
        "version_warnings_on_load": version_warnings,
        "n_texts": len(texts),
        "n_features": int(X.shape[1]),
        "tfidf": dense(tfidf),
        "psy": dense(psy),
        "decision": decision,
        "proba": {t: proba[t].tolist() for t in TRAITS},
    }))
    print(f"sklearn {sklearn.__version__} numpy {np.__version__}: {len(texts)} texts, "
          f"{X.shape[1]} features, {len(version_warnings)} version warnings -> {out_path}")


if __name__ == "__main__":
    main(sys.argv[1])
