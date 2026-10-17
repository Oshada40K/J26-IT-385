# Text model: scikit-learn version check

Reference (training version): scikit-learn 1.6.1, NumPy 2.2.6, Python 3.13.14
Serving (shared backend): scikit-learn 1.5.2, NumPy 1.26.4, Python 3.12.10

15 sample student texts, 30789 features. Sentence-BERT inputs were fixed vectors shared by both runs (Sentence-BERT does not use scikit-learn).

| Output | Max absolute difference |
|---|---|
| TF-IDF features | 0.00e+00 |
| Psycholinguistic features (scaled) | 0.00e+00 |
| OPN decision value | 0.00e+00 |
| CON decision value | 0.00e+00 |
| EXT decision value | 0.00e+00 |
| AGR decision value | 0.00e+00 |
| NEU decision value | 0.00e+00 |
| OPN P(high) | 0.00e+00 |
| CON P(high) | 1.11e-16 |
| EXT P(high) | 1.11e-16 |
| AGR P(high) | 5.55e-17 |
| NEU P(high) | 5.55e-17 |

High/low label identical for every text and trait: yes

Version warnings when loading under 1.5.2: Trying to unpickle estimator FeatureUnion, Trying to unpickle estimator LogisticRegression, Trying to unpickle estimator StandardScaler, Trying to unpickle estimator TfidfTransformer, Trying to unpickle estimator TfidfVectorizer

**Result: PASS** (tolerance 1e-06).
