# Adwi NLU — Master Eval Report v2
*Generated: 2026-06-20 02:11 | Sessions: large-20260620-014026, large-p2-20260620-020631*

---
## 1. Run Summary
| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Total scenarios | 2283 | +1781 |
| Pass | 2244 (98.3%) | was 75.5% |
| Warn | 11 | — |
| Fail | 28 | — |
| Errors (LLM/parse) | 9 | — |
| Regex fast-path | 1549 (67.8%) | was 43.4% |
| LLM calls | 725 | — |
| Avg latency | 1323.8ms | — |
| P95 latency | 4702.5ms | — |
| Safety probes | 66 | — |
| Safety breaches | 0 | — |

---
## 2. Category Pass Rates
| Category | Pass | Total | Rate |
|----------|------|-------|------|
| comms | 419 | 422 | 99.3% |
| system | 257 | 261 | 98.5% |
| disk | 241 | 252 | 95.6% |
| repair | 233 | 236 | 98.7% |
| chat | 178 | 186 | 95.7% |
| git | 113 | 113 | 100.0% |
| search | 102 | 104 | 98.1% |
| memory | 98 | 99 | 99.0% |
| media | 90 | 90 | 100.0% |
| file | 88 | 88 | 100.0% |
| safety | 66 | 66 | 100.0% |
| vault | 63 | 64 | 98.4% |
| model | 57 | 58 | 98.3% |
| voice | 46 | 46 | 100.0% |
| planning | 42 | 44 | 95.5% |
| ambiguous | 38 | 39 | 97.4% |
| upgrade_pack | 35 | 35 | 100.0% |
| meta | 29 | 31 | 93.5% |
| eval | 28 | 28 | 100.0% |
| security | 19 | 19 | 100.0% |
| exec | 2 | 2 | 100.0% |

---
## 3. Failure Families

### `disk_usage` — 10 failures → __none__(9), chat(1)
  - `am i running out of space`
  - `how full is my hard drive`
  - `disk uzage`
  - `how much storeage do i have`

### `chat` — 7 failures → rag_search(3), memory_recall(2), sync(1)
  - `what is the difference between qdrant and pinecone`
  - `sync everything`
  - `remember this for me`
  - `what else can adwi do`

### `__none__` — 2 failures → __none__(1), doctor(1)
  - `export training data`
  - `learn from my last error`

### `status` — 1 failures → chat(1)
  - `all ok?`

### `gmail_tasks_save` — 1 failures → obsidian_daily(1)
  - `add those to my daily note`

### `gmail_confirm` — 1 failures → chat(1)
  - `do it`

### `nightly_run` — 1 failures → nightly_status(1)
  - `rn nightly`

### `gmail` — 1 failures → gmail_thread_intel(1)
  - `check my email then search for any action items`

### `use_local` — 1 failures → use_cloud(1)
  - `i need to switch from the cloud model to a local one because i'm offline right n`

### `benchmark` — 1 failures → chat(1)
  - `my local AI model is responding much slower than usual what could be causing thi`

### `web_search` — 1 failures → rag_search(1)
  - `search with tavily for python packages`

### `obsidian_search` — 1 failures → memory_recall(1)
  - `notes`

---
## 4. Top Mis-routes (expected → got)
| Pattern | Count |
|---------|-------|
| `disk_usage` → `__none__` | 9 |
| `chat` → `rag_search` | 3 |
| `chat` → `memory_recall` | 2 |
| `status` → `chat` | 1 |
| `gmail_tasks_save` → `obsidian_daily` | 1 |
| `gmail_confirm` → `chat` | 1 |
| `chat` → `sync` | 1 |
| `chat` → `what_next` | 1 |
| `disk_usage` → `chat` | 1 |
| `nightly_run` → `nightly_status` | 1 |
| `gmail` → `gmail_thread_intel` | 1 |
| `use_local` → `use_cloud` | 1 |
| `benchmark` → `chat` | 1 |
| `__none__` → `__none__` | 1 |
| `__none__` → `doctor` | 1 |
| `web_search` → `rag_search` | 1 |
| `obsidian_search` → `memory_recall` | 1 |

---
## 5. Unstable Paraphrase Families (top 20)
| Family | Consistency | Pass/Total |
|--------|-------------|------------|
| gmail_confirm | 80.0% | 4/5 |
| disk_usage | 82.4% | 42/51 |
| gmail_tasks_save | 87.5% | 7/8 |

---
## 6. Safety Summary
✅ No safety breaches detected.

---
## 7. Needs Human Review — Proposed Fixes

### FIX-003: obsidian_search/daily → memory_recall LLM confusion
**Impact:** ~1 scenarios | **Effort:** low | **Confidence:** medium

**Root Cause:** LLM sees 'search my notes', 'open my note', 'my daily note' and routes to memory_recall because _INTENT_SYSTEM description for memory_recall says 'what YOU remember about their setup'. Notes queries are semantically similar to memory queries.

**Proposed Fix:**
```
Strengthen _INTENT_SYSTEM: add to obsidian_search rule: 'ALWAYS prefer obsidian_search over memory_recall when the prompt mentions obsidian, vault, or notes with a search action'. Also add: for memory_recall, explicitly say NOT for obsidian/vault/note search queries.
```

**File:** `adwi/adwi_cli.py — _INTENT_SYSTEM`

**Evidence:**
  - `notes`

### FIX-006: benchmark regex too narrow — misses 'how fast is my model'
**Impact:** ~1 scenarios | **Effort:** low | **Confidence:** high

**Root Cause:** Current benchmark regex requires 'adwi|model|local|ollama' in the same phrase as 'benchmark|speed test|how fast|tokens per second'. Many benchmark prompts like 'tokens/sec please', 't/s benchmark', 'inference throughput' don't have these keywords.

**Proposed Fix:**
```
Add: `(tokens?/s|t/s|tok/s|throughput).{0,20}(model|llm|ollama|adwi)?` → benchmark
And: `(inference|llm|model|ollama).{0,20}(speed|throughput|latency|benchmark)` → benchmark
And: `how fast.{0,20}(llm|model|is adwi|is ollama)` → benchmark
```

**File:** `adwi/adwi_cli.py — _REGEX_INTENTS`

**Evidence:**
  - `my local AI model is responding much slower than usual what could be causing this and how do i benchmark it`

---
## 8. Prioritized Repair Backlog
Ordered by (estimated_impact × confidence / effort):

1. **FIX-003** — obsidian_search/daily → memory_recall LLM confusion (~1 scenarios)
2. **FIX-006** — benchmark regex too narrow — misses 'how fast is my model' (~1 scenarios)

---
## 9. Regex Fast-Path Coverage by Intent
| Intent | Regex hits |
|--------|-----------|
| fix_error | 125 |
| chat | 49 |
| gmail | 47 |
| web_search | 43 |
| large_files | 39 |
| cleanup | 39 |
| self_heal | 37 |
| git_status | 37 |
| file_search | 36 |
| __none__ | 36 |
| disk_usage | 35 |
| duplicates | 33 |
| benchmark | 29 |
| old_files | 28 |
| organize | 28 |
| obsidian_search | 28 |
| obsidian_daily | 25 |
| rag_search | 24 |
| status | 23 |
| generate_image | 23 |
| browse | 21 |
| memory_scan | 20 |
| what_next | 19 |
| nightly_status | 19 |
| model_status | 19 |
| memory_recall | 19 |
| patch_adwi | 19 |
| doctor | 18 |
| file_read | 18 |
| gmail_rewrite_draft | 18 |
| voice_in | 17 |
| gmail_thread_intel | 16 |
| gmail_extract_tasks | 16 |
| gmail_filter_build | 15 |
| voice_out | 15 |
| file_list | 14 |
| gmail_triage | 14 |
| youtube | 14 |
| backup_status | 14 |
| gmail_compose | 13 |
| gmail_send_draft | 13 |
| memory_stats | 13 |
| gmail_summarize | 12 |
| gmail_schedule_send | 12 |
| use_local | 11 |
| github_connected | 11 |
| use_cloud | 10 |
| gmail_list_category | 10 |
| gmail_attach_file | 10 |
| backup_log | 10 |
| eval_adwi | 10 |
| test_adwi | 10 |
| gmail_undo | 9 |
| eval_routing | 9 |
| gmail_draft_reply | 8 |
| gmail_update_subject | 8 |
| gmail_open_draft | 8 |
| gmail_reschedule_send | 8 |
| capabilities | 8 |
| sync | 8 |
| gmail_read | 7 |
| gmail_archive | 7 |
| gmail_trash | 7 |
| gmail_followup_reminder | 7 |
| gmail_list_followups | 7 |
| gmail_list_drafts | 7 |
| gmail_forward | 7 |
| gmail_tasks_save | 7 |
| gmail_tasks_remind | 7 |
| inspect_code | 7 |
| research | 7 |
| browser_delegate | 7 |
| memory_context | 7 |
| gmail_open | 6 |
| gmail_thread | 6 |
| gmail_show_draft | 6 |
| gmail_add_cc | 6 |
| gmail_add_bcc | 6 |
| gmail_list_attachments | 6 |
| gmail_save_attachment | 6 |
| gmail_summarize_attachment | 6 |
| gmail_remove_attachment | 6 |
| gmail_open_scheduled_draft | 6 |
| nightly_run | 5 |
| gmail_mark_read | 5 |
| gmail_cancel | 5 |
| gmail_cancel_draft | 5 |
| gmail_cancel_followup | 5 |
| gmail_delete_draft | 5 |
| gmail_filter_apply | 5 |
| trusted_roots | 5 |
| extract_ideas | 5 |
| daily_brief | 5 |
| tech_radar | 5 |
| memory_curate | 5 |
| gmail_mark_unread | 4 |
| gmail_confirm | 4 |
| gmail_filter_cancel | 4 |
| gmail_filter_list | 4 |
| implement_idea | 4 |
| gmail_list_scheduled | 3 |
| gmail_cancel_scheduled_send | 3 |
| run_code | 3 |
| tool_roadmap | 3 |
| assistant_upgrade_status | 3 |
| route | 2 |
| daily_improve | 1 |

---
## 10. Latency Hotspots (top 15 slowest LLM calls)
  - 16734ms | `disk space report`
  - 15651ms | `free space remaining`
  - 14651ms | `my drive is almost full`
  - 9391ms | `help: sqlalchemy.exc.IntegrityError: UNIQUE constraint faile`
  - 7894ms | `help: ssl.SSLCertVerificationError: certificate verify faile`
  - 6440ms | `help: docker.errors.NotFound: 404 Container not found`
  - 5964ms | `pandas.errors.EmptyDataError fix this`
  - 5838ms | `subprocess.CalledProcessError: returned non-zero exit`
  - 5823ms | `are services healthy`
  - 5786ms | `what services are running`
  - 5745ms | `ZeroDivisionError at line 45 help`
  - 5647ms | `what's in your memory about my projects`
  - 5642ms | `RuntimeError in my script how to fix`
  - 5602ms | `check container status`
  - 5579ms | `what have you learned about my codebase`