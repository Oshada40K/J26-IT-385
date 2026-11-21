"""Profile page endpoints: details, consent, CV record, photo, password change, export and deletion."""
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.profile import router as profile_router
from app.auth.router import router as auth_router

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


class ProfileTests(unittest.TestCase):
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
        app.include_router(auth_router)
        app.include_router(profile_router)
        self.client = TestClient(app, headers={'Origin': 'http://localhost:5173'})
        self.account = {'full_name': 'Research Student', 'email': 'student@example.com', 'password': 'a long unique test passphrase'}
        self.assertEqual(self.client.post('/api/auth/register', json=self.account).status_code, 201)
        self.assertEqual(self.client.post('/api/auth/login', json=self.account).status_code, 200)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def details(self, **changes):
        return {'full_name': 'Research Student', 'phone': '+94 77 123 4567', 'location': 'Colombo, Sri Lanka',
                'university': 'SLIIT', 'degree': 'BSc (Hons) in IT', 'academic_year': 'Year 4', 'graduation_year': 2027,
                'linkedin_url': 'https://www.linkedin.com/in/student', 'github_url': 'https://github.com/student',
                'bio': 'Interested in data.', 'interests': ['Data Science', 'Data Science', 'Cybersecurity'],
                'work_type': 'hybrid', 'region': 'sri_lanka', **changes}

    def test_new_profile_is_empty_with_real_member_since(self):
        data = self.client.get('/api/auth/profile').json()
        self.assertEqual(data['account']['provider'], 'password')
        self.assertIsNotNone(data['account']['member_since'])  # recorded at registration
        self.assertIsNone(data['profile']['university'])
        self.assertEqual(data['profile']['interests'], [])
        self.assertIsNone(data['consent']['research_use'])  # never asked yet
        self.assertIsNone(data['cv']['file_name'])

    def test_requires_login(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/auth/profile').status_code, 401)

    def test_save_details_and_name(self):
        response = self.client.put('/api/auth/profile', json=self.details(full_name='Research  Student Two'))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['profile']['university'], 'SLIIT')
        self.assertEqual(data['profile']['interests'], ['Data Science', 'Cybersecurity'])
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['full_name'], 'Research Student Two')

    def test_validation_messages(self):
        for field, value in [('github_url', 'github.com/x'), ('linkedin_url', 'https://example.com/me'),
                             ('phone', 'call me'), ('bio', 'x' * 301), ('graduation_year', 1800), ('work_type', 'office')]:
            response = self.client.put('/api/auth/profile', json=self.details(**{field: value}))
            self.assertEqual(response.status_code, 422, field)

    def test_blank_optional_fields_become_empty(self):
        data = self.client.put('/api/auth/profile', json=self.details(phone='', github_url='  ', academic_year='')).json()
        self.assertIsNone(data['profile']['phone'])
        self.assertIsNone(data['profile']['github_url'])
        self.assertIsNone(data['profile']['academic_year'])

    def test_untrusted_origin_cannot_write(self):
        response = self.client.put('/api/auth/profile', json=self.details(), headers={'Origin': 'https://evil.example'})
        self.assertEqual(response.status_code, 403)

    def test_consent_records_dates(self):
        given = self.client.put('/api/auth/profile/consent', json={'research_use': True}).json()['consent']
        self.assertTrue(given['research_use'])
        self.assertIsNotNone(given['given_at'])
        withdrawn = self.client.put('/api/auth/profile/consent', json={'research_use': False}).json()['consent']
        self.assertFalse(withdrawn['research_use'])
        self.assertIsNone(withdrawn['given_at'])
        self.assertIsNotNone(withdrawn['updated_at'])

    def test_cv_record_and_photo(self):
        cv = self.client.put('/api/auth/profile/cv', json={'file_name': 'my-cv.pdf'}).json()['cv']
        self.assertEqual(cv['file_name'], 'my-cv.pdf')
        self.assertEqual(self.client.put('/api/auth/profile/avatar', files={'file': ('a.png', PNG, 'image/png')}).status_code, 200)
        photo = self.client.get('/api/auth/profile/avatar')
        self.assertEqual(photo.headers['content-type'], 'image/png')
        self.assertEqual(self.client.put('/api/auth/profile/avatar', files={'file': ('a.gif', b'GIF89a', 'image/gif')}).status_code, 415)
        big = b'\xff\xd8\xff' + b'\x00' * (2 * 1024 * 1024)
        self.assertEqual(self.client.put('/api/auth/profile/avatar', files={'file': ('a.jpg', big, 'image/jpeg')}).status_code, 413)
        self.assertFalse(self.client.delete('/api/auth/profile/avatar').json()['avatar']['present'])

    def test_change_password(self):
        bad = self.client.post('/api/auth/password', json={'current_password': 'wrong', 'new_password': 'another long passphrase'})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post('/api/auth/password', json={'current_password': self.account['password'], 'new_password': 'another long passphrase'})
        self.assertEqual(ok.status_code, 204, ok.text)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)  # this device stays signed in
        self.client.post('/api/auth/logout', json={})
        relogin = self.client.post('/api/auth/login', json={**self.account, 'password': 'another long passphrase'})
        self.assertEqual(relogin.status_code, 200)

    def test_export_and_delete(self):
        self.client.put('/api/auth/profile', json=self.details())
        exported = self.client.get('/api/auth/profile/export').json()
        self.assertEqual(exported['profile']['degree'], 'BSc (Hons) in IT')
        self.assertEqual(self.client.post('/api/auth/profile/delete', json={'confirm': 'delete'}).status_code, 422)
        done = self.client.post('/api/auth/profile/delete', json={'confirm': 'DELETE'})
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(self.client.post('/api/auth/login', json=self.account).status_code, 401)


if __name__ == '__main__':
    unittest.main()
