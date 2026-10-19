// Component 03: explainable career recommendation.
import { expect, test } from '@playwright/test'
import { ANALYSIS_TIMEOUT, candidateId, uploadCv } from '../helpers.js'

function section(page, title) {
  return page.locator('.api-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) })
}

async function expectRecommendations(page, expectedCandidate) {
  await expect(section(page, 'Best Job').locator('.best-job-name')).not.toBeEmpty({ timeout: ANALYSIS_TIMEOUT })
  const rows = section(page, 'Top 5 Jobs').locator('tbody tr')
  await expect(rows).toHaveCount(5, { timeout: ANALYSIS_TIMEOUT })
  // The best job is ranked first in the top five.
  const best = await section(page, 'Best Job').locator('.best-job-name').innerText()
  await expect(rows.first().locator('td').nth(1)).toHaveText(best)
  await expect(section(page, 'Explanation').getByRole('listitem').first()).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  const info = section(page, 'Model information')
  await expect(info.getByText(expectedCandidate, { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
}

test.describe('Component 03 - Career recommendation', () => {
  test('loads sample recommendations when no CV has been uploaded', async ({ page }) => {
    await page.goto('/component03')
    await expect(page.getByRole('heading', { name: 'Find your direction. Understand why.' })).toBeVisible()
    await expect(page.getByText('Showing sample recommendations.')).toBeVisible()

    await page.getByRole('button', { name: 'Load all recommendations' }).click()
    await expectRecommendations(page, 'sample_candidate_001')
  })

  test('shows recommendations for the uploaded CV straight after analysis', async ({ page }) => {
    await uploadCv(page)
    await expect(page.getByText('Recommendations use your CV skills')).toBeVisible()
    await expectRecommendations(page, await candidateId(page))
  })

  test('reloads a single section on demand', async ({ page }) => {
    await page.goto('/component03')
    const topJobs = section(page, 'Top 5 Jobs')
    await topJobs.getByRole('button', { name: 'Load' }).click()
    await expect(topJobs.locator('tbody tr')).toHaveCount(5, { timeout: ANALYSIS_TIMEOUT })
    await expect(section(page, 'Best Job').locator('.best-job-name')).toHaveCount(0)

    await topJobs.getByRole('button', { name: 'Reload' }).click()
    await expect(topJobs.locator('tbody tr')).toHaveCount(5, { timeout: ANALYSIS_TIMEOUT })
  })
})
