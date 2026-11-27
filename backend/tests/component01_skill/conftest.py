"""Isolate Component 01 unit test databases so tests never pollute live .data/skills.sqlite3."""
import pytest


@pytest.fixture(autouse=True)
def isolated_skill_db(tmp_path, monkeypatch):
    if 'SKILL_DATABASE_PATH' not in __import__('os').environ:
        monkeypatch.setenv('SKILL_DATABASE_PATH', str(tmp_path / 'test_skills.sqlite3'))
    monkeypatch.setenv('SKILL_ENABLE_ESCO_API', 'false')
