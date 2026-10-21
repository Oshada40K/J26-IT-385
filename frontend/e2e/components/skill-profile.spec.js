// Component 01: technical skill assessment from an uploaded CV.
import { expect, test } from '@playwright/test'
import { fixture, uploadCv } from '../helpers.js'

// Skills written into the fixture CVs (see e2e/fixtures).
const CV_SKILLS = ['CSS', 'Git', 'HTML', 'JavaScript', 'Python', 'React', 'SQL']

test.describe('Component 01 - Skill assessment', () => {
  test('asks for a CV before any assessment exists', async ({ page }) => {
    await page.goto('/component01')
    await expect(page.getByRole('heading', { name: 'Your technical strengths' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Start with your CV' })).toBeVisible()
    await page.getByRole('link', { name: 'Choose your CV' }).click()
    await expect(page).toHaveURL('/')
  })

  test('rejects a file that is not a PDF or DOCX', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Choose your CV').setInputFiles({ name: 'cv.txt', mimeType: 'text/plain', buffer: Buffer.from('Python') })
    await expect(page.getByRole('alert')).toHaveText('Please choose a PDF or DOCX file.')
    await expect(page.getByRole('button', { name: 'Analyze my CV' })).toHaveCount(0)
  })

  test('lets the student remove a selected CV', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Choose your CV').setInputFiles(fixture('sample-cv.pdf'))
    await expect(page.getByText('sample-cv.pdf')).toBeVisible()
    await page.getByRole('button', { name: 'Remove selected CV' }).click()
    await expect(page.getByText('sample-cv.pdf')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Analyze my CV' })).toHaveCount(0)
  })

  for (const file of ['sample-cv.docx', 'sample-cv.pdf']) {
    test(`assesses skills from a ${file.split('.').pop().toUpperCase()} CV`, async ({ page }) => {
      await uploadCv(page, file)
      await page.goto('/component01')

      await expect(page.getByText('Assessment complete')).toBeVisible()
      await expect(page.getByText(/\d+ technical skills identified/)).toBeVisible()
      for (const skill of CV_SKILLS) {
        await expect(page.getByRole('heading', { name: skill, exact: true })).toBeVisible()
      }

      const python = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Python', exact: true }) })
      await expect(python.getByText(/^[1-5]\/ 5 estimated$/)).toBeVisible()
      await python.getByText(/View CV evidence \(\d+\)/).click()
      await expect(python.locator('blockquote').first()).toContainText('Python')
    })
  }
})
