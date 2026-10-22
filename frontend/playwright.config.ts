import { defineConfig, devices } from '@playwright/test';

const PORT = 5173;
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  reporter: isCI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${String(PORT)}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'Pixel 7',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'iPhone 14',
      // The iPhone 14 profile defaults to WebKit, whose Linux system libraries need
      // `sudo npx playwright install-deps`. To keep a single browser (Chromium) in local
      // and CI, we emulate the iPhone 14 viewport, DPR, touch and user agent on Chromium.
      use: { ...devices['iPhone 14'], browserName: 'chromium' },
    },
  ],
  webServer: {
    command: `npm run dev -- --port ${String(PORT)} --strictPort`,
    url: `http://localhost:${String(PORT)}`,
    reuseExistingServer: !isCI,
    timeout: 60_000,
  },
});
