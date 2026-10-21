import { expect, test as setup } from '@playwright/test'
import { AUTH_STATE, logIn, newUser, registerViaApi } from './helpers.js'

setup('log in a shared component-test user', async ({ page, request }) => {
  const user = newUser('Component Tester')
  await registerViaApi(request, user)
  await logIn(page, user)
  await expect(page).toHaveURL('/')
  await page.context().storageState({ path: AUTH_STATE })
})
