"""Browser regression checks with Supabase HTTP responses mocked, not Google credentials.

Run: python tests/google_auth_browser.py http://localhost:5173
Uses frontend/.env.local to locate the configured Supabase project.
"""
import base64
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright


def verify(base):
    config = dotenv_values(Path(__file__).resolve().parents[1] / '.env.local')
    supabase = config['VITE_SUPABASE_URL'].rstrip('/')
    user = {
        'id': '8f725861-2910-45bc-959d-541ac8f010f1', 'email': 'google-test@example.com',
        'aud': 'authenticated', 'role': 'authenticated',
        'app_metadata': {'provider': 'google', 'providers': ['google']},
        'user_metadata': {'full_name': 'Google Test Student', 'avatar_url': 'https://avatar.example/student.png'},
        'created_at': '2026-01-01T00:00:00Z',
    }
    exchanges, authorizations, refreshes, legacy_requests = [], [], [], []
    logged_out = False

    def session():
        def encode(value):
            return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
        now = int(time.time())
        token = encode({'alg': 'HS256', 'typ': 'JWT'}) + '.' + encode({
            'sub': user['id'], 'aud': 'authenticated', 'exp': now + 3600, 'iat': now,
        }) + '.' + encode('mock-signature')
        return {'access_token': token, 'refresh_token': 'mock-refresh-token',
                'expires_in': 3600, 'expires_at': now + 3600, 'token_type': 'bearer', 'user': user}

    def upstream(route):
        nonlocal logged_out
        request = route.request
        parsed = urlparse(request.url)
        headers = {'access-control-allow-origin': base, 'access-control-allow-headers': '*'}
        if request.method == 'OPTIONS':
            route.fulfill(status=204, headers=headers); return
        if parsed.path.endswith('/authorize'):
            query = parse_qs(parsed.query)
            authorizations.append(query)
            assert query['provider'] == ['google']
            assert query['redirect_to'] == [base + '/auth/callback']
            assert query['code_challenge']
            assert query['code_challenge_method'][0].lower() == 's256'
            route.fulfill(status=302, headers={'location': base + '/auth/callback?code=mock-google-code'})
        elif parsed.path.endswith('/token'):
            body = request.post_data_json
            if parse_qs(parsed.query)['grant_type'] == ['pkce']:
                assert body['auth_code'] == 'mock-google-code'
                assert body['code_verifier']
                exchanges.append(body['auth_code'])
            else:
                refreshes.append(True)
            route.fulfill(status=200, json=session(), headers=headers)
        elif parsed.path.endswith('/user'):
            route.fulfill(status=401 if logged_out else 200, json={'message': 'Signed out'} if logged_out else user, headers=headers)
        elif parsed.path.endswith('/logout'):
            logged_out = True
            route.fulfill(status=204, headers=headers)
        else:
            raise AssertionError(f'Unexpected Supabase path: {parsed.path}')

    def legacy(route):
        legacy_requests.append(route.request.url)
        route.fulfill(status=503, json={'detail': 'Legacy backend unavailable'}, headers={'access-control-allow-origin': base, 'access-control-allow-credentials': 'true'})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.route(supabase + '/**', upstream)
        context.route('**/api/auth/**', legacy)
        context.route('https://avatar.example/**', lambda route: route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><circle cx="20" cy="20" r="20" fill="purple"/></svg>'))
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/component03')
        expect(page).to_have_url(base + '/login')
        page.get_by_role('button', name='Continue with Google').click()
        expect(page).to_have_url(base + '/', timeout=20000)
        expect(page.get_by_text(user['email'], exact=True)).to_be_visible()
        expect(page.get_by_role('img', name=user['user_metadata']['full_name'])).to_be_visible()
        assert len(authorizations) == 1
        assert len(exchanges) == 1, 'React StrictMode must not exchange the single-use code twice'
        page.reload()
        expect(page.get_by_text(user['email'], exact=True)).to_be_visible()
        # Expire the stored session to exercise the SDK refresh-token path.
        page.evaluate('''() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
            const session = JSON.parse(localStorage.getItem(key));
            session.expires_at = Math.floor(Date.now() / 1000) - 1;
            localStorage.setItem(key, JSON.stringify(session));
        }''')
        page.reload()
        expect(page.get_by_text(user['email'], exact=True)).to_be_visible()
        assert refreshes
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.evaluate("sessionStorage.setItem('careernova-skill-session', 'test-candidate')")
        legacy_count = len(legacy_requests)
        page.get_by_role('button', name='Log out').click()
        expect(page).to_have_url(base + '/login')
        assert logged_out
        assert page.evaluate("sessionStorage.getItem('careernova-skill-session')") is None
        page.goto(base + '/component03')
        expect(page).to_have_url(base + '/login')
        assert len(legacy_requests) == legacy_count, 'Google logout must not fall back to the legacy cookie'
        page.goto(base + '/auth/callback?error=access_denied&error_description=Google+login+cancelled')
        expect(page.get_by_role('alert')).to_contain_text('Google login cancelled')
        expect(page).to_have_url(base + '/auth/callback')
        page.get_by_role('link', name='Back to login').click()
        page.goto(base + '/auth/callback')
        expect(page.get_by_role('alert')).to_contain_text('No Google session was found')
        assert not errors, errors
        browser.close()
    print('PASS: Google PKCE redirect/callback, single code exchange, profile, reload, refresh token, logout, protected routes, mobile layout, cancelled/missing callback errors; Google consent mocked.')


if __name__ == '__main__':
    verify(sys.argv[1].rstrip('/'))
