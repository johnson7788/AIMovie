import { defineConfig, devices } from 'playwright/test'

/**
 * E2E config for the AIMovie frontend.
 * Assumes the dev server (vite, port 36310) and backend (port 8666) are already running.
 */
export default defineConfig({
    testDir: './e2e',
    timeout: 60_000,
    expect: { timeout: 15_000 },
    fullyParallel: false,
    reporter: [['list']],
    use: {
        baseURL: 'http://127.0.0.1:36310',
        headless: true,
        screenshot: 'only-on-failure',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
})
