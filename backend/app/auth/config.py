import os
from pathlib import Path

from fastapi import HTTPException

COOKIE = 'careernova_session'
ISSUER = 'careernova'
AUDIENCE = 'careernova-web'


def allowed_origins():
    return [value.strip().rstrip('/') for value in os.getenv(
        'AUTH_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',') if value.strip() and value.strip() != '*']


def secret():
    value = os.getenv('AUTH_SECRET_KEY', '')
    if len(value.encode()) < 32:
        raise HTTPException(503, 'Account service is not configured. Set AUTH_SECRET_KEY on the backend.')
    return value


def database_path():
    return Path(os.getenv('AUTH_DATABASE_PATH', str(Path(__file__).parents[2] / '.data' / 'auth.sqlite3')))


def cookie_options():
    secure = os.getenv('AUTH_COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.getenv('AUTH_COOKIE_SAMESITE', 'lax').lower()
    if same_site not in {'lax', 'strict', 'none'} or (same_site == 'none' and not secure):
        raise HTTPException(503, 'Invalid authentication cookie configuration.')
    return {'httponly': True, 'secure': secure, 'samesite': same_site, 'path': '/api/auth'}
