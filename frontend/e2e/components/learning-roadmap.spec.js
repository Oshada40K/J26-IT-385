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

async function fillForm(page, methods = ['Online courses', 'Hands-on projects']) {
  const skills = await skillGroups(page).all()
  expect(skills.length).toBeGreaterThan(0)
  for (const [index, skill] of skills.entries()) {
    // Mix real ratings with "Not studied" so both paths are submitted.
    await skill.getByRole('radio', index % 3 === 2 ? { name: 'Not studied' } : { name: /Moderately confident/ }).check()
  }
  for (const method of methods) await page.getByRole('checkbox', { name: method }).check()
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

  // Interactive exercises: a student who chose "Interactive coding exercises" gets them right after "How it works";
  // answers stay on the server until an attempt; a wrong check shows only "Not quite" until "Show answer".
  test('interactive exercises come right after "How it works" and are checked on the server', async ({ page }) => {
    await uploadCv(page)
    const career = await openForm(page)
    await fillForm(page, ['Interactive coding exercises'])
    await submitAndExpectRoadmap(page, career.name)
    await page.getByRole('tab', { name: 'Adaptive Roadmap', exact: true }).click()
    await expect(page.getByText('Loading your lessons…')).toHaveCount(0, { timeout: ANALYSIS_TIMEOUT })
    await page.locator('details.c4r-step').evaluateAll(steps => steps.forEach(step => { step.open = true }))
    const openLesson = page.getByRole('button', { name: 'Open lesson' })
    if (await openLesson.count() === 0) {
      const reason = `No curated lesson is open in the roadmap Component 03 decided for this CV (${career.name}); ` +
        'the exercise UI could not be reached, so this test was skipped (not passed).'
      console.log(`SKIPPED: ${reason}`)
      test.skip(true, reason)
    }
    const activity = page.waitForResponse(r => r.url().includes('/activity?') && r.request().method() === 'GET')
    await openLesson.first().click()
    const lesson = await (await activity).json()

    // The lesson JSON never carries the exercise answers, explanations or fixed lines.
    const exercisesSection = lesson.sections.find(s => s.kind === 'exercises')
    expect(exercisesSection, 'curated lessons have an exercises section').toBeTruthy()
    for (const exercise of exercisesSection.exercises) {
      expect(Object.keys(exercise).filter(k => ['answer', 'answers', 'explanation', 'fix'].includes(k))).toEqual([])
    }

    // Order and the personalisation note.
    await expect(page.getByText('Interactive practice first: you prefer interactive coding exercises.')).toBeVisible()
    await expect(page.getByText('Practical task first: you prefer hands-on learning.')).toHaveCount(0)
    const kinds = await page.locator('.c4l-lesson > .c4l-part').evaluateAll(parts =>   // parts without a kind (extra resources) are skipped
      parts.map(p => [...p.classList].find(c => c.startsWith('c4l-part-'))?.replace('c4l-part-', '')).filter(Boolean))
    expect(kinds.indexOf('exercises')).toBe(kinds.indexOf('explanation') + 1)
    const section = page.locator('.c4l-part-exercises')
    await expect(section.getByRole('heading', { name: /Practice: interactive exercises/ })).toBeVisible()
    await expect(section.locator('li.c4x')).toHaveCount(exercisesSection.exercises.length)

    // One exercise end to end: a deliberately wrong answer -> "Not quite" only -> hint -> show answer -> try again.
    const first = section.locator('li.c4x').first()
    const type = exercisesSection.exercises[0].type
    if (type === 'fill_blank') await first.getByLabel('Your answer for ____').fill('certainly not the answer')
    else if (type !== 'order_steps') await first.getByRole('radio').last().check()   // order_steps starts shuffled (never correct)
    const check = page.waitForResponse(r => r.url().includes('/exercises/check'))
    await first.getByRole('button', { name: 'Check' }).click()
    const checked = await (await check).json()
    console.log(`Exercises checked in lesson ${lesson.topic_id} (${exercisesSection.exercises.map(e => e.type).join(', ')}); ` +
      `first check correct=${checked.correct}, attempt ${checked.attempt_number}`)
    await expect(first.getByRole('status')).toContainText(checked.correct ? 'Correct!' : 'Not quite.')
    if (!checked.correct) {
      expect(checked.explanation).toBeUndefined()
      await expect(first.locator('.c4x-solution')).toHaveCount(0)
      await first.getByRole('button', { name: 'Show hint' }).click()
      await expect(first.locator('.c4x-hint')).toHaveText(`💡 ${exercisesSection.exercises[0].hint}`)
      await first.getByRole('button', { name: 'Show answer' }).click()
      await expect(first.getByRole('status')).toContainText('Here is the answer.')
    }
    await expect(first.locator('.c4x-solution')).toBeVisible()
    await first.getByRole('button', { name: 'Try again' }).click()
    await expect(first.getByRole('button', { name: 'Check' })).toBeVisible()

    // Keyboard: an order_steps line moves with the arrow buttons (Enter on a focused button).
    const order = section.locator('li.c4x').filter({ has: page.locator('.c4x-order') }).first()
    if (await order.count()) {
      const before = await order.locator('.c4x-order code').allInnerTexts()
      await order.getByRole('button', { name: 'Move line 2 up' }).focus()
      await page.keyboard.press('Enter')
      const after = await order.locator('.c4x-order code').allInnerTexts()
      expect(after.slice(0, 2)).toEqual([before[1], before[0]])
    }

    // 390 px wide, light and dark: no horizontal page scroll, and the exercise card follows the theme tokens.
    await page.setViewportSize({ width: 390, height: 844 })
    const backgrounds = []
    for (const theme of ['light', 'dark']) {
      await page.evaluate(t => { document.documentElement.dataset.theme = t }, theme)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow, `horizontal scroll in ${theme} theme at 390 px`).toBeLessThanOrEqual(0)
      backgrounds.push(await first.evaluate(el => getComputedStyle(el).backgroundColor))
    }
    expect(backgrounds[0]).not.toBe(backgrounds[1])
  })
})
