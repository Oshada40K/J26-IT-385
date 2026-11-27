"""Tests for Multi-Source Input, Independent Source Profiles, and Cross-Source Skill Comparison."""
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.component01_skill.router import router
from app.component01_skill.services.cross_source_comparator import compare_sources
from app.component01_skill.services.profile_service import process_cv


def test_cross_source_comparison_highlights_multi_single_and_claimed_gaps():
    cv_text = (
        'SUMMARY\nSoftware Developer\n'
        'SKILLS\nPython, SQL, Docker\n'
        'PROJECTS\nBuilt a Python backend service.\n'
    )
    gh_records = [
        {'skill': 'Python', 'source': 'github', 'section': 'external', 'text': 'Repo uses Python', 'url': 'https://github.com/u/r1', 'match_method': 'repository_metadata'},
        {'skill': 'TypeScript', 'source': 'github', 'section': 'external', 'text': 'Repo uses TypeScript', 'url': 'https://github.com/u/r2', 'match_method': 'repository_metadata'},
    ]
    li_text = 'SKILLS\nSQL, Project Management\nEXPERIENCE\nManaged SQL reporting workflows.\n'

    with patch('app.component01_skill.services.profile_service.parse_cv_document', return_value=(cv_text, [])), \
         patch('app.component01_skill.services.profile_service.analyze_github_profile', return_value=(gh_records, 'completed', [])), \
         patch('app.component01_skill.services.profile_service.repository.save_assessment', side_effect=lambda cid, content, details: details):
        details = process_cv(
            'cand_1', 'cv.pdf', b'pdf',
            github_username='https://github.com/example',
            linkedin_username='https://www.linkedin.com/in/example-user',
            analyze_github=True,
            linkedin_text=li_text,
        )

    comp = details['cross_source_comparison']
    assert comp['summary']['sources_available'] == {'cv': True, 'github': True, 'linkedin': True}
    assert 'Python' in comp['multi_source_skills']
    assert 'SQL' in comp['multi_source_skills']
    assert 'Docker' in comp['single_source_skills']
    assert 'Docker' in comp['claimed_without_practical_skills']
    assert 'TypeScript' in comp['single_source_skills']

    by_name = {item['name']: item for item in comp['skills']}
    assert by_name['Python']['claim_vs_practice_status'] == 'corroborated_practical'
    assert by_name['Docker']['claim_vs_practice_status'] == 'claimed_only'
    assert by_name['TypeScript']['claim_vs_practice_status'] == 'external_only'


def test_missing_external_sources_do_not_penalize_cv_proficiency():
    source_profiles = {
        'cv': {'status': 'completed', 'skills': [{'name': 'Python', 'level': 3, 'percentage': 60, 'category': 'Programming languages', 'evidence': [{'section': 'projects', 'text': 'Built Python API.'}]}]},
        'github': {'status': 'unavailable', 'skills': []},
        'linkedin': {'status': 'not_provided', 'skills': []},
    }
    comp = compare_sources(source_profiles, source_profiles['cv']['skills'])
    assert comp['summary']['sources_available'] == {'cv': True, 'github': False, 'linkedin': False}
    assert comp['skills'][0]['claim_vs_practice_status'] == 'cv_practical_only'
    assert 'never treated as proof' in comp['summary']['note'].lower()


def test_upload_endpoint_accepts_linkedin_text_and_returns_comparison(tmp_path, monkeypatch):
    monkeypatch.setenv('SKILL_DATABASE_PATH', str(tmp_path / 'cmp.sqlite3'))
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    monkeypatch.setenv('SKILL_ENABLE_ESCO_API', 'false')
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        sess = client.post('/api/component01/skills/session').json()
        headers = {'Authorization': 'Bearer ' + sess['access_token']}
        import pymupdf
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 40), 'SKILLS\nPython, PostgreSQL\nPROJECTS\nBuilt Python ETL scripts.')
            pdf_bytes = doc.tobytes()

        resp = client.post(
            '/api/component01/skills/upload',
            data={
                'candidate_id': sess['candidate_id'],
                'linkedin_username': 'https://www.linkedin.com/in/test-user',
                'linkedin_text': 'SKILLS\nPython, Tableau\n',
            },
            files={'file': ('cv.pdf', pdf_bytes)},
            headers=headers,
        )
        assert resp.status_code == 200
        details = client.get(f"/api/component01/skills/{sess['candidate_id']}/details", headers=headers).json()
        assert details['source_profiles']['linkedin']['status'] == 'completed'
        assert 'Python' in details['cross_source_comparison']['multi_source_skills']
        assert 'Tableau' in details['cross_source_comparison']['single_source_skills']
