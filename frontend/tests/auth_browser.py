"""Optional real-browser auth QA; run against disposable local auth storage.

python tests/auth_browser.py http://127.0.0.1:5175
Requires the Python Playwright package and its Chromium browser.
"""
import sys
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright


def verify(base):
    screenshots = Path(__file__).resolve().parents[2] / 'backend' / '.data' / 'auth-qa'
    screenshots.mkdir(parents=True, exist_ok=True)
    email = f'qa-{uuid4().hex}@example.com'
    password = 'a unique browser test passphrase'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto(base + '/component03')
        expect(page).to_have_url(base + '/login')
        expect(page.get_by_role('heading', name='Welcome back.')).to_be_visible()
        page.screenshot(path=str(screenshots / 'login-desktop.png'), full_page=True, animations='disabled')
        page.get_by_role('button', name='Log in', exact=True).click()
        expect(page.get_by_text('Enter a valid email address.')).to_be_visible()
        page.get_by_role('link', name='Register now').click()
        page.get_by_label('Full name', exact=True).fill('QA Student')
        page.get_by_label('Email address', exact=True).fill(email)
        page.get_by_label('Password', exact=True).fill(password)
        page.get_by_label('Confirm password', exact=True).fill('does not match')
        page.get_by_role('button', name='Create account', exact=True).click()
        expect(page.get_by_text('Passwords do not match.')).to_be_visible()
        page.screenshot(path=str(screenshots / 'register-desktop.png'), full_page=True, animations='disabled')
        page.get_by_label('Confirm password', exact=True).fill(password)
        page.get_by_role('button', name='Create account', exact=True).click()
        expect(page).to_have_url(base + '/login')
        expect(page.get_by_role('status')).to_contain_text('Your account is ready')
        page.get_by_label('Password', exact=True).fill('incorrect password')
        page.get_by_role('button', name='Log in', exact=True).click()
        expect(page.get_by_role('alert')).to_have_text('Email or password is incorrect.')
        page.get_by_label('Password', exact=True).fill(password)
        page.get_by_role('button', name='Show password', exact=True).click()
        expect(page.get_by_label('Password', exact=True)).to_have_attribute('type', 'text')
        page.get_by_role('button', name='Hide password', exact=True).click()
        page.get_by_label('Remember me').check()
        page.get_by_role('button', name='Log in', exact=True).click()
        expect(page).to_have_url(base + '/')
        expect(page.get_by_role('heading', name='Big possibilities. Start with your CV.')).to_be_visible()
        cookie = next(c for c in context.cookies() if c['name'] == 'careernova_session')
        assert cookie['httpOnly'] and cookie['expires'] > 0
        assert 'careernova_session' not in page.evaluate('document.cookie')
        page.reload()
        expect(page.get_by_role('button', name='Log out')).to_be_visible()
        page.goto(base + '/component03')
        expect(page.get_by_role('heading', name='Find your direction. Understand why.')).to_be_visible()
        other_tab = context.new_page()
        other_tab.goto(base + '/')
        expect(other_tab.get_by_role('button', name='Log out')).to_be_visible()
        page.evaluate("sessionStorage.setItem('careernova-skill-session', JSON.stringify({candidate_id:'prior-user',access_token:'test-only'}))")
        page.get_by_role('button', name='Log out').click()
        expect(page).to_have_url(base + '/login')
        expect(other_tab).to_have_url(base + '/login')
        other_tab.close()
        assert page.evaluate("sessionStorage.getItem('careernova-skill-session')") is None
        page.goto(base + '/component04')
        expect(page).to_have_url(base + '/login')
        page.get_by_role('link', name='Forgot password?').click()
        page.get_by_label('Email address').fill(email)
        page.get_by_role('button', name='Send reset link').click()
        expect(page.get_by_role('alert')).to_contain_text('Password reset email is not configured')
        page.goto(base + '/login')
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(page.get_by_role('button', name='Log in', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(screenshots / 'login-mobile.png'), full_page=True, animations='disabled')
        page.goto(base + '/register')
        expect(page.get_by_role('button', name='Create account', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(screenshots / 'register-mobile.png'), full_page=True, animations='disabled')
        assert not errors, errors
        browser.close()
    print('PASS: protected navigation, validation, registration, login, remember me, reload, logout, reset availability, desktop and mobile layouts')
    print(f'Screenshots: {screenshots}')


if __name__ == '__main__':
    verify(sys.argv[1].rstrip('/'))
