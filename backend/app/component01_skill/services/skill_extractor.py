"""Boundary-aware explicit extraction and guarded optional semantic evidence."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
from ..config import MODEL_NAME
from .cv_parser import evidence_units

DATA = Path(__file__).parents[1] / 'data'
TAXONOMY = json.loads((DATA / 'technical_skills.json').read_text())
RUBRIC = json.loads((DATA / 'scoring_rubric.json').read_text())
MODEL_LOCK = Lock()
ACTION = re.compile(r'\b(?:built|developed|implemented|designed|created|deployed|automated|integrated|maintained|optimized|tested|wrote|managed)\b', re.I)
NEGATIVE = re.compile(r'\b(?:no|not|without|never|lack(?:ing)?|want to learn|wish to learn|plan to learn|planning to learn|interested in learning|hope to learn)\b', re.I)


@lru_cache(maxsize=1)
def semantic_model():
    # Loading is synchronized by the caller; missing dependencies/models are reported.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(os.getenv('SKILL_SBERT_MODEL_PATH', MODEL_NAME), local_files_only=True, trust_remote_code=False)


def alias_pattern(alias):
    left = r'(?<![\w.])' if alias in {'JS', 'TS'} else r'(?<![\w])'
    right = r'(?![\w+#])' if alias in {'C', 'R'} else r'(?![\w])'
    return re.compile(left + re.escape(alias) + right, re.I)


PATTERNS = {name: [(alias, alias_pattern(alias)) for alias in set(meta['aliases'])] for name, meta in TAXONOMY.items()}


def positive_context(text, position):
    # Clause-scoped rejection avoids accepting wishes/negation as experience.
    before = re.split(r'[.;!]|\bbut\b|\bhowever\b', text[:position], flags=re.I)[-1]
    return not NEGATIVE.search(before) and not re.match(r'.{0,25}\b(?:no experience|not experienced|not proficient|not familiar)\b', text[position:], re.I)


def extract_skills(text):
    skills = {}
    units = evidence_units(text)
    for unit in units:
        for name, patterns in PATTERNS.items():
            matches = [m for alias, pattern in patterns for m in pattern.finditer(unit['text'])]
            matches = [m for m in matches if positive_context(unit['text'], m.start())]
            if not matches:
                continue
            # Short/ambiguous words require programming context or a skills declaration.
            if name in {'Go', 'R', 'C', 'React'} and unit['section'] != 'skills':
                if name != 'React' and not re.search(r'\b(?:programming|language|code|compiler|backend|statistical|analysis|developed|built)\b', unit['text'], re.I):
                    continue
                if name == 'React' and re.search(r'\breact\s+(?:to|with|quickly|calmly)\b', unit['text'], re.I):
                    continue
            evidence = {'source': 'cv_' + unit['section'], 'section': unit['section'], 'text': unit['text'], 'unit_start': unit['start'], 'match_start': min(m.start() for m in matches), 'match_method': 'explicit'}
            records = skills.setdefault(name, [])
            if not any(e['text'].casefold() == evidence['text'].casefold() for e in records):
                records.append(evidence)
    warnings = []
    model_version = 'explicit_boundary_v1'
    if os.getenv('SKILL_ENABLE_SBERT', 'false').lower() == 'true':
        try:
            with MODEL_LOCK:
                model = semantic_model()
                # Only support explicitly grounded skills; similarity never determines level.
                for name, records in skills.items():
                    contextual = [e for e in records if e['section'] in {'projects', 'experience'} and ACTION.search(e['text'])]
                    if not contextual:
                        continue
                    vectors = model.encode([TAXONOMY[name]['description']] + [e['text'] for e in contextual], normalize_embeddings=True)
                    for index, record in enumerate(contextual, 1):
                        score = float(vectors[0] @ vectors[index])
                        record['semantic_similarity'] = round(score, 4)
                        record['semantic_supported'] = score >= RUBRIC['semantic_threshold']
                model_version = MODEL_NAME
                warnings.append('Semantic threshold is experimental and requires annotated CV calibration.')
        except Exception:
            warnings.append('SBERT unavailable locally; explicit CV evidence was used.')
    else:
        warnings.append('Semantic matching is disabled; explicit CV evidence was used.')
    return skills, model_version, warnings
