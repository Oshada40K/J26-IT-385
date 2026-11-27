// Component 04: career readiness assessment, skill gap analysis and learning roadmap.
// The target career is decided by the system from Component 03's recommendation for the uploaded CV and shown
// read-only (career, C03 rank, match score and C03's top 5); the student cannot choose another career.
import { expect, test } from '@playwright/test'
import { ANALYSIS_TIMEOUT, uploadCv } from '../helpers.js'

const careerCard = page => page.getByRole('region', { name: 'Your target career' })
const topJobs = scope => scope.getByRole('list', { name: /Component 03's top 5 careers/ })
const skillGroups = page => page.locator('#c4-skills').getByRole('group')
const escape = text => text.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')
const TARGET_LINE = /^Your target career \(recommended by Component 03\): (.+) — rank (\d), match score (\d+\.\d)$/

// Opens the form for the uploaded CV and returns the career Component 03 decided, as shown on the card.
async function openForm(page) {
  await page.goto('/component04')
  await expect(page.getByRole('heading', { name: 'Career Readiness Assessment' })).toBeVisible()
  const line = careerCard(page).getByText(/^Your target career \(recommended by Component 03\):/)
  await expect(line).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  const [, name, rank, score] = (await line.innerText()).match(TARGET_LINE)
  await expect(page.getByRole('heading', { name: 'Skill Confidence Assessment' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
  return { name, rank: Number(rank), score }
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

// C03's five ranked careers, read-only, with exactly the target career highlighted.
async function expectTopFive(list, career) {
  const items = list.getByRole('listitem')
  await expect(items).toHaveCount(5)
  for (const [index, item] of (await items.all()).entries()) {
    await expect(item.locator('.rank-badge')).toHaveText(String(index + 1))
    await expect(item).toContainText(/Match score \d+\.\d/)
  }
  const selected = list.locator('[aria-current="true"]')
  await expect(selected).toHaveCount(1)
  await expect(selected.locator('strong')).toHaveText(career.name)
  await expect(selected.locator('.rank-badge')).toHaveText(String(career.rank))
  await expect(selected).toContainText(`Match score ${career.score}`)
  await expect(selected).toContainText('Your roadmap')
  await expect(list.getByRole('radio')).toHaveCount(0)
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
  await expect(page.getByRole('heading', { name: 'Career readiness score' })).toBeVisible()
  // The results are arranged in tabs: open each main section as a student would.
  for (const [tab, heading] of [['Skill Gap Overview', 'Skill gap analysis'], ['Priority Engine', 'Skill priorities'],
    ['Adaptive Roadmap', 'Adaptive learning roadmap'], ['Roadmap Dashboard', 'Career readiness score']]) {
    await page.getByRole('tab', { name: tab, exact: true }).click()
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
  }
  await expect(page.getByRole('alert')).toHaveCount(0)
}

test.describe('Component 04 - Learning roadmap', () => {
  // Every test except the first uploads a CV, and each upload runs Component 03's model, which serves one request
  // at a time. Run this file's tests one after another (each still independent) so uploads do not queue past the
  // analysis timeout.
  test.describe.configure({ mode: 'default' })

  test('without a CV there is no career to choose, only a link to Component 01', async ({ page }) => {
    await page.goto('/component04')
    await expect(page.getByRole('heading', { name: 'We could not set your target career' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expect(page.getByText(/Upload your CV in Component 01 first/)).toBeVisible()
    await expect(page.getByRole('link', { name: /Go to Component 01/ })).toBeVisible()
    await expect(page.getByRole('combobox')).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Skill Confidence Assessment' })).toHaveCount(0)
  })

  test('shows the Component 03 career read-only and loads its skills', async ({ page }) => {
    await uploadCv(page)
    const career = await openForm(page)
    const card = careerCard(page)
    // No way to choose: no dropdown and no radio buttons for careers.
    await expect(page.getByRole('combobox')).toHaveCount(0)
    await expect(card.getByRole('radio')).toHaveCount(0)
    await expectTopFive(topJobs(card), career)
    // C03's #1 is used when C4 covers it; otherwise the card explains the fallback to the highest supported job.
    const fallback = card.getByText(/^Component 03's #1 is .+, which is outside the IT roadmap, so your roadmap uses #\d .+\.$/)
    if (career.rank === 1) await expect(fallback).toHaveCount(0)
    else {
      await expect(fallback).toContainText(`so your roadmap uses #${career.rank} ${career.name}.`)
      const above = topJobs(card).getByRole('listitem').filter({ hasNot: page.locator('[aria-current="true"]') })
      for (let rank = 1; rank < career.rank; rank++) {
        await expect(above.nth(rank - 1)).toContainText('Not covered by the IT roadmap')
      }
    }
    await expect(card.getByText(/skills found in your CV\./)).toBeVisible()
    await expect(page.getByText(new RegExp(`\\d+ key skills for ${escape(career.name)}`))).toBeVisible()
    await expect(page.locator('#c4-skills').getByText('In your CV').first()).toBeVisible()
    await expect(page.getByText('0% complete')).toBeVisible()
  })

  test('highlights every unanswered field on an empty submission', async ({ page }) => {
    await uploadCv(page)
    await openForm(page)
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText(/Please complete \d+ required fields before submitting\./)).toBeVisible()
    await expect(page.getByText('Select at least one learning method.')).toBeVisible()
    await expect(page.getByText('Select how many hours per week you can dedicate to learning.')).toBeVisible()
    await expect(page.getByText('Enter a number. Use 0 if you have none.')).toHaveCount(3)
    await expect(page.getByRole('heading', { name: 'Your learning roadmap' })).toHaveCount(0)
  })

  test('asks for a description when "Other" learning method is chosen', async ({ page }) => {
    await uploadCv(page)
    await openForm(page)
    await fillForm(page)
    await page.getByRole('checkbox', { name: 'Other' }).check()
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText('Describe your other learning method.')).toBeVisible()
    await page.getByLabel('Please describe your other learning method').fill('Mentoring')
    await expect(page.getByText('Describe your other learning method.')).toHaveCount(0)
  })

  test('rejects experience counts above 1000', async ({ page }) => {
    await uploadCv(page)
    await openForm(page)
    await fillForm(page)
    await page.getByLabel(/relevant projects/).fill('1001')
    await page.getByRole('button', { name: 'Submit Assessment' }).click()
    await expect(page.getByText('Enter a number of 1000 or less.')).toBeVisible()
  })

  test('builds a roadmap for the Component 03 career and shows it on return', async ({ page }) => {
    await uploadCv(page)
    const career = await openForm(page)
    await fillForm(page)
    await submitAndExpectRoadmap(page, career.name)

    // The results header shows where the career came from; there is no way to choose another one.
    const header = page.locator('.c4r-overview')
    await expect(header.getByText(`Recommended by Component 03 — rank ${career.rank}, match score ${career.score}`)).toBeVisible()
    await expectTopFive(topJobs(header), career)
    await expect(page.getByRole('button', { name: 'Choose another career' })).toHaveCount(0)
    await expect(page.getByText(/Component 03 now recommends/)).toHaveCount(0)    // same CV: the career has not changed

    await page.reload()
    await expect(page.getByRole('heading', { name: 'Your learning roadmap' })).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expectAnalysis(page, career.name)

    // Updating starts from the previous answers, for the same Component 03 career.
    await page.getByRole('button', { name: 'Update my assessment' }).click()
    await expect(page.getByText('100% complete')).toBeVisible({ timeout: ANALYSIS_TIMEOUT })
    await expect(careerCard(page).getByText(`${career.name} — rank ${career.rank}, match score ${career.score}`)).toBeVisible()
    await expect(page.getByRole('combobox')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Back to my results' })).toBeVisible()
  })
})
