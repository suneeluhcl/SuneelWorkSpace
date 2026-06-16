import { defineConfig, devices } from "@playwright/test";

/**
 * Adwi Playwright Config
 * Tests Open WebUI at :3000 and n8n at :5678 for smoke-level validation.
 * Run: npx playwright test
 */

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 1,
  workers: 1, // serial on local machine to avoid resource spikes

  reporter: [
    ["list"],
    ["json", { outputFile: "results/playwright.json" }],
  ],

  use: {
    headless: true,
    screenshot: "only-on-failure",
    video: "off",
    trace: "on-first-retry",
    // No external base URL — tests use absolute URLs
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
