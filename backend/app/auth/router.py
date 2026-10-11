import hashlib
import secrets
import sqlite3
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from . import config, mailer, repository, security
from .schemas import EmailInput, LoginInput, RegisterInput, ResetInput, Session, User

router = APIRouter(prefix='/api/auth', tags=['Authentication'])
write_access = [Depends(security.trusted_origin)]


@router.post('/register', response_model=User, status_code=201, dependencies=write_access)
def register(body: RegisterInput, request: Request):
    security.rate_limit(request, 'register')
    user_id = uuid4().hex
    hashed = security.password_hasher.hash(body.password)
    try:
        with repository.connection() as db:
            db.execute('INSERT INTO auth_users VALUES (?,?,?,?)', (user_id, body.full_name, body.email, hashed))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'An account with this email already exists. Please log in.') from exc
    return {'id': user_id, 'full_name': body.full_name, 'email': body.email}


@router.post('/login', response_model=Session, dependencies=write_access)
def login(body: LoginInput, request: Request, response: Response):
    options = config.cookie_options()
    security.rate_limit(request, 'login', body.email)
    with repository.connection() as db:
        row = db.execute('SELECT * FROM auth_users WHERE email=?', (body.email,)).fetchone()
    valid = security.verify_password(row['password_hash'] if row else None, body.password)
    if not row or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    if security.password_hasher.check_needs_rehash(row['password_hash']):
        with repository.connection() as db:
            db.execute('UPDATE auth_users SET password_hash=? WHERE id=?',
                       (security.password_hasher.hash(body.password), row['id']))
    # Replace a valid session in this browser instead of leaving it reusable.
    try:
        previous = security.current_session(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    else:
        with repository.connection() as db:
            db.execute('DELETE FROM auth_sessions WHERE id=?', (previous['session_id'],))
    token, expires = security.create_session(row['id'], body.remember_me)
    response.set_cookie(config.COOKIE, token, max_age=30 * 86400 if body.remember_me else None, **options)
    return {'user': dict(row), 'expires_at': expires}


@router.get('/me', response_model=Session)
def me(session=Depends(security.current_session)):
    return session


@router.post('/logout', status_code=204, dependencies=write_access)
def logout(request: Request, response: Response):
    try:
        session = security.current_session(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    else:
        with repository.connection() as db:
            db.execute('DELETE FROM auth_sessions WHERE id=?', (session['session_id'],))
    response.delete_cookie(config.COOKIE, **config.cookie_options())


@router.post('/forgot-password', dependencies=write_access)
def forgot_password(body: EmailInput, request: Request):
    security.rate_limit(request, 'reset', body.email)
    mailer.settings()
    with repository.connection() as db:
        row = db.execute('SELECT id FROM auth_users WHERE email=?', (body.email,)).fetchone()
    if row:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with repository.connection() as db:
            db.execute('DELETE FROM auth_resets WHERE expires_at<=?', (int(time.time()),))
            db.execute('INSERT INTO auth_resets VALUES (?,?,?)', (digest, row['id'], int(time.time()) + 1800))
        try:
            mailer.send_reset(body.email, token)
        except Exception:
            # Do not disclose whether this email has an account, or log its token.
            with repository.connection() as db:
                db.execute('DELETE FROM auth_resets WHERE token_hash=?', (digest,))
    return {'message': 'If an account exists for this email, a password reset link will be sent.'}


@router.post('/reset-password', dependencies=write_access)
def reset_password(body: ResetInput, request: Request):
    security.rate_limit(request, 'reset-confirm')
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    hashed = security.password_hasher.hash(body.password)
    with repository.connection() as db:
        # Serialize consumption so two requests cannot reuse the same token.
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT user_id FROM auth_resets WHERE token_hash=? AND expires_at>?',
                         (digest, int(time.time()))).fetchone()
        if not row:
            raise HTTPException(400, 'This reset link is invalid or expired. Request a new one.')
        db.execute('UPDATE auth_users SET password_hash=? WHERE id=?', (hashed, row['user_id']))
        db.execute('DELETE FROM auth_resets WHERE user_id=?', (row['user_id'],))
        db.execute('DELETE FROM auth_sessions WHERE user_id=?', (row['user_id'],))
    return {'message': 'Password updated. Please log in with your new password.'}
