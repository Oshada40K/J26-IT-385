# SHARED FILE - controlled by the group leader.
# Loads environment variables from backend/.env (if present).

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/career_db",
)
