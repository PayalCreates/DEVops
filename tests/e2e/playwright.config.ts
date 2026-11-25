import { defineConfig, devices } from '@playwright/test'

// E2E_BASE_URL: the running stack (docker compose -> http://localhost:8080).
// PW_CHANNEL=chrome uses an installed Google Chrome instead of downloaded Chromium.
export default defineConfig({
  testDir: './specs',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], channel: process.env.PW_CHANNEL || undefined },
    },
  ],
})
