import { expect, test } from '@playwright/test'
import { newUser, registerViaApi, submitLogin } from './helpers.js'

async function fillSignup(page, { full_name, email, password, confirm = password }) {
  await page.getByLabel('Full name', { exact: true }).fill(full_name)
  await page.getByLabel('Email address', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByLabel('Confirm password', { exact: true }).fill(confirm)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
}

test.describe('Signup', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register')
    await expect(page.getByRole('heading', { name: 'Start your journey.' })).toBeVisible()
  })

  test('creates an account, then the new user can log in', async ({ page }) => {
    const user = newUser('Grace Hopper')
    await fillSignup(page, user)

    await expect(page).toHaveURL('/login')
    await expect(page.getByRole('status')).toContainText('Your account is ready. Log in to begin.')
    await expect(page.getByLabel('Email address', { exact: true })).toHaveValue(user.email)

    await page.getByLabel('Password', { exact: true }).fill(user.password)
    await submitLogin(page)
    await expect(page).toHaveURL('/')
    await expect(page.getByLabel('Grace Hopper')).toHaveText('GH')
  })

  test('shows validation errors for an empty form', async ({ page }) => {
    await page.getByRole('button', { name: 'Create account', exact: true }).click()
    await expect(page.getByText('Please enter your full name.')).toBeVisible()
    await expect(page.getByText('Enter a valid email address.')).toBeVisible()
    await expect(page.getByText('Enter your password.')).toBeVisible()
    await expect(page).toHaveURL('/register')
  })

  test('rejects an invalid email address', async ({ page }) => {
    await fillSignup(page, { ...newUser(), email: 'not-an-email' })
    await expect(page.getByText('Enter a valid email address.')).toBeVisible()
    await expect(page).toHaveURL('/register')
  })

  test('requires a password of at least 12 characters', async ({ page }) => {
    await fillSignup(page, { ...newUser(), password: 'short pass' })
    await expect(page.getByText('Use at least 12 characters.', { exact: true })).toBeVisible()
    await expect(page).toHaveURL('/register')
  })

  test('requires matching passwords', async ({ page }) => {
    await fillSignup(page, { ...newUser(), confirm: 'a different passphrase' })
    await expect(page.getByText('Passwords do not match.')).toBeVisible()
    await expect(page).toHaveURL('/register')
  })

  test('rejects an email that already has an account', async ({ page, request }) => {
    const user = newUser()
    await registerViaApi(request, user)
    await fillSignup(page, user)
    await expect(page.getByRole('alert')).toHaveText('An account with this email already exists. Please log in.')
    await expect(page).toHaveURL('/register')
  })

  test('links between signup and login', async ({ page }) => {
    await page.getByText('Already have an account?').getByRole('link', { name: 'Log in' }).click()
    await expect(page).toHaveURL('/login')
    await page.getByRole('link', { name: 'Register now' }).click()
    await expect(page).toHaveURL('/register')
  })
})
