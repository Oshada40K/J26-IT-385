import { expect, test } from '@playwright/test'
import { logIn, newUser, registerViaApi } from './helpers.js'

test.describe('Login', () => {
  let user

  test.beforeEach(async ({ request }) => {
    user = newUser('Ada Lovelace')
    await registerViaApi(request, user)
  })

  test('redirects an anonymous visitor from a protected page to login', async ({ page }) => {
    await page.goto('/component03')
    await expect(page).toHaveURL('/login')
    await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
  })

  test('shows validation errors for an empty form', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'Log in', exact: true }).click()
    await expect(page.getByText('Enter a valid email address.')).toBeVisible()
    await expect(page.getByText('Enter your password.')).toBeVisible()
    await expect(page).toHaveURL('/login')
  })

  test('rejects an incorrect password', async ({ page }) => {
    await logIn(page, { email: user.email, password: 'definitely the wrong one' })
    await expect(page.getByRole('alert')).toHaveText('Email or password is incorrect.')
    await expect(page).toHaveURL('/login')
  })

  test('rejects an email with no account', async ({ page }) => {
    await logIn(page, { email: newUser().email, password: user.password })
    await expect(page.getByRole('alert')).toHaveText('Email or password is incorrect.')
  })

  test('logs in, lands on the dashboard and keeps the session across reloads', async ({ page }) => {
    await logIn(page, user)
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: /Big possibilities/ })).toBeVisible()
    await expect(page.getByLabel('Ada Lovelace')).toHaveText('AL')

    await page.reload()
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible()

    await page.goto('/component03')
    await expect(page).toHaveURL('/component03')
  })

  test('treats the email as case-insensitive', async ({ page }) => {
    await logIn(page, { email: user.email.toUpperCase(), password: user.password })
    await expect(page).toHaveURL('/')
  })

  test('redirects a logged-in user away from the login page', async ({ page }) => {
    await logIn(page, user)
    await expect(page).toHaveURL('/')
    await page.goto('/login')
    await expect(page).toHaveURL('/')
  })

  test('logs out and protects the dashboard again', async ({ page }) => {
    await logIn(page, user)
    await page.getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL('/login')

    await page.goto('/component04')
    await expect(page).toHaveURL('/login')
  })

  test('toggles password visibility', async ({ page }) => {
    await page.goto('/login')
    const password = page.getByLabel('Password', { exact: true })
    await expect(password).toHaveAttribute('type', 'password')
    await page.getByRole('button', { name: 'Show password' }).click()
    await expect(password).toHaveAttribute('type', 'text')
    await page.getByRole('button', { name: 'Hide password' }).click()
    await expect(password).toHaveAttribute('type', 'password')
  })
})
