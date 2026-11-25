import { expect, test } from '@playwright/test'

const unique = () => Math.random().toString(36).slice(2, 8)

test.describe('critical user journey', () => {
  test('register → create task → complete it → see it on the dashboard → sign out', async ({ page }) => {
    const email = `e2e-${unique()}@example.com`

    await page.goto('/register')
    await page.getByLabel('Full name').fill('E2E Tester')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('E2eTest!Pass1')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('E2E Tester')).toBeVisible()

    await page.getByRole('link', { name: 'Tasks' }).click()
    await page.getByRole('button', { name: '+ New task' }).click()
    const form = page.getByRole('form', { name: 'Task form' })
    await form.getByLabel('Title').fill('Ship blue-green release')
    await form.getByLabel('Priority').selectOption('high')
    await form.getByRole('button', { name: 'Save task' }).click()

    const card = page.locator('article.task', { hasText: 'Ship blue-green release' })
    await expect(card).toBeVisible()

    // todo -> in_progress -> done
    const advance = card.getByRole('button', { name: /Advance status/ })
    await advance.click()
    await expect(card.getByText('In progress', { exact: true })).toBeVisible()
    await advance.click()
    await expect(card.getByText('Done', { exact: true })).toBeVisible()

    await page.getByRole('link', { name: 'Dashboard' }).click()
    await expect(page.getByText('100%')).toBeVisible()

    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  })

  test('rejects weak passwords client-side', async ({ page }) => {
    await page.goto('/register')
    await page.getByLabel('Full name').fill('Weak')
    await page.getByLabel('Email').fill(`weak-${unique()}@example.com`)
    await page.getByLabel('Password').fill('weak')
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByText('At least 8 characters')).toBeVisible()
  })

  test('protected routes redirect to login', async ({ page }) => {
    await page.goto('/tasks')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('serves security headers', async ({ request }) => {
    const res = await request.get('/')
    expect(res.headers()['content-security-policy']).toContain("default-src 'self'")
    expect(res.headers()['x-frame-options']).toBe('DENY')
  })
})
