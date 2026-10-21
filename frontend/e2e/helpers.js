import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { expect } from '@playwright/test'

// Same host as the API so the SameSite=Lax session cookie is sent.
export const APP_URL = 'http://127.0.0.1:5175'
export const API_URL = 'http://127.0.0.1:8010'
export const PASSWORD = 'a long enough test passphrase'
export const AUTH_STATE = fileURLToPath(new URL('../playwright/.auth/user.json', import.meta.url))
export const fixture = name => fileURLToPath(new URL(`./fixtures/${name}`, import.meta.url))

// CV parsing plus career inference runs on the backend; allow for a cold start.
export const ANALYSIS_TIMEOUT = 90_000

// Upload a CV from Home; the app assesses it (C01), then predicts careers (C03).
export async function uploadCv(page, name = 'sample-cv.docx') {
  await page.goto('/')
  await page.getByLabel('Choose your CV').setInputFiles(fixture(name))
  await page.getByRole('button', { name: 'Analyze my CV' }).click()
  await expect(page).toHaveURL('/component03', { timeout: ANALYSIS_TIMEOUT })
}

export const candidateId = page =>
  page.evaluate(() => JSON.parse(sessionStorage.getItem('careernova-skill-session'))?.candidate_id)

export function newUser(name = 'Test Student') {
  return { full_name: name, email: `e2e-${randomUUID()}@example.com`, password: PASSWORD }
}

export async function registerViaApi(request, user) {
  const response = await request.post(`${API_URL}/api/auth/register`, {
    headers: { Origin: APP_URL },
    data: user,
  })
  expect(response.status(), await response.text()).toBe(201)
}

// Login makes two API calls and then routes, which can exceed the default 5s
// expect timeout on a cold backend. Wait until it settles either way.
export const LOGIN_TIMEOUT = 20_000

export async function submitLogin(page) {
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page.getByRole('alert').or(page.getByRole('button', { name: 'Log out' })).first())
    .toBeVisible({ timeout: LOGIN_TIMEOUT })
}

export async function logIn(page, { email, password }) {
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await submitLogin(page)
}
