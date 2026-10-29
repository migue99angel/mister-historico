import { defineConfig, devices } from '@playwright/test';

// The app against the real API (production composition, PostgreSQL and the engine), with
// the synthetic Test FC season and the golden seed: see e2e/support/real_api.py. Its ports
// differ from `make dev` (5173 and 8000), so a running dev stack is never reused by mistake.
const PORT = 5175;
const API_PORT = 8010;
// Same app with the MSW handlers (fictional Test FC): the accessibility pass plays whole runs
// without a backend.
const MOCKED_PORT = 5174;
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
  webServer: [
    {
      // Needs uv and Docker: a throwaway PostgreSQL container is created and removed.
      command: 'uv run --project ../backend python e2e/support/real_api.py',
      url: `http://localhost:${String(API_PORT)}/health`,
      env: { E2E_API_PORT: String(API_PORT) },
      // Never reuse: an API left by another worktree would serve another backend.
      reuseExistingServer: false,
      // SIGTERM lets uvicorn return and remove the container; without it Playwright kills
      // the process and only the testcontainers reaper (Ryuk) cleans up.
      gracefulShutdown: { signal: 'SIGTERM', timeout: 15_000 },
      // First runs pull the PostgreSQL image and sync the backend environment.
      timeout: 300_000,
    },
    {
      command: `npm run dev -- --port ${String(PORT)} --strictPort`,
      url: `http://localhost:${String(PORT)}`,
      env: {
        API_PROXY_TARGET: `http://localhost:${String(API_PORT)}`,
        VITE_API_MOCKING: 'disabled',
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --port ${String(MOCKED_PORT)} --strictPort`,
      url: `http://localhost:${String(MOCKED_PORT)}`,
      env: { VITE_API_MOCKING: 'enabled' },
      reuseExistingServer: !isCI,
      timeout: 60_000,
    },
  ],
});
