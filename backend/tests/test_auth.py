import hashlib
import os
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import config, repository
from app.auth.router import router


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'AUTH_DATABASE_PATH': str(Path(self.temp.name) / 'auth.sqlite3'),
            'AUTH_SECRET_KEY': secrets.token_urlsafe(48),
            'AUTH_ALLOWED_ORIGINS': 'http://localhost:5173',
            'AUTH_COOKIE_SECURE': 'false', 'AUTH_COOKIE_SAMESITE': 'lax',
        })
        self.env.start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app, headers={'Origin': 'http://localhost:5173'})
        self.account = {'full_name': 'Research Student', 'email': 'student@example.com', 'password': 'a long unique test passphrase'}

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def register(self):
        response = self.client.post('/api/auth/register', json=self.account)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def login(self, **extra):
        response = self.client.post('/api/auth/login', json={**self.account, **extra})
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_registration_hashes_password_and_normalizes_email(self):
        self.account['email'] = ' Student@Example.com '
        user = self.register()
        self.assertEqual(user['email'], 'student@example.com')
        self.assertNotIn('password_hash', user)
        with repository.connection() as db:
            row = db.execute('SELECT password_hash FROM auth_users').fetchone()
        self.assertTrue(row['password_hash'].startswith('$argon2id$'))
        self.assertNotIn(self.account['password'], row['password_hash'])
        self.assertEqual(self.client.post('/api/auth/register', json=self.account).status_code, 409)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_login_cookie_me_and_logout_revocation(self):
        user = self.register()
        login = self.login()
        cookie = login.headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=lax', cookie)
        self.assertNotIn('Max-Age', cookie)
        self.assertNotIn('access_token', login.json())
        token = self.client.cookies.get(config.COOKIE)
        self.assertEqual(self.client.get('/api/auth/me').json()['user'], user)
        self.assertEqual(self.client.post('/api/auth/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        # A captured JWT is revoked server-side, not only removed from the browser.
        replay = self.client.get('/api/auth/me', headers={'Cookie': f'{config.COOKIE}={token}'})
        self.assertEqual(replay.status_code, 401)

    def test_remember_me_secure_cookie_and_expiry(self):
        self.register()
        with patch.dict(os.environ, {'AUTH_COOKIE_SECURE': 'true', 'AUTH_COOKIE_SAMESITE': 'none'}):
            response = self.login(remember_me=True)
        self.assertIn('Max-Age=2592000', response.headers['set-cookie'])
        self.assertIn('Secure', response.headers['set-cookie'])
        self.assertIn('SameSite=none', response.headers['set-cookie'])
        self.assertGreater(response.json()['expires_at'], time.time() + 29 * 86400)

    def test_incorrect_password_unknown_user_and_rate_limit(self):
        self.register()
        wrong = self.client.post('/api/auth/login', json={**self.account, 'password': 'wrong'})
        unknown = self.client.post('/api/auth/login', json={**self.account, 'email': 'nobody@example.com'})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json(), unknown.json())
        for _ in range(10):
            last = self.client.post('/api/auth/login', json={**self.account, 'password': 'wrong'})
        self.assertEqual(last.status_code, 429)

    def test_forged_and_expired_tokens_rejected(self):
        self.register(); self.login()
        token = self.client.cookies.get(config.COOKIE)
        claims = jwt.decode(token, config.secret(), algorithms=['HS256'], audience=config.AUDIENCE)
        for key, value in [('exp', int(time.time()) - 1), ('aud', 'another-app'), ('iss', 'another-issuer')]:
            changed = jwt.encode({**claims, key: value}, config.secret(), algorithm='HS256')
            response = self.client.get('/api/auth/me', headers={'Cookie': f'{config.COOKIE}={changed}'})
            self.assertEqual(response.status_code, 401)
        response = self.client.get('/api/auth/me', headers={'Cookie': f'{config.COOKIE}={token[:-8]}forgedxx'})
        self.assertEqual(response.status_code, 401)

    def test_validation_and_csrf(self):
        for changes in [{'email': 'invalid'}, {'full_name': '  '}, {'password': 'short'}]:
            self.assertEqual(self.client.post('/api/auth/register', json={**self.account, **changes}).status_code, 422)
        for endpoint in ['register', 'login', 'logout', 'forgot-password', 'reset-password']:
            response = self.client.post('/api/auth/' + endpoint, json=self.account, headers={'Origin': 'https://evil.example'})
            self.assertEqual(response.status_code, 403)
        with patch.dict(os.environ, {'AUTH_SECRET_KEY': ''}):
            self.assertEqual(self.client.post('/api/auth/register', json=self.account).status_code, 503)

    def test_password_reset_is_single_use_and_revokes_sessions(self):
        self.register(); self.login()
        old_token = self.client.cookies.get(config.COOKIE)
        with patch('app.auth.mailer.settings'), patch('app.auth.mailer.send_reset') as send:
            known = self.client.post('/api/auth/forgot-password', json={'email': self.account['email']})
            unknown = self.client.post('/api/auth/forgot-password', json={'email': 'unknown@example.com'})
            self.assertEqual(known.json(), unknown.json())
            token = send.call_args.args[1]
        with repository.connection() as db:
            stored = db.execute('SELECT token_hash FROM auth_resets').fetchone()['token_hash']
        self.assertEqual(stored, hashlib.sha256(token.encode()).hexdigest())
        body = {'token': token, 'password': 'a different long passphrase'}
        self.assertEqual(self.client.post('/api/auth/reset-password', json=body).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/reset-password', json=body).status_code, 400)
        self.assertEqual(self.client.get('/api/auth/me', headers={'Cookie': f'{config.COOKIE}={old_token}'}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json=self.account).status_code, 401)
        self.login(password=body['password'])

    def test_reset_delivery_requires_configuration(self):
        with patch.dict(os.environ, {'AUTH_SMTP_HOST': ''}):
            response = self.client.post('/api/auth/forgot-password', json={'email': self.account['email']})
        self.assertEqual(response.status_code, 503)


if __name__ == '__main__':
    unittest.main()
