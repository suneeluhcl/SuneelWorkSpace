/**
 * Adwi UI Smoke Tests (Playwright)
 *
 * Tests:
 *   1. Open WebUI (:3000) loads and shows model list
 *   2. n8n (:5678) workflow UI is reachable
 *   3. Safe Command API (:5055) /health responds
 *   4. Obsidian Bridge (:5056) responds
 *   5. SearXNG (:8888) search page loads
 *
 * These are smoke tests only — not functional end-to-end.
 * Run nightly to detect service failures before the morning session.
 */

import { test, expect } from "@playwright/test";

const WEBUI_URL = "http://localhost:3000";
const N8N_URL = "http://localhost:5678";
const CMD_API_URL = "http://localhost:5055";
const OBS_BRIDGE_URL = "http://localhost:5056";
const SEARXNG_URL = "http://localhost:8888";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function quickFetch(url: string): Promise<number> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    return res.status;
  } catch {
    return 0;
  }
}

// ---------------------------------------------------------------------------
// Open WebUI
// ---------------------------------------------------------------------------

test("Open WebUI loads (@3000)", async ({ page }) => {
  const response = await page.goto(WEBUI_URL, { timeout: 15_000 });
  expect(response?.status()).toBeLessThan(400);
  // Page should contain some recognisable UI text
  await page.waitForLoadState("domcontentloaded");
  const title = await page.title();
  expect(title.length).toBeGreaterThan(0);
});

test("Open WebUI has model selector", async ({ page }) => {
  await page.goto(WEBUI_URL, { timeout: 15_000 });
  await page.waitForLoadState("networkidle", { timeout: 10_000 });

  // Look for model selector or chat input — either means UI is functional
  const hasModel =
    (await page.locator("[data-testid='model-selector']").count()) > 0 ||
    (await page.locator("select").count()) > 0 ||
    (await page.locator("textarea").count()) > 0 ||
    (await page.locator("input[type='text']").count()) > 0;

  expect(hasModel).toBeTruthy();
});

// ---------------------------------------------------------------------------
// n8n
// ---------------------------------------------------------------------------

test("n8n workflow UI is reachable (@5678)", async ({ page }) => {
  const response = await page.goto(N8N_URL, { timeout: 15_000 });
  // n8n redirects to /setup or /workflows — any 200-class response is fine
  expect(response?.status()).toBeLessThan(500);
});

// ---------------------------------------------------------------------------
// Safe Command API (HTTP — no browser needed)
// ---------------------------------------------------------------------------

test("Safe Command API /health responds (@5055)", async () => {
  const status = await quickFetch(`${CMD_API_URL}/health`);
  // Allow 200 or 404 (no /health endpoint but server is up)
  expect([200, 404]).toContain(status);
});

test("Safe Command API /status responds (@5055)", async () => {
  const status = await quickFetch(`${CMD_API_URL}/adwi-status`);
  // 200 or 405 (method not allowed — POST endpoint) means server is up
  expect([200, 405, 404]).toContain(status);
});

// ---------------------------------------------------------------------------
// Obsidian Bridge
// ---------------------------------------------------------------------------

test("Obsidian Bridge responds (@5056)", async () => {
  const status = await quickFetch(`${OBS_BRIDGE_URL}/`);
  expect([200, 404, 405]).toContain(status);
});

// ---------------------------------------------------------------------------
// SearXNG
// ---------------------------------------------------------------------------

test("SearXNG search page loads (@8888)", async ({ page }) => {
  const response = await page.goto(SEARXNG_URL, { timeout: 10_000 });
  expect(response?.status()).toBeLessThan(400);
});

// ---------------------------------------------------------------------------
// Aggregate service health
// ---------------------------------------------------------------------------

test("All critical services are reachable", async () => {
  const checks = await Promise.all([
    quickFetch(WEBUI_URL).then((s) => ({ service: "Open WebUI", status: s, ok: s === 200 })),
    quickFetch(N8N_URL).then((s) => ({ service: "n8n", status: s, ok: s < 400 && s > 0 })),
    quickFetch(`${CMD_API_URL}/health`).then((s) => ({ service: "SafeCmdAPI", status: s, ok: s > 0 })),
    quickFetch(OBS_BRIDGE_URL).then((s) => ({ service: "ObsidianBridge", status: s, ok: s > 0 })),
    quickFetch(SEARXNG_URL).then((s) => ({ service: "SearXNG", status: s, ok: s === 200 })),
  ]);

  const failed = checks.filter((c) => !c.ok);
  console.table(checks);

  // Allow 1 non-critical failure (obsidian bridge may be down)
  const critical_failed = failed.filter(
    (c) => !["ObsidianBridge"].includes(c.service)
  );
  expect(critical_failed.length).toBe(0);
});
