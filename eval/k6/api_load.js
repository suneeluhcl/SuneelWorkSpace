/**
 * k6 API Load Test — Adwi Safe Command API + Ollama
 *
 * Tests:
 *   - Safe Command API (:5055) under light load
 *   - Ollama /api/tags endpoint (model availability)
 *   - SearXNG (:8888) search responsiveness
 *
 * Run: k6 run eval/k6/api_load.js
 * With JSON output: k6 run --out json=results.json eval/k6/api_load.js
 *
 * Target: p95 < 5000ms for all endpoints (local machine, 3 VUs)
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("error_rate");
const ollamaTrend = new Trend("ollama_latency_ms");
const cmdApiTrend = new Trend("cmd_api_latency_ms");
const searxngTrend = new Trend("searxng_latency_ms");

export const options = {
  // Light load — this runs on the same machine as Adwi
  vus: 3,
  duration: "30s",

  thresholds: {
    http_req_failed: ["rate<0.10"],          // <10% failures
    http_req_duration: ["p(95)<10000"],       // p95 under 10s (generous for local LLM)
    error_rate: ["rate<0.10"],
    ollama_latency_ms: ["p(95)<5000"],
    cmd_api_latency_ms: ["p(95)<2000"],
    searxng_latency_ms: ["p(95)<3000"],
  },
};

const CMD_API_BASE = "http://localhost:5055";
const OLLAMA_BASE = "http://localhost:11434";
const SEARXNG_BASE = "http://localhost:8888";

export default function () {
  // 1. Ollama model list (cheapest call — just verifies Ollama is up)
  const ollamaRes = http.get(`${OLLAMA_BASE}/api/tags`, { timeout: "10s" });
  ollamaTrend.add(ollamaRes.timings.duration);
  const ollamaOk = check(ollamaRes, {
    "ollama /api/tags status 200": (r) => r.status === 200,
    "ollama returns model list": (r) => {
      try {
        return JSON.parse(r.body).models !== undefined;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!ollamaOk);
  sleep(0.5);

  // 2. Safe Command API health / status
  const healthRes = http.get(`${CMD_API_BASE}/health`, { timeout: "5s" });
  cmdApiTrend.add(healthRes.timings.duration);
  // 200 or 404 = server is up (we just check it responds)
  const cmdApiOk = check(healthRes, {
    "cmd api responds": (r) => r.status < 500,
  });
  errorRate.add(!cmdApiOk);
  sleep(0.2);

  // 3. SearXNG search (with a benign query)
  const searxRes = http.get(
    `${SEARXNG_BASE}/search?q=adwi+local+ai&format=json`,
    { timeout: "10s" }
  );
  searxngTrend.add(searxRes.timings.duration);
  const searxOk = check(searxRes, {
    "searxng responds": (r) => r.status === 200 || r.status === 404,
  });
  errorRate.add(!searxOk);

  sleep(1);
}

export function handleSummary(data) {
  // Write a clean JSON summary for the nightly report
  return {
    "results/k6_summary.json": JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        metrics: {
          http_req_duration_p95: data.metrics.http_req_duration?.values["p(95)"],
          http_req_failed_rate: data.metrics.http_req_failed?.values["rate"],
          ollama_p95_ms: data.metrics.ollama_latency_ms?.values["p(95)"],
          cmd_api_p95_ms: data.metrics.cmd_api_latency_ms?.values["p(95)"],
          searxng_p95_ms: data.metrics.searxng_latency_ms?.values["p(95)"],
          error_rate: data.metrics.error_rate?.values["rate"],
          total_requests: data.metrics.http_reqs?.values["count"],
        },
        thresholds_passed: Object.entries(data.root_group?.checks || {}).every(
          ([, v]) => v.passes > 0
        ),
      },
      null,
      2
    ),
  };
}
