"""User profile, research consent and account management for the /profile page.

Everything lives under /api/auth/profile so the existing session cookie (path /api/auth) is
sent. Two kinds of account can use it:
  * email/password accounts: the existing careernova_session cookie;
  * Google accounts (Supabase on the frontend): an "Authorization: Bearer <Supabase access token>"
    header, checked with Supabase's /auth/v1/user endpoint. This needs SUPABASE_URL and
    SUPABASE_ANON_KEY on the backend (the same public values the frontend uses).

Profiles are stored in the auth database, table auth_profiles, keyed by "<provider>:<user id>".
The table is created on first use; no migration step is needed.
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, field_validator

from . import config, repository, security
from .schemas import Password

router = APIRouter(prefix='/api/auth', tags=['Profile'])

MAX_AVATAR_BYTES = 2 * 1024 * 1024
ACADEMIC_YEARS = ('Year 1', 'Year 2', 'Year 3', 'Year 4', 'Postgraduate', 'Graduate')
FIELDS = ('full_name', 'phone', 'location', 'university', 'degree', 'academic_year', 'graduation_year',
          'linkedin_url', 'github_url', 'bio', 'work_type', 'region')

SCHEMA = '''
    CREATE TABLE IF NOT EXISTS auth_profiles (
        account TEXT PRIMARY KEY,
        full_name TEXT, phone TEXT, location TEXT, university TEXT, degree TEXT,
        academic_year TEXT, graduation_year INTEGER, linkedin_url TEXT, github_url TEXT, bio TEXT,
        interests_json TEXT NOT NULL DEFAULT '[]', work_type TEXT, region TEXT,
        avatar BLOB, avatar_type TEXT, avatar_updated_at INTEGER,
        research_consent INTEGER, consent_given_at INTEGER, consent_updated_at INTEGER,
        cv_file_name TEXT, cv_uploaded_at INTEGER,
        member_since INTEGER, updated_at INTEGER
    );
'''


def ensure_schema(db):
    db.execute(SCHEMA)  # execute, not executescript: executescript would commit the open transaction


def record_signup(db, user_id):
    """Called by /register so new accounts have a real "member since" date."""
    ensure_schema(db)
    db.execute('INSERT OR IGNORE INTO auth_profiles (account, member_since) VALUES (?, ?)',
               (f'password:{user_id}', int(time.time())))


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat() if seconds else None


# ---------- Who is calling ----------

_google_cache = {}  # sha256(token) -> (expires_at, user)


def google_user(token):
    url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    key = os.getenv('SUPABASE_ANON_KEY', '').strip()
    if not url or not key:
        raise HTTPException(503, 'Google profiles are not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY on the backend.')
    digest = hashlib.sha256(token.encode()).hexdigest()
    cached = _google_cache.get(digest)
    if cached and cached[0] > time.time():
        return cached[1]
    try:
        reply = httpx.get(f'{url}/auth/v1/user', headers={'Authorization': f'Bearer {token}', 'apikey': key}, timeout=8)
    except httpx.HTTPError as exc:
        raise HTTPException(503, 'Could not reach Google sign-in to confirm your account. Please try again.') from exc
    if reply.status_code != 200:
        raise HTTPException(401, 'Your Google session has ended. Please sign in again.')
    data = reply.json()
    meta = data.get('user_metadata') or {}
    created = data.get('created_at')
    user = {
        'id': data['id'], 'email': data.get('email') or '',
        'full_name': meta.get('full_name') or meta.get('name') or (data.get('email') or '').split('@')[0] or 'CareerNova member',
        'member_since': int(datetime.fromisoformat(created.replace('Z', '+00:00')).timestamp()) if created else None,
    }
    if len(_google_cache) > 500:
        _google_cache.clear()
    _google_cache[digest] = (time.time() + 60, user)
    return user


def current_account(request: Request):
    header = request.headers.get('authorization', '')
    if header.lower().startswith('bearer '):
        user = google_user(header[7:].strip())
        return {'key': f"google:{user['id']}", 'provider': 'google', **user}
    session = security.current_session(request)
    user = session['user']
    return {'key': f"password:{user['id']}", 'provider': 'password', 'id': user['id'], 'email': user['email'],
            'full_name': user['full_name'], 'member_since': None, 'session_id': session['session_id']}


def trusted_origin(request: Request):
    # Same rule as the other account writes, without requiring the cookie secret for Google users.
    if request.headers.get('origin') not in config.allowed_origins():
        raise HTTPException(403, 'Request origin is not allowed.')


Account = Annotated[dict, Depends(current_account)]
write_access = [Depends(trusted_origin)]


# ---------- Input ----------

def _blank_to_none(value):
    if isinstance(value, str):
        value = ' '.join(value.split()) if '\n' not in value else value.strip()
        return value or None
    return value


class ProfileInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=100)
    university: str | None = Field(default=None, max_length=120)
    degree: str | None = Field(default=None, max_length=120)
    academic_year: Literal[ACADEMIC_YEARS] | None = None
    graduation_year: int | None = Field(default=None, ge=1990, le=2100)
    linkedin_url: str | None = Field(default=None, max_length=200)
    github_url: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=300)
    interests: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(default_factory=list, max_length=10)
    work_type: Literal['remote', 'hybrid', 'onsite'] | None = None
    region: Literal['sri_lanka', 'remote', 'global'] | None = None

    @field_validator('full_name', 'phone', 'location', 'university', 'degree', 'linkedin_url', 'github_url', 'bio', 'academic_year', 'work_type', 'region', mode='before')
    @classmethod
    def clean(cls, value):
        return _blank_to_none(value)

    @field_validator('phone')
    @classmethod
    def check_phone(cls, value):
        if value and not re.fullmatch(r'\+?[0-9][0-9 ()-]{6,18}', value):
            raise ValueError('Enter a phone number with digits only, for example +94 77 123 4567.')
        return value

    @field_validator('linkedin_url')
    @classmethod
    def check_linkedin(cls, value):
        if value and not re.fullmatch(r'https://([a-z]{2,3}\.)?linkedin\.com/[^\s]+', value, re.I):
            raise ValueError('Enter a LinkedIn link that starts with https://linkedin.com/ or https://www.linkedin.com/.')
        return value

    @field_validator('github_url')
    @classmethod
    def check_github(cls, value):
        if value and not re.fullmatch(r'https://(www\.)?github\.com/[A-Za-z0-9-]+/?', value):
            raise ValueError('Enter a GitHub profile link like https://github.com/your-username.')
        return value

    @field_validator('interests')
    @classmethod
    def unique_interests(cls, value):
        return list(dict.fromkeys(' '.join(item.split()) for item in value if item.strip()))


class ConsentInput(BaseModel):
    research_use: bool


class CvInput(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)


class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class DeleteInput(BaseModel):
    confirm: str

    @field_validator('confirm')
    @classmethod
    def typed_delete(cls, value):
        if value != 'DELETE':
            raise ValueError('Type DELETE in capital letters to confirm.')
        return value


# ---------- Storage ----------

def load_row(db, account):
    ensure_schema(db)
    row = db.execute('SELECT * FROM auth_profiles WHERE account=?', (account['key'],)).fetchone()
    if row is None:
        db.execute('INSERT INTO auth_profiles (account, member_since) VALUES (?, ?)', (account['key'], account.get('member_since')))
        row = db.execute('SELECT * FROM auth_profiles WHERE account=?', (account['key'],)).fetchone()
    elif account.get('member_since') and not row['member_since']:
        db.execute('UPDATE auth_profiles SET member_since=? WHERE account=?', (account['member_since'], account['key']))
        row = db.execute('SELECT * FROM auth_profiles WHERE account=?', (account['key'],)).fetchone()
    return row


def view(account, row):
    name = account['full_name'] if account['provider'] == 'password' else (row['full_name'] or account['full_name'])
    consent = None if row['research_consent'] is None else bool(row['research_consent'])
    return {
        'account': {'provider': account['provider'], 'id': account['id'], 'email': account['email'],
                    'full_name': name, 'member_since': iso(row['member_since'])},
        'profile': {**{field: row[field] for field in FIELDS}, 'full_name': name,
                    'interests': json.loads(row['interests_json'] or '[]')},
        'avatar': {'present': row['avatar'] is not None, 'updated_at': iso(row['avatar_updated_at'])},
        'consent': {'research_use': consent, 'given_at': iso(row['consent_given_at']), 'updated_at': iso(row['consent_updated_at'])},
        'cv': {'file_name': row['cv_file_name'], 'uploaded_at': iso(row['cv_uploaded_at'])},
        'updated_at': iso(row['updated_at']),
    }


def read(account):
    with repository.connection() as db:
        return view(account, load_row(db, account))


# ---------- Routes ----------

@router.get('/profile')
def get_profile(account: Account):
    return read(account)


@router.put('/profile', dependencies=write_access)
def save_profile(body: ProfileInput, account: Account):
    now = int(time.time())
    with repository.connection() as db:
        load_row(db, account)
        values = body.model_dump()
        db.execute(f'''UPDATE auth_profiles SET {", ".join(f"{field}=?" for field in FIELDS)}, interests_json=?, updated_at=?
                       WHERE account=?''', (*[values[field] for field in FIELDS], json.dumps(values['interests']), now, account['key']))
        if account['provider'] == 'password':
            db.execute('UPDATE auth_users SET full_name=? WHERE id=?', (values['full_name'], account['id']))
    if account['provider'] == 'password':
        account = {**account, 'full_name': values['full_name']}
    return read(account)


@router.put('/profile/avatar', dependencies=write_access)
async def save_avatar(account: Account, file: UploadFile = File(...)):
    content = await file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(413, 'Choose a photo of 2 MB or less.')
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        kind = 'image/png'
    elif content.startswith(b'\xff\xd8\xff'):
        kind = 'image/jpeg'
    else:
        raise HTTPException(415, 'Choose a JPG or PNG photo.')
    with repository.connection() as db:
        load_row(db, account)
        db.execute('UPDATE auth_profiles SET avatar=?, avatar_type=?, avatar_updated_at=? WHERE account=?',
                   (content, kind, int(time.time()), account['key']))
    return read(account)


@router.delete('/profile/avatar', dependencies=write_access)
def delete_avatar(account: Account):
    with repository.connection() as db:
        load_row(db, account)
        db.execute('UPDATE auth_profiles SET avatar=NULL, avatar_type=NULL, avatar_updated_at=NULL WHERE account=?', (account['key'],))
    return read(account)


@router.get('/profile/avatar')
def get_avatar(account: Account):
    with repository.connection() as db:
        row = load_row(db, account)
    if row['avatar'] is None:
        raise HTTPException(404, 'No profile photo has been uploaded.')
    return Response(row['avatar'], media_type=row['avatar_type'], headers={'Cache-Control': 'private, no-store'})


@router.put('/profile/consent', dependencies=write_access)
def save_consent(body: ConsentInput, account: Account):
    now = int(time.time())
    with repository.connection() as db:
        row = load_row(db, account)
        given = now if body.research_use and not row['research_consent'] else row['consent_given_at']
        db.execute('UPDATE auth_profiles SET research_consent=?, consent_given_at=?, consent_updated_at=? WHERE account=?',
                   (int(body.research_use), given if body.research_use else None, now, account['key']))
    return read(account)


@router.put('/profile/cv', dependencies=write_access)
def record_cv(body: CvInput, account: Account):
    # Only the name and time are kept; the CV file itself is never stored.
    with repository.connection() as db:
        load_row(db, account)
        db.execute('UPDATE auth_profiles SET cv_file_name=?, cv_uploaded_at=? WHERE account=?',
                   (body.file_name.strip()[:255], int(time.time()), account['key']))
    return read(account)


@router.get('/profile/export')
def export_profile(account: Account):
    data = read(account)
    return {'exported_at': iso(int(time.time())), **data,
            'note': 'Profile photo bytes are not included. Results from the research modules are added by the app.'}


@router.post('/password', status_code=204, dependencies=write_access)
def change_password(body: PasswordChangeInput, request: Request, account: Account):
    if account['provider'] != 'password':
        raise HTTPException(400, 'This account signs in with Google, so it has no CareerNova password.')
    security.rate_limit(request, 'password', account['email'])
    with repository.connection() as db:
        row = db.execute('SELECT password_hash FROM auth_users WHERE id=?', (account['id'],)).fetchone()
    if not row or not security.verify_password(row['password_hash'], body.current_password):
        raise HTTPException(400, 'Your current password is incorrect.')
    if body.new_password == body.current_password:
        raise HTTPException(400, 'Choose a new password that is different from the current one.')
    with repository.connection() as db:
        db.execute('UPDATE auth_users SET password_hash=? WHERE id=?', (security.password_hasher.hash(body.new_password), account['id']))
        # Other devices are signed out; this one stays signed in.
        db.execute('DELETE FROM auth_sessions WHERE user_id=? AND id<>?', (account['id'], account['session_id']))
        db.execute('DELETE FROM auth_resets WHERE user_id=?', (account['id'],))


@router.post('/profile/delete', dependencies=write_access)
def delete_account(body: DeleteInput, response: Response, account: Account):
    with repository.connection() as db:
        ensure_schema(db)
        db.execute('DELETE FROM auth_profiles WHERE account=?', (account['key'],))
        if account['provider'] == 'password':
            db.execute('DELETE FROM auth_sessions WHERE user_id=?', (account['id'],))
            db.execute('DELETE FROM auth_resets WHERE user_id=?', (account['id'],))
            db.execute('DELETE FROM auth_users WHERE id=?', (account['id'],))
    if account['provider'] == 'password':
        response.delete_cookie(config.COOKIE, **config.cookie_options())
    return {'deleted': True, 'provider': account['provider'],
            # A Google sign-in identity is held by Supabase and needs an administrator to remove.
            'sign_in_identity_kept': account['provider'] == 'google'}
