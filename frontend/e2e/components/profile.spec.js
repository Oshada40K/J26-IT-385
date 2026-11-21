// /profile: opens from the account menu, saves details with inline validation, links to modules.
import { expect, test } from '@playwright/test'

test.describe('Profile page', () => {
  test('opens from the account menu and shows the real journey', async ({ page }) => {
    await page.goto('/')
    await page.locator('.account-trigger').click()
    await page.getByRole('link', { name: 'My profile', exact: true }).click()
    await expect(page).toHaveURL('/profile')
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^Component Tester/)
    await expect(page.getByText(/^Member since \d/)).toBeVisible() // recorded at registration
    await expect(page.getByRole('tab')).toHaveCount(4)
    await expect(page.getByRole('img', { name: /^Profile \d+% complete$/ })).toBeVisible()

    // Module links go to the right pages, and empty modules offer a start button.
    const steps = page.locator('.pf-steps a')
    await expect(steps).toHaveCount(4)
    for (const [index, path] of ['/component01', '/component02', '/component03', '/component04'].entries()) {
      await expect(steps.nth(index)).toHaveAttribute('href', path)
    }
    await expect(page.getByRole('link', { name: 'Start skill assessment' })).toHaveAttribute('href', '/component01')
    await steps.nth(3).click()
    await expect(page).toHaveURL('/component04')
  })

  test('edits and saves details with inline validation', async ({ page }) => {
    await page.goto('/profile?tab=edit')
    const university = `Test University ${Date.now()}`
    await page.getByLabel('University').fill(university)
    await page.getByLabel('Academic year').selectOption('Year 4')
    await page.getByRole('button', { name: 'Data Science', exact: true }).click()
    await page.getByRole('radio', { name: 'Hybrid' }).click()
    await expect(page.getByText('You have unsaved changes')).toBeVisible()

    await page.getByLabel('GitHub URL').fill('github.com/tester')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText('Use a link like https://github.com/your-username')).toBeVisible()
    await page.getByLabel('GitHub URL').fill('https://github.com/tester')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText('Your details have been saved.')).toBeVisible()

    await page.reload()
    await expect(page.getByLabel('University')).toHaveValue(university)
    await expect(page.getByRole('button', { name: 'Data Science', exact: true })).toHaveAttribute('aria-pressed', 'true')
    await page.getByRole('tab', { name: 'Overview' }).click()
    await expect(page.locator('.pf-role')).toContainText(university)
  })
})
