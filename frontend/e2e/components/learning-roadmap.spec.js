// Component 04: career readiness assessment, skill gap analysis and learning roadmap.
import { expect, test } from '@playwright/test'
import { ANALYSIS_TIMEOUT, uploadCv } from '../helpers.js'

const careerSelect = page => page.getByRole('combobox', { name: /target career|another IT career/ })
const skillGroups = page => page.locator('#c4-skills').getByRole('group')

async function openForm(page) {
  await page.goto('/component04')
  await expect(page.getByRole('heading', { name: 'Career Readiness Assessment' })).toBeVisible()
  await expect(careerSelect(page)).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
}

async function chooseFirstCareer(page) {
  const name = await careerSelect(page).locator('option:not([disabled])').first().innerText()
  await careerSelect(page).selectOption({ label: name })
  await expect(page.getByRole('heading', { name: 'Skill Confidence Assessment' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  return name
}

async function fillForm(page) {
  const skills = await skillGroups(page).all()
  expect(skills.length).toBeGreaterThan(0)
  for (const [index, skill] of skills.entries()) {
    // Mix real ratings with "Not studied" so both paths are submitted.
    await skill.getByRole('radio', index % 3 === 2 ? { name: 'Not studied' } : { name: /Moderately confident/ }).check()
  }
  await page.getByRole('checkbox', { name: 'Online courses' }).check()
  await page.getByRole('checkbox', { name: 'Hands-on projects' }).check()
  await page.getByRole('radio', { name: '4–6 hours' }).check()
  await page.getByLabel(/relevant projects/).fill('2')
  await page.getByLabel(/professional certifications/).fill('0')
  await page.getByLabel(/relevant internships/).fill('1')
  await expect(page.getByText('100% complete')).toBeVisible()
}

// The analysis either renders for the career or shows an error card; fail fast with its text.
async function expectAnalysis(page, careerName) {
  const career = page.getByRole('heading', { name: careerName, exact: true })
  await expect(career.or(page.getByRole('alert')).first()).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  expect(await page.getByRole('alert').allInnerTexts(), 'roadmap analysis errors').toEqual([])
  await expect(career).toBeVisible()
}

async function submitAndExpectRoadmap(page, careerName) {
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByRole('heading', { name: 'Your learning roadmap' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  await expectAnalysis(page, careerName)
  await expect(page.getByRole('img', { name: /^Readiness score \d+ out of 100$/ })).toBeVisible()
  for (const heading of ['Career readiness score', 'Skill gap analysis', 'Skill priorities', 'Personalised learning roadmap']) {
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
  }
  await expect(page.getByRole('alert')).toHaveCount(0)
}

test.describe('Component 04 - Learning roadmap', () => {
  test('lists supported careers and loads skills for the chosen one', async ({ page }) => {
    await openForm(page)
    // No assertion on the empty state: even without a CV, the best match from
    // Component 03's sample recommendations is preselected.
    const career = await chooseFirstCareer(page)
    await expect(page.getByText(new RegExp(`\\d+ key skills for ${career}`))).toBeVisible()
    await expect(page.getByText('0% complete')).toBeVisible()
  })

  test('highlights every unanswered field on an empty submission', async ({ page }) => {
    await openForm(page)
    await chooseFirstCareer(page)
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText(/Please complete \d+ required fields before submitting\./)).toBeVisible()
    await expect(page.getByText('Select at least one learning method.')).toBeVisible()
    await expect(page.getByText('Select how many hours per week you can dedicate to learning.')).toBeVisible()
    await expect(page.getByText('Enter a number. Use 0 if you have none.')).toHaveCount(3)
    await expect(page.getByRole('heading', { name: 'Your learning roadmap' })).toHaveCount(0)
  })

  test('asks for a description when "Other" learning method is chosen', async ({ page }) => {
    await openForm(page)
    await chooseFirstCareer(page)
    await fillForm(page)
    await page.getByRole('checkbox', { name: 'Other' }).check()
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText('Describe your other learning method.')).toBeVisible()
    await page.getByLabel('Please describe your other learning method').fill('Mentoring')
    await expect(page.getByText('Describe your other learning method.')).toHaveCount(0)
  })

  test('rejects experience counts above 1000', async ({ page }) => {
    await openForm(page)
    await chooseFirstCareer(page)
    await fillForm(page)
    await page.getByLabel(/relevant projects/).fill('1001')
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText('Enter a number of 1000 or less.')).toBeVisible()
  })

  test('builds a roadmap from a completed assessment and shows it on return', async ({ page }) => {
    await openForm(page)
    const career = await chooseFirstCareer(page)
    await fillForm(page)
    await submitAndExpectRoadmap(page, career)

    await page.reload()
    await expect(page.getByRole('heading', { name: 'Your learning roadmap' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expectAnalysis(page, career)

    // Updating starts from the previous answers.
    await page.getByRole('button', { name: 'Update my assessment' }).click()
    await expect(page.getByText('100% complete')).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expect(page.getByRole('button', { name: 'Back to my results' })).toBeVisible()
  })

  test('uses the uploaded CV and Component 03 matches', async ({ page }) => {
    await uploadCv(page)
    await openForm(page)
    await expect(page.getByRole('radiogroup', { name: 'Component 03 career matches' })).toBeVisible()
    await expect(page.getByText(/skills found in your CV\./)).toBeVisible()
    // The best supported match is preselected, so its skills load straight away.
    await expect(page.getByRole('heading', { name: 'Skill Confidence Assessment' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expect(page.locator('#c4-skills').getByText('In your CV').first()).toBeVisible()

    const career = await page.getByRole('radiogroup', { name: 'Component 03 career matches' })
      .locator('label').filter({ has: page.getByRole('radio', { checked: true }) }).locator('strong').innerText()
    await fillForm(page)
    await submitAndExpectRoadmap(page, career)
  })
})
