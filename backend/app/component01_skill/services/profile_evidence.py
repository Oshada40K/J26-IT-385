"""Attach corroborating profile evidence without changing CV-derived scores."""
import re


def combine_evidence(skills, records):
    by_name = {skill['name']: skill for skill in skills}
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        skill = by_name.get(record.get('skill'))
        text = record.get('text')
        if skill is None or not isinstance(text, str) or not text.strip() or len(text) > 4000:
            continue
        normalized = re.sub(r'\s+', ' ', text).strip().casefold()
        url = record.get('url', '')
        if not isinstance(url, str) or len(url) > 2048:
            continue
        identity = (skill['name'], url.rstrip('/').casefold() or normalized)
        project = record.get('project_name', '')
        project = re.sub(r'[-_\s]+', ' ', project).strip().casefold() if isinstance(project, str) else ''
        project_identity = (skill['name'], 'project:' + project)
        same_project = project and (project_identity in seen or any(
            e.get('section') in {'projects', 'experience'} and
            re.search(r'(?<!\w)' + re.escape(project) + r'(?!\w)', re.sub(r'[-_\s]+', ' ', e['text']).casefold())
            for e in skill['evidence']))
        if same_project or identity in seen or any(re.sub(r'\s+', ' ', e['text']).strip().casefold() == normalized or (url and url.casefold().rstrip('/') in e['text'].casefold()) for e in skill['evidence']):
            continue
        seen.add(identity)
        if project:
            seen.add(project_identity)
        evidence = {'source': record.get('source', 'external'), 'section': 'external',
                    'text': text.strip(), 'match_method': record.get('match_method', 'authorized_profile')}
        if url:
            evidence['url'] = url
        skill['evidence'].append(evidence)
    return skills
