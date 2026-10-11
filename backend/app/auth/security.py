import hashlib
import secrets
import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException, Request

from . import config, repository

password_hasher = PasswordHasher()
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def verify_password(encoded, password):
    try:
        return password_hasher.verify(encoded or _dummy_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def trusted_origin(request: Request):
    # Cookie writes require an explicit trusted Origin, including login/logout.
    if request.headers.get('origin') not in config.allowed_origins():
        raise HTTPException(403, 'Request origin is not allowed.')
    config.secret()


def rate_limit(request, action, email=''):
    now = int(time.time())
    address = request.client.host if request.client else 'unknown'
    buckets = [(f'{action}:ip:{address}', 30)]
    if email:
        buckets.append((f'{action}:email:{email}', 10))
    limited = False
    with repository.connection() as db:
        db.execute('DELETE FROM auth_attempts WHERE expires_at<=?', (now,))
        for bucket, limit in buckets:
            key = hashlib.sha256(bucket.encode()).hexdigest()
            db.execute('INSERT INTO auth_attempts VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now + 900))
            if db.execute('SELECT count FROM auth_attempts WHERE key=?', (key,)).fetchone()['count'] > limit:
                limited = True
    if limited:
        raise HTTPException(429, 'Too many attempts. Please try again in 15 minutes.', headers={'Retry-After': '900'})


def create_session(user_id, remember):
    now = int(time.time())
    expires = now + (30 * 86400 if remember else 8 * 3600)
    session_id = secrets.token_urlsafe(32)
    token = jwt.encode({'sub': user_id, 'jti': session_id, 'iat': now, 'exp': expires,
                        'iss': config.ISSUER, 'aud': config.AUDIENCE}, config.secret(), algorithm='HS256')
    with repository.connection() as db:
        db.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (now,))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?)', (session_id, user_id, expires))
    return token, expires


def current_session(request: Request):
    token = request.cookies.get(config.COOKIE)
    if not token:
        raise HTTPException(401, 'Please log in to continue.')
    try:
        claims = jwt.decode(token, config.secret(), algorithms=['HS256'], issuer=config.ISSUER,
                            audience=config.AUDIENCE, options={'require': ['sub', 'jti', 'iat', 'exp', 'iss', 'aud']})
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, 'Your session has expired. Please log in again.') from exc
    with repository.connection() as db:
        row = db.execute('''SELECT u.id,u.full_name,u.email,s.expires_at FROM auth_sessions s
                            JOIN auth_users u ON u.id=s.user_id
                            WHERE s.id=? AND s.user_id=? AND s.expires_at>?''',
                         (claims['jti'], claims['sub'], int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, 'Your session has ended. Please log in again.')
    return {'user': dict(row), 'expires_at': row['expires_at'], 'session_id': claims['jti']}
