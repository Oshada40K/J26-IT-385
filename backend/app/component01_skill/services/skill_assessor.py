"""Conservative, versioned ordinal estimates; no fabricated expert levels."""
import re
from .skill_extractor import ACTION


def assess_skills(extracted):
    results = []
    for name in sorted(extracted, key=str.casefold):
        records = extracted[name]
        implemented = [e for e in records if e['section'] in {'projects', 'experience'} and ACTION.search(e['text'])]
        foundational = all(re.search(r'\b(?:basic|beginner|introductory|learning|introduction)\b', e['text'], re.I) for e in records)
        level = 1 if foundational else 2
        reason = 'Introductory evidence.' if foundational else 'Self-reported presence; insufficient implementation evidence.'
        confidence = 'low'
        if implemented:
            level = 3
            confidence = 'medium'
            reason = 'Named technology accompanies concrete implementation in project/work evidence.'
        # Advanced claims must explicitly name the skill in the ownership sentence.
        complex_records = [e for e in implemented if e['section'] == 'experience' and re.search(r'\b(?:owned|led|architected)\b', e['text'], re.I) and re.search(r'\bproduction\b', e['text'], re.I) and re.search(r'\b(?:distributed|scalable|architecture|performance|security)\b', e['text'], re.I)]
        if len(implemented) >= 2 and complex_records:
            level = 4
            reason = 'Repeated implementation and explicit production ownership with complex responsibilities; review required.'
        results.append({'name': name, 'level': level, 'confidence': confidence, 'status': 'needs_review' if level == 4 else 'provisional', 'reason': reason, 'evidence': records})
    return results
