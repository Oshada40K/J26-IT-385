// Component 02: personality analysis (questionnaire, writing, scenarios, fused profile).
import { expect, test } from '@playwright/test'

const TRAITS = ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Neuroticism']
// The first text analysis loads a language model on the backend (about a minute when cold).
const TEXT_MODEL_TIMEOUT = 150_000

const ANSWERS = {
  problem: 'I break a difficult problem into smaller parts, research each part carefully, try a simple version first and then test my ideas step by step until the solution works.',
  team: 'In a team I usually organise the tasks, keep everyone informed about progress, and help teammates who are stuck so that we finish the project together on time.',
  challenge: 'When our demo failed the day before the deadline I stayed calm, found the bug with my teammate, and we wrote down what went wrong so it would not happen again.',
  learning: 'I like to learn something new by reading the official documentation, watching a short tutorial and then building a small hands-on project to practise what I learned.',
}

const stage = (page, name) => page.getByRole('navigation', { name: 'Assessment stages' }).getByRole('button', { name: new RegExp(name) })

// Varied answers: the backend flags identical answers to every statement as unreliable.
const CYCLE = ['Agree', 'Neutral', 'Disagree', 'Strongly agree']

// Answers every statement on the visible page. Attention checks ask for a specific
// answer; failing one picks a different option on purpose.
async function answerQuestionnairePage(page, { passAttentionChecks = true } = {}) {
  const groups = page.locator('form').getByRole('group')
  await expect(groups.first()).toBeVisible() // the questionnaire loads from the API
  for (const [index, item] of (await groups.all()).entries()) {
    const instruction = /please select "([^"]+)"/.exec(await item.innerText())?.[1]
    const answer = !instruction ? CYCLE[index % CYCLE.length]
      : passAttentionChecks ? instruction : (instruction === 'Neutral' ? 'Agree' : 'Neutral')
    await item.getByRole('radio', { name: answer, exact: true }).check()
  }
}

async function completeQuestionnaire(page, options) {
  await page.goto('/component02')
  await expect(page.getByRole('heading', { name: 'Big Five questionnaire' })).toBeVisible()
  for (;;) {
    await answerQuestionnairePage(page, options)
    const next = page.getByRole('button', { name: 'Next page' })
    if (!await next.isVisible()) break
    await next.click()
  }
  await page.getByRole('button', { name: 'Score my answers' }).click()
}

async function completeScenarios(page) {
  await stage(page, 'Situational judgement').click()
  const scenarios = page.locator('form').getByRole('group')
  await expect(scenarios.first()).toBeVisible()
  for (const scenario of await scenarios.all()) await scenario.getByRole('radio').first().check()
  await page.getByRole('button', { name: 'Score my choices' }).click()
}

async function completeWriting(page) {
  await stage(page, 'Behavioural answers').click()
  await page.getByRole('textbox', { name: /Problem solving/ }).fill(ANSWERS.problem)
  await page.getByRole('textbox', { name: /Teamwork/ }).fill(ANSWERS.team)
  await page.getByRole('textbox', { name: /Handling challenges/ }).fill(ANSWERS.challenge)
  await page.getByRole('textbox', { name: /Learning style/ }).fill(ANSWERS.learning)
  await page.getByRole('button', { name: 'Analyse my answers' }).click()
}

async function expectMeters(page, source) {
  for (const trait of TRAITS) {
    await expect(page.getByRole('meter', { name: new RegExp(`^${trait} from ${source}`) })).toBeVisible()
  }
}

test.describe('Component 02 - Personality analysis', () => {
  test('keeps the final profile locked until a part is complete', async ({ page }) => {
    await page.goto('/component02')
    await expect(page.getByRole('heading', { name: 'Discover your work personality' })).toBeVisible()
    await expect(stage(page, 'Your profile')).toBeDisabled()
    await expect(page.getByText('Complete any of the three parts')).toBeVisible()
  })

  test('requires every statement on a questionnaire page before moving on', async ({ page }) => {
    await page.goto('/component02')
    await expect(page.getByText('Page 1 of 4 · 0 of 52 answered')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
    await answerQuestionnairePage(page)
    await expect(page.getByText('Page 1 of 4 · 13 of 52 answered')).toBeVisible()
    await page.getByRole('button', { name: 'Next page' }).click()
    await expect(page.getByText('Page 2 of 4')).toBeVisible()
  })

  test('scores the completed questionnaire into Big Five traits', async ({ page }) => {
    await completeQuestionnaire(page)
    await expectMeters(page, 'questionnaire')
    await expect(page.getByText('1 of 3 parts complete.')).toBeVisible()
    await expect(stage(page, 'Big Five questionnaire')).toContainText('Done')
    await expect(page.getByRole('alert')).toHaveCount(0)
  })

  test('warns when an attention check is answered incorrectly', async ({ page }) => {
    await completeQuestionnaire(page, { passAttentionChecks: false })
    await expectMeters(page, 'questionnaire')
    await expect(page.getByRole('alert')).toHaveText('An attention check was not answered as instructed, so these answers may be careless.')
  })

  test('keeps questionnaire answers after a page reload', async ({ page }) => {
    await page.goto('/component02')
    await answerQuestionnairePage(page)
    await page.reload()
    await expect(page.getByText('13 of 52 answered')).toBeVisible()
  })

  test('scores the situational judgement scenarios', async ({ page }) => {
    await page.goto('/component02')
    await completeScenarios(page)
    await expectMeters(page, 'scenario choices')
    await expect(stage(page, 'Situational judgement')).toContainText('Done')
  })

  test('requires at least 20 words before analysing writing', async ({ page }) => {
    await page.goto('/component02')
    await stage(page, 'Behavioural answers').click()
    await page.getByRole('textbox', { name: /Problem solving/ }).fill('I plan carefully.')
    await expect(page.getByText('3 words in total · at least 20 needed')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Analyse my answers' })).toBeDisabled()
  })

  test('analyses written answers', async ({ page }) => {
    test.setTimeout(TEXT_MODEL_TIMEOUT + 60_000)
    await page.goto('/component02')
    await completeWriting(page)
    await expect(page.getByRole('meter', { name: /^Openness from writing/ })).toBeVisible({ timeout: TEXT_MODEL_TIMEOUT })
    await expectMeters(page, 'writing')
  })

  test('combines all three parts into a profile with a consistency score', async ({ page }) => {
    test.setTimeout(2 * TEXT_MODEL_TIMEOUT + 60_000)
    await completeQuestionnaire(page)
    await expectMeters(page, 'questionnaire')
    await completeScenarios(page)
    await expectMeters(page, 'scenario choices')
    await completeWriting(page)
    await expect(page.getByRole('meter', { name: /^Openness from writing/ })).toBeVisible({ timeout: TEXT_MODEL_TIMEOUT })

    await expect(page.getByText('All three parts are complete.')).toBeVisible()
    await page.getByRole('button', { name: 'See my combined profile' }).click()

    await expect(page.getByText('PERSONALITY CONSISTENCY SCORE')).toBeVisible({ timeout: TEXT_MODEL_TIMEOUT })
    await expect(page.locator('.personality-pcs-score strong')).toHaveText(/^\d{1,3}$/)
    await expect(page.locator('.personality-band')).toHaveText(/^(High|Moderate|Low)$/)
    await expect(page.getByText('Based on')).toBeVisible()
    for (const trait of TRAITS) {
      await expect(page.getByRole('meter', { name: new RegExp(`^${trait} combined: \\d+ out of 100$`) })).toBeVisible()
    }
  })
})
