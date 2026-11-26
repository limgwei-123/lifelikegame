import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  timeout: 45_000,
  use: {
    baseURL: process.env.E2E_WEB_URL || 'http://localhost:5173',
    browserName: 'chromium',
    channel: process.env.E2E_BROWSER_CHANNEL || undefined,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
