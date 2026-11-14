// Quick checks for the redesigned login page: Google still redirects, and the links still work.
import { expect, test } from '@playwright/test'

test('Continue with Google still redirects to Google sign-in', async ({ page }) => {
  // Stop at the sign-in provider instead of really signing in.
  await page.route(/\/auth\/v1\/authorize/, route => route.fulfill({ contentType: 'text/html', body: '<p>Google sign-in</p>' }))
  await page.goto('/login')
  await page.getByRole('button', { name: 'Continue with Google' }).click()
  await expect(page).toHaveURL(/\/auth\/v1\/authorize\?provider=google/)
})

test('Forgot password and Register links work, and the form slides between them', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('link', { name: 'Forgot password?' }).click()
  await expect(page).toHaveURL('/forgot-password')
  await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Welcome to CareerNova' })).toBeVisible() // brand panel stays
  await page.getByRole('link', { name: 'Back to login' }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
  await page.getByRole('link', { name: /Create an account/ }).click()
  await expect(page).toHaveURL('/register')
  await expect(page.getByRole('heading', { name: 'Start your journey.' })).toBeVisible()
})
