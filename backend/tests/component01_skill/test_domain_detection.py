"""Phase 1 tests: multi-domain CV support and automatic domain detection."""
from pathlib import Path
from unittest.mock import patch
import pytest
from app.component01_skill.services.cv_parser import parse_cv
from app.component01_skill.services.domain_detector import SUPPORTED_DOMAINS, detect_domain
from app.component01_skill.services.profile_service import process_cv
from app.component01_skill.services.skill_assessor import assess_skills
from app.component01_skill.services.skill_extractor import extract_skills

SAMPLE = Path(__file__).parents[2] / 'app/component01_skill/Tharindi_Jayawickrama_Sample_CV_Usernames_Only.pdf'

DOMAIN_CVS = {
    'Software Engineering': (
        'SUMMARY\nFull-Stack Software Developer building scalable web applications.\n'
        'SKILLS\nReact, Node.js, Express.js, TypeScript, Jest\n'
        'PROJECTS\nBuilt a React and Node.js REST API platform with automated Jest unit testing.\n'
    ),
    'Data Science': (
        'SUMMARY\nData Scientist focused on statistical modeling and experimentation.\n'
        'SKILLS\nPython, R, Pandas, NumPy, SciPy, Feature Engineering, Hypothesis Testing\n'
        'PROJECTS\nAnalyzed customer churn using Pandas, SciPy, and statistical modeling with A/B testing.\n'
    ),
    'Data Analytics': (
        'SUMMARY\nData Analyst and Business Intelligence specialist creating executive dashboards.\n'
        'SKILLS\nPower BI, Tableau, Microsoft Excel, DAX, Looker, SQL, ETL\n'
        'PROJECTS\nDesigned interactive Power BI and Tableau dashboards using DAX and ETL pipelines.\n'
    ),
    'UI/UX Design': (
        'SUMMARY\nUI/UX Designer crafting accessible interfaces and design systems.\n'
        'SKILLS\nFigma, Adobe XD, Sketch, Wireframing, Prototyping, User Research, Usability Testing\n'
        'PROJECTS\nPrototyped mobile checkout flows in Figma and ran usability testing with users.\n'
    ),
    'Networking': (
        'SUMMARY\nNetwork Engineer managing enterprise routing and switching infrastructure.\n'
        'SKILLS\nCisco IOS, TCP/IP, Subnetting, Routing and Switching, Wireshark, DNS, DHCP, VPN\n'
        'PROJECTS\nConfigured VLANs, OSPF routing, and VPN tunnels on Cisco IOS routers and analyzed packets in Wireshark.\n'
    ),
    'Cybersecurity': (
        'SUMMARY\nCybersecurity Analyst specializing in SOC monitoring and penetration testing.\n'
        'SKILLS\nSIEM, OWASP, Penetration Testing, Vulnerability Assessment, Incident Response, Nmap, Burp Suite, Kali Linux\n'
        'PROJECTS\nAudited web apps against OWASP Top 10 using Burp Suite and Nmap; monitored SIEM alerts for incident response.\n'
    ),
    'Cloud Computing': (
        'SUMMARY\nCloud Engineer automating scalable cloud infrastructure.\n'
        'SKILLS\nAWS, Azure, Google Cloud Platform, Terraform, Kubernetes, Docker, Ansible\n'
        'PROJECTS\nProvisioned AWS EC2 and Amazon S3 infrastructure with Terraform and deployed Kubernetes clusters.\n'
    ),
    'Database Administration': (
        'SUMMARY\nDatabase Administrator experienced in high availability and performance tuning.\n'
        'SKILLS\nOracle Database, Microsoft SQL Server, PostgreSQL, Database Tuning, Backup and Recovery, Database Replication, Schema Design\n'
        'PROJECTS\nAdministered Oracle Database and SQL Server clusters, tuned indexing, and automated backup and recovery.\n'
    ),
    'IT Support': (
        'SUMMARY\nIT Support Specialist delivering help desk and endpoint administration.\n'
        'SKILLS\nActive Directory, ServiceNow, ITIL, Windows Server, Microsoft 365, Hardware Troubleshooting\n'
        'PROJECTS\nResolved ServiceNow support tickets, managed Active Directory users, and troubleshot Windows Server endpoints.\n'
    ),
    'AI/ML': (
        'SUMMARY\nAI Engineer building deep learning, NLP, and LLM systems.\n'
        'SKILLS\nPyTorch, TensorFlow, Keras, Natural Language Processing, Computer Vision, Hugging Face, Large Language Models, LangChain, MLOps\n'
        'PROJECTS\nTrained PyTorch transformer models and built a LangChain RAG pipeline for natural language processing.\n'
    ),
}


def test_all_ten_required_domains_are_supported():
    expected = {
        'Software Engineering',
        'Data Science',
        'Data Analytics',
        'UI/UX Design',
        'Networking',
        'Cybersecurity',
        'Cloud Computing',
        'Database Administration',
        'IT Support',
        'AI/ML',
    }
    assert set(SUPPORTED_DOMAINS) == expected


@pytest.mark.parametrize('expected_domain,cv_text', list(DOMAIN_CVS.items()))
def test_detects_each_supported_domain_and_marks_relevant_skills(expected_domain, cv_text, monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    extracted, _, _ = extract_skills(cv_text)
    detected = detect_domain(cv_text, extracted)
    assert detected['status'] == 'detected'
    assert detected['primary_domain'] == expected_domain
    assert detected['confidence'] in {'medium', 'high'}
    assessed = assess_skills(extracted, detected_domain=detected)
    assert assessed
    assert any(skill['relevant_to_domain'] for skill in assessed)
    assert all(expected_domain in skill['domains'] for skill in assessed if skill['relevant_to_domain'])


def test_sample_cv_detects_software_engineering():
    text = parse_cv(SAMPLE.name, SAMPLE.read_bytes())
    extracted, _, _ = extract_skills(text)
    detected = detect_domain(text, extracted)
    assert detected['primary_domain'] == 'Software Engineering'
    assert detected['confidence'] == 'high'


def test_short_acronyms_do_not_false_match_ordinary_prose(monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    text = 'SUMMARY\nI am eager to learn, and I soc it to daily challenges in dax or etl ideas.\n'
    extracted, _, _ = extract_skills(text)
    assert 'IAM' not in extracted
    assert 'DAX' not in extracted
    assert 'ETL' not in extracted
    detected = detect_domain(text, extracted)
    assert detected['primary_domain'] is None
    assert detected['status'] == 'undetermined'


def test_negative_domain_mentions_are_not_counted(monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    text = (
        'SUMMARY\nI have no cybersecurity analyst experience and no penetration testing background.\n'
        'SKILLS\nFigma, Wireframing, Prototyping, User Research\n'
        'PROJECTS\nDesigned interactive Figma prototypes and conducted usability testing.\n'
    )
    extracted, _, _ = extract_skills(text)
    detected = detect_domain(text, extracted)
    assert detected['primary_domain'] == 'UI/UX Design'


def test_process_cv_persists_detected_domain_and_filters_relevant_skills(monkeypatch):
    monkeypatch.setenv('SKILL_ENABLE_SBERT', 'false')
    cv_text = (
        'SUMMARY\nCybersecurity Analyst focused on vulnerability assessment.\n'
        'SKILLS\nSIEM, OWASP, Nmap, HTML\n'
        'PROJECTS\nAudited endpoints with Nmap and monitored SIEM alerts.\n'
    )
    with patch('app.component01_skill.services.profile_service.parse_cv_document', return_value=(cv_text, [])), \
         patch('app.component01_skill.services.profile_service.repository.save_assessment', side_effect=lambda cid, content, details: details):
        details = process_cv('candidate_1', 'cv.pdf', b'pdf')
    assert details['detected_domain']['primary_domain'] == 'Cybersecurity'
    by_name = {s['name']: s for s in details['skills']}
    assert by_name['SIEM']['relevant_to_domain'] is True
    assert by_name['Nmap']['relevant_to_domain'] is True
    assert by_name['HTML']['relevant_to_domain'] is False
