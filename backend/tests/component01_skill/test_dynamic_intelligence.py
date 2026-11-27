"""Tests for dynamic ESCO + O*NET skill intelligence across non-IT & emerging careers."""
from unittest.mock import patch
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.component01_skill.repository import connection, ensure_taxonomy_bootstrapped
from app.component01_skill.router import router
from app.component01_skill.services.domain_detector import detect_domain
from app.component01_skill.services.esco_client import sync_esco_occupation
from app.component01_skill.services.profile_service import process_cv
from app.component01_skill.services.semantic_matcher import SemanticMatcher
from app.component01_skill.services.skill_assessor import assess_skills
from app.component01_skill.services.skill_extractor import extract_skills
from app.component01_skill.taxonomy_repository import search_occupations, search_skills, taxonomy_stats


NON_IT_CVS = {
    'Finance': (
        'SUMMARY\nFinancial Analyst specializing in budgeting, forecasting, and corporate reporting.\n'
        'SKILLS\nIntuit QuickBooks, Microsoft Excel, SAP software, GAAP Compliance, Financial Modeling\n'
        'EXPERIENCE\nFinancial Analyst at Horizon Capital\n'
        'Prepared financial models and audited quarterly variance reports using Microsoft Excel and Intuit QuickBooks.\n',
        {'Finance & Accounting', 'Finance & Business Operations'},
        {'Intuit QuickBooks', 'Microsoft Excel', 'Financial Modeling'},
    ),
    'Healthcare': (
        'SUMMARY\nRegistered Nurse delivering acute patient care and clinical documentation.\n'
        'SKILLS\nPatient Triage, Electronic Health Records, BLS Certification, EpicCare, Medication Administration\n'
        'EXPERIENCE\nRegistered Nurse at City General Hospital\n'
        'Managed patient triage and administered medication plans using EpicCare clinical workflows.\n',
        {'Healthcare', 'Healthcare Support'},
        {'Patient Triage', 'BLS Certification'},
    ),
    'Education': (
        'SUMMARY\nSecondary School Teacher experienced in curriculum design and classroom instruction.\n'
        'SKILLS\nCurriculum Development, Lesson Planning, Moodle, Student Assessment, Classroom Management\n'
        'EXPERIENCE\nSecondary School Teacher at Oakridge Academy\n'
        'Designed digital coursework and conducted student assessments using Moodle.\n',
        {'Education & Training'},
        {'Curriculum Development', 'Lesson Planning', 'Moodle'},
    ),
    'Engineering': (
        'SUMMARY\nCivil Engineer experienced in structural design and CAD modeling.\n'
        'SKILLS\nAutodesk AutoCAD, MATLAB, Structural Analysis, Project Scheduling, Microsoft Project\n'
        'EXPERIENCE\nCivil Engineer at Apex Infrastructure\n'
        'Designed structural blueprints and analyzed load models using Autodesk AutoCAD and MATLAB.\n',
        {'Engineering & Architecture'},
        {'Autodesk AutoCAD', 'MATLAB'},
    ),
    'Marketing': (
        'SUMMARY\nMarketing Manager leading digital campaigns, CRM analytics, and brand growth.\n'
        'SKILLS\nGoogle Analytics, HubSpot, Salesforce, SEO Strategy, Campaign Management\n'
        'EXPERIENCE\nMarketing Manager at BrightWave Media\n'
        'Implemented multi-channel campaigns and analyzed conversion funnels using Google Analytics and HubSpot.\n',
        {'Marketing & Sales', 'Business & Management'},
        {'Google Analytics', 'HubSpot', 'SEO Strategy'},
    ),
}


@pytest.mark.parametrize('label,cv_data', list(NON_IT_CVS.items()))
def test_non_it_professional_cvs_are_analyzed_accurately(label, cv_data):
    cv_text, expected_fields, expected_skills = cv_data
    extracted, _, _ = extract_skills(cv_text)
    assert expected_skills <= set(extracted)
    detected = detect_domain(cv_text, extracted)
    assert detected['status'] == 'detected'
    assert detected['primary_domain'] in expected_fields or detected['career_field'] in expected_fields
    assert detected['related_occupations']
    assessed = assess_skills(extracted, detected_domain=detected)
    for skill in assessed:
        assert 1 <= skill['level'] <= 5
        assert 10 <= skill['percentage'] <= 100
        assert skill['category']
        assert skill['xai']['why_identified']
        assert skill['xai']['score_factors']


def test_onet_db_bootstrap_and_multi_occupation_relationships():
    with connection() as db:
        ensure_taxonomy_bootstrapped(db)
        stats = taxonomy_stats(db)
        assert stats['occupations'] >= 880
        assert stats['skills'] >= 8000
        assert stats['occupation_skill_links'] >= 30000
        # Same skill belongs to multiple distinct occupations (e.g. Microsoft Excel across Finance, Management, Healthcare, etc.).
        excel = search_skills(db, query='Microsoft Excel', limit=5)
        assert excel
        assert len(excel[0]['occupations']) >= 3


def test_newly_discovered_skills_are_preserved_in_db_and_assessment():
    cv_text = (
        'SUMMARY\nSpecialist in emerging spatial-computing analytics.\n'
        'SKILLS\nQuantum Ledger Auditing, HoloFlow Studio\n'
        'PROJECTS\nBuilt an enterprise reporting workflow using HoloFlow Studio.\n'
    )
    extracted, _, _ = extract_skills(cv_text)
    assert 'Quantum Ledger Auditing' in extracted
    assert 'HoloFlow Studio' in extracted
    assert extracted['HoloFlow Studio'][0]['is_discovered'] is True

    assessed = {s['name']: s for s in assess_skills(extracted)}
    assert assessed['HoloFlow Studio']['is_discovered'] is True
    assert assessed['HoloFlow Studio']['level'] == 3
    assert assessed['HoloFlow Studio']['percentage'] >= 50
    assert 'newly discovered' in assessed['HoloFlow Studio']['xai']['why_identified'].lower()

    with connection() as db:
        found = search_skills(db, query='HoloFlow Studio', source='discovered')
        assert len(found) == 1
        assert found[0]['is_discovered'] is True


def test_unknown_occupation_does_not_drop_skills():
    cv_text = (
        'SUMMARY\nBio-Acoustic Ecology Coordinator\n'
        'SKILLS\nAcoustic Spectrogram Tagging, Field Hydrophone Calibration\n'
    )
    extracted, _, _ = extract_skills(cv_text)
    detected = detect_domain(cv_text, extracted)
    assert detected['is_unknown_occupation'] is True
    assert detected['status'] == 'unknown_occupation'
    assessed = assess_skills(extracted, detected_domain=detected)
    assert len(assessed) == 2
    assert all(s['relevant_to_domain'] is True for s in assessed)


def test_semantic_cosine_matcher_matches_similar_phrase():
    items = [
        {'canonical_name': 'Financial Modeling', 'description': 'Building corporate financial forecasts and valuation models'},
        {'canonical_name': 'Kubernetes', 'description': 'Orchestrating containerized cloud workloads'},
    ]
    matcher = SemanticMatcher(items)
    hit, score, backend = matcher.match_phrase('Financial Model', threshold=0.6)
    assert backend == 'tfidf_cosine_fallback'
    assert hit is not None and hit['canonical_name'] == 'Financial Modeling'
    assert score >= 0.6


def test_esco_api_dynamic_sync_and_skill_lookup(monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_ESCO_API', 'true')
    occ_uri = 'http://data.europa.eu/esco/occupation/11111111-1111-1111-1111-111111111111'
    skill_uri = 'http://data.europa.eu/esco/skill/22222222-2222-2222-2222-222222222222'

    def handler(req):
        if '/api/search' in str(req.url) and 'type=occupation' in str(req.url):
            return httpx.Response(200, json={'_embedded': {'results': [{'uri': occ_uri, 'title': 'clinical pharmacist', 'code': '2262'}]}})
        if '/api/resource/occupation' in str(req.url):
            return httpx.Response(200, json={
                'uri': occ_uri,
                'title': 'clinical pharmacist',
                'code': '2262',
                'description': {'en': {'literal': 'Advises patients and prescribers on safe medication therapy.'}},
                '_links': {
                    'hasEssentialSkill': [{'uri': skill_uri, 'title': 'pharmacovigilance monitoring', 'skillType': 'http://data.europa.eu/esco/skill-type/skill'}],
                    'hasOptionalSkill': [],
                },
            })
        if '/api/search' in str(req.url) and 'type=skill' in str(req.url):
            return httpx.Response(200, json={'_embedded': {'results': [{
                'uri': skill_uri,
                'title': 'pharmacovigilance monitoring',
                'alternativeLabel': {'en': ['drug safety monitoring']},
                'description': {'en': {'literal': 'Monitoring adverse drug reactions in clinical practice.'}},
                '_links': {'hasSkillType': [{'uri': 'http://data.europa.eu/esco/skill-type/skill'}]},
            }]}})
        raise AssertionError(req.url)

    real_client = httpx.Client
    with patch('httpx.Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
        with connection() as db:
            ensure_taxonomy_bootstrapped(db)
            synced = sync_esco_occupation(db, 'clinical pharmacist')
            assert synced and synced['skills_linked'] >= 1
            occs = search_occupations(db, query='Clinical Pharmacist')
            assert occs and occs[0]['source'] == 'esco'
        extracted, _, _ = extract_skills('SKILLS\ndrug safety monitoring\n')
        assert 'pharmacovigilance monitoring' in extracted


def test_independent_source_profiles_and_taxonomy_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv('SKILL_DATABASE_PATH', str(tmp_path / 'api_skills.sqlite3'))
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    monkeypatch.setenv('SKILL_ENABLE_ESCO_API', 'false')
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        stats = client.get('/api/component01/taxonomy/stats').json()
        assert stats['occupations'] >= 880
        occs = client.get('/api/component01/taxonomy/occupations?q=nurse').json()['occupations']
        assert occs

        session = client.post('/api/component01/skills/session').json()
        cid = session['candidate_id']
        headers = {'Authorization': 'Bearer ' + session['access_token']}

        import pymupdf
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 40), 'SUMMARY\nAccountant\nSKILLS\nIntuit QuickBooks, Microsoft Excel\nEXPERIENCE\nPrepared audits using Intuit QuickBooks.')
            pdf_bytes = doc.tobytes()

        up = client.post('/api/component01/skills/upload', data={'candidate_id': cid}, files={'file': ('cv.pdf', pdf_bytes)}, headers=headers)
        assert up.status_code == 200
        details = client.get(f'/api/component01/skills/{cid}/details', headers=headers).json()
        assert set(details['source_profiles']) == {'cv', 'github', 'linkedin'}
        assert details['source_profiles']['cv']['status'] == 'completed'
        assert details['source_profiles']['github']['status'] == 'not_provided'
        assert details['source_profiles']['linkedin']['status'] == 'not_provided'
        assert details['skills'][0]['percentage'] >= 30
        assert 'score_factors' in details['skills'][0]['xai']
