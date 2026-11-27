"""Tests for contact isolation, 4-tier evidence classification, career stage, and recommendations."""
from unittest.mock import patch
from app.component01_skill.services.cv_parser import evidence_units
from app.component01_skill.services.domain_detector import detect_domain
from app.component01_skill.services.profile_service import process_cv
from app.component01_skill.services.skill_assessor import assess_skills
from app.component01_skill.services.skill_extractor import extract_skills


def test_personal_info_and_contact_details_are_never_extracted_as_skills():
    cv = (
        'DR. MAYA PERERA\n'
        'Colombo, Sri Lanka | +94 71 234 5678 | maya.python.sql@email.com\n'
        'CLINICAL SKILLS\n'
        'Patient history taking, CPR\n'
    )
    units = evidence_units(cv)
    assert any(u['section'] == 'personal_info' for u in units)
    extracted, _, _ = extract_skills(cv)
    assert 'Python' not in extracted
    assert 'SQL' not in extracted
    assert {'Patient history taking', 'CPR'} <= set(extracted)


def test_four_evidence_tiers_and_consistent_proficiency_scoring():
    cv = (
        'CLINICAL SKILLS\n'
        'Patient confidentiality, ECG recording, Basic Life Support\n'
        'CLINICAL EXPERIENCE\n'
        'Observed ECG recording under supervision.\n'
        'Prepared draft clinical histories and case summaries for review.\n'
        'CERTIFICATIONS & ADDITIONAL INFORMATION\n'
        'Basic Life Support (BLS): University-approved student training workshop, 2025\n'
    )
    # Use "clinical note preparation" or "Patient history taking" for practical tier:
    cv_full = (
        'CLINICAL SKILLS\n'
        'Patient confidentiality, ECG recording, Basic Life Support, Patient history taking\n'
        'CLINICAL EXPERIENCE\n'
        'Observed ECG recording under supervision.\n'
        'Prepared Patient history taking notes and case summaries for review.\n'
        'CERTIFICATIONS & ADDITIONAL INFORMATION\n'
        'Basic Life Support (BLS): University-approved student training workshop, 2025\n'
    )
    extracted, _, _ = extract_skills(cv_full)
    assessed = {s['name']: s for s in assess_skills(extracted)}

    assert assessed['Patient history taking']['evidence_tier'] == 'practical_implementation'
    assert assessed['Patient history taking']['level'] == 3
    assert assessed['Patient history taking']['percentage'] >= 50

    assert assessed['ECG recording']['evidence_tier'] == 'observational'
    assert assessed['ECG recording']['level'] == 2
    assert 40 <= assessed['ECG recording']['percentage'] < 50

    assert assessed['Basic Life Support']['evidence_tier'] == 'training_certification'
    assert assessed['Basic Life Support']['level'] == 2

    assert assessed['Patient confidentiality']['evidence_tier'] == 'self_reported'
    assert assessed['Patient confidentiality']['level'] == 2
    assert assessed['Patient confidentiality']['percentage'] < assessed['ECG recording']['percentage']


def test_distinguishes_medical_student_from_nurse_and_builds_targeted_recommendations():
    cv = (
        'DR. MAYA PERERA\n'
        'Medical Student | Clinical Training | Patient Care & Community Health\n'
        'PROFESSIONAL SUMMARY\n'
        'Final-year medical student with supervised clinical exposure across internal medicine, general surgery, paediatrics.\n'
        'CLINICAL SKILLS\n'
        'Patient history taking, Patient confidentiality, ECG recording\n'
        'CLINICAL EXPERIENCE\n'
        'Clinical Clerkship Student — Teaching Hospital\n'
        'Prepared Patient history taking summaries; observed ECG recording under supervision.\n'
        'EDUCATION\n'
        'Bachelor of Medicine, Bachelor of Surgery (MBBS) — In Progress\n'
    )
    with patch('app.component01_skill.services.profile_service.parse_cv_document', return_value=(cv, [])), \
         patch('app.component01_skill.services.profile_service.repository.save_assessment', side_effect=lambda cid, content, details: details):
        details = process_cv('cand_med', 'maya.pdf', b'pdf')

    dom = details['detected_domain']
    assert dom['career_field'] == 'Healthcare'
    assert dom['career_stage']['stage'] == 'student_trainee'
    assert 'nurse' not in (dom['primary_occupation'] or '').lower()
    assert 'medical student' in (dom['primary_occupation'] or '').lower()

    recs = details['recommendations']
    assert recs['career_stage'] == 'Student / Trainee'
    assert recs['evidence_gaps']
    assert any('clinical' in r['recommendation'].lower() or 'supervised' in r['recommendation'].lower() for r in recs['evidence_gaps'])
