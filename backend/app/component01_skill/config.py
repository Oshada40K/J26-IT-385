"""Component-local configuration; no changes to the shared database."""
import os
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_PAGES = 50
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
METHOD_VERSION = 'cv_evidence_rubric_v1'


def database_path():
    return Path(os.getenv('SKILL_DATABASE_PATH', str(Path(__file__).parents[2] / '.data' / 'skills.sqlite3')))
