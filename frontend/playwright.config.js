// End-to-end tests. Starts an isolated backend + Vite pair so test accounts, CV
// assessments and rate-limit counters never touch the developer's local or live data.
import { randomBytes } from 'node:crypto'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig, devices } from '@playwright/test'
import { API_URL, APP_URL, AUTH_STATE } from './e2e/helpers.js'

// Workers re-evaluate this file; set once in the main process so they inherit it.
process.env.E2E_DATA_DIR ??= mkdtempSync(join(tmpdir(), 'careernova-e2e-'))
process.env.E2E_AUTH_SECRET ??= randomBytes(48).toString('base64url')
const data = process.env.E2E_DATA_DIR

const python = process.env.E2E_PYTHON
  ?? (process.platform === 'win32' ? 'venv\\Scripts\\python.exe' : 'venv/bin/python')

export default defineConfig({
  testDir: './e2e',
  globalTeardown: './e2e/teardown.js',
  // Leaves room for ANALYSIS_TIMEOUT (90s) waits on cold ML endpoints.
  timeout: 120_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: APP_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'auth', testMatch: /(login|signup)\.spec\.js/, use: { ...devices['Desktop Chrome'] } },
    // Logs in once; component tests reuse the session (login is rate limited per IP).
    { name: 'setup', testMatch: /auth\.setup\.js/, use: { ...devices['Desktop Chrome'] } },
    {
      name: 'components',
      testMatch: /components\/.*\.spec\.js/,
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'], storageState: AUTH_STATE },
    },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port ${new URL(API_URL).port}`,
      cwd: '../backend',
      url: `${API_URL}/health`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        AUTH_DATABASE_PATH: join(data, 'auth.sqlite3'),
        SKILL_DATABASE_PATH: join(data, 'skills.sqlite3'),
        C4_DATABASE_PATH: join(data, 'component04.sqlite3'),
        C4_EVIDENCE_DIR: join(data, 'component04_evidence'),
        // Component 03 fetches profiles over HTTP; without this it calls port 8000.
        CAREER_UPSTREAM_BASE_URL: API_URL,
        AUTH_SECRET_KEY: process.env.E2E_AUTH_SECRET,
        AUTH_ALLOWED_ORIGINS: APP_URL,
        AUTH_COOKIE_SECURE: 'false',
        AUTH_COOKIE_SAMESITE: 'lax',
        AUTH_FRONTEND_URL: APP_URL,
        SKILL_ENABLE_SBERT: 'false',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${new URL(APP_URL).port} --strictPort`,
      url: APP_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      // Overrides .env / .env.local so the app can never point at the live backend.
      env: { VITE_API_BASE_URL: API_URL },
    },
  ],
})
