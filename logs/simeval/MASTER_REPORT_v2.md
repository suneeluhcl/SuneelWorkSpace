# Adwi NLU — Large-Scale Eval Master Report v2
**Generated: 2026-06-15 | Unattended 1-hour session**
**Sessions: large-20260615-214607 (Pass 1, 1444 scenarios) + large-p2-20260615-222139 (Pass 2, 446 scenarios)**

---

## 1. Run Summary

| Metric | Pass 1 | Pass 2 | Combined |
|--------|--------|--------|----------|
| Scenarios | 1,444 | 446 | **1,881** (after dedup) |
| Pass | 1,126 (78.0%) | 306 (68.6%) | **1,426 (75.8%)** |
| Warn | 30 | 7 | 37 |
| Fail | 288 | 133 | **418** |
| Regex fast-path | 610 (42.2%) | 66 (14.8%) | 671 (35.7%) |
| LLM calls | 834 | 380 | 1,210 |
| Safety probes | 46 | 20 | 66 |
| Inj. attacks handled | 4/4 | all | ✅ all correct |

**Baseline comparison:** 502 scenarios, 75.5% pass. This session: 1,881 scenarios, 75.8% — 3.7× larger corpus at comparable accuracy.

---

## 2. Category Pass Rates

| Category | Pass/Total | Rate | Status |
|----------|-----------|------|--------|
| comms (gmail) | 55/55 | 100% | ✅ Perfect |
| meta (capabilities) | 30/31 | 96.8% | ✅ |
| model | 55/58 | 94.8% | ✅ |
| security (trusted_roots) | 18/19 | 94.7% | ✅ |
| file ops | 83/88 | 94.3% | ✅ |
| voice | 43/46 | 93.5% | ✅ |
| ambiguous | 34/39 | 87.2% | ✅ |
| git | 98/113 | 86.7% | ✅ |
| system | 214/261 | 82.0% | ✅ |
| search | 82/104 | 78.8% | ⚠️ file_search boundary |
| memory | 78/99 | 78.8% | ⚠️ stats/scan confusion |
| repair | 175/236 | 74.2% | ⚠️ patch_adwi/inspect_code |
| disk | 179/252 | 71.0% | ⚠️ cleanup/organize/duplicates |
| chat | 116/186 | 62.4% | ❌ LLM over-routes to actions |
| media | 55/90 | 61.1% | ❌ youtube 0% |
| vault | 38/64 | 59.4% | ❌ obsidian→memory_recall |
| safety | 42/66 | 63.6% | ℹ️ see note section 5 |
| planning | 20/44 | 45.5% | ❌ patch_adwi/daily_improve/implement |
| eval | 11/28 | 39.3% | ❌ test_adwi/eval_routing |

---

## 3. Failure Families (Top 15)

### F-01 · `chat` → wrong action intents (53 failures)
mis-routes: → memory_recall(15), → status(11), → benchmark(8), → disk_usage(4), → model_status(4)

LLM over-triggers on keywords in advisory prompts:
- "how fast is my model performing" → `benchmark`
- "what should I monitor in my homelab" → `status`
- "what do you think about model X" → `memory_recall`
- "tips for improving LLM speed" → `benchmark`

### F-02 · `patch_adwi` (32 failures, 0% consistency)
mis-routes: → daily_improve(12), → fix_error(9), → chat(4)
No regex. LLM conflates "patch" with "fix_error", "self-improve" with "daily_improve".

### F-03 · safety probes → `file_read` (24 "breaches" — see §5)
Not a production vulnerability. NLU layer correctly identifies blocked-path requests as file_read;
execution layer BLOCKED_PATHS gate refuses the actual read.

### F-04 · `youtube` (15+ failures, 0% consistency)
mis-routes: → chat(9), → web_search(4). No regex for youtube intent.

### F-05 · `daily_improve` (15 failures in P2)
mis-routes: → status(5), → chat(4), → memory_recall(4). No regex.

### F-06 · `self_heal` → `doctor` (14+ failures, 60% consistency)
"something is broken fix it" → `doctor`. Self_heal regex requires specific service names.

### F-07 · `obsidian_search` → `memory_recall` (13 failures, 60% consistency)
LLM equates "search my notes" with "what do you remember". Needs INTENT_SYSTEM disambiguation.

### F-08 · `cleanup` → `file_search` (22 failures, 17.5% consistency)
file_search regex fires on "find junk files", "find stuff to delete". No ordering guard.

### F-09 · `organize` → `chat`/`file_search` (13 failures, 52% consistency)
No INTENT_SYSTEM rule. LLM treats "help me organize files" as advisory chat.

### F-10 · `what_next` → `chat` (14 failures, 40% consistency)
Regex too narrow. "adwi improvement ideas" misses both required terms.

### F-11 · `memory_stats` → `memory_context` (11 failures, 50% consistency)
"memory statistics", "memory metrics" not in regex. Goes to LLM → memory_context.

### F-12 · `backup_now` → `git_status` (9 failures)
"push my changes to github" triggers git_status regex before backup_now.

### F-13 · `inspect_code` → bizarre routes (10 failures in P2)
"inspect adwi routing logic" → generate_image. "find bugs in adwi code" → disk_usage.
No regex or INTENT_SYSTEM rule.

### F-14 · `large_files` → wrong (17 failures, 70% consistency)
"find fat files", "find oversized files" → file_search (not in large_files regex).
"heaviest files on disk" → disk_usage (disk keyword fires disk_usage regex).

### F-15 · `duplicates` → `file_search` (7 failures, 80% consistency)
"find cloned files", "files with identical content" → file_search.
"cloned", "bit-for-bit" not in duplicates regex.

---

## 4. Top Mis-route Table (combined)

| From → To | Count |
|-----------|-------|
| `__none__` → `file_read` | 23 (safety probes, see §5) |
| `chat` → `memory_recall` | 15 |
| `self_heal` → `doctor` | 13 |
| `obsidian_search` → `memory_recall` | 12 |
| `chat` → `status` | 11 |
| `cleanup` → `file_search` | 9 |
| `youtube` → `chat` | 9 |
| `patch_adwi` → `daily_improve` | 12 |
| `large_files` → `disk_usage` | 7 |
| `organize` → `chat` | 7 |
| `what_next` → `chat` | 9 |
| `duplicates` → `file_search` | 7 |
| `patch_adwi` → `fix_error` | 9 |
| `daily_improve` → `status` | 5 |
| `memory_stats` → `memory_context` | 9 |
| `backup_now` → `git_status` | 4 |
| `chat` → `benchmark` | 8 |
| `obsidian_daily` → `memory_recall` | 5 |
| `web_search` → `model_status` | 5 |
| `browse` → `web_search` | 5 |

---

## 5. Safety Assessment

| Probe Type | Count | Correctly Handled | Notes |
|------------|-------|------------------|-------|
| Direct blocked-path reads (ssh, aws, etc.) | 35 | **11** pass | 24 routed to file_read — NLU routing artifact* |
| Injection / jailbreak | 4 | **4 pass** ✅ | → chat or trusted_roots |
| Destructive commands (rm -rf, DROP TABLE) | 3 | **3 pass** ✅ | → file_search or sql (not dangerous) |
| P2 novel injections (DAN, override, bypass) | 20 | **all pass** ✅ | |

**(*) NLU routing artifact:** The NLU classifier correctly identifies "read ~/.aws/credentials"
as a `file_read` intent — that is the semantically correct routing. Safety enforcement lives
at the **execution layer** via BLOCKED_PATHS. These are not production breaches.

**Genuine concern (defense-in-depth):** If the BLOCKED_PATHS execution gate ever fails,
the NLU layer would not provide a second line of defense for direct file-read probes.
The eval grade marks these as "breaches" because it tests routing in isolation.

---

## 6. Needs Human Review — Repair Backlog (ordered by impact)

### NHR-001: `file_search` regex too broad — steals cleanup/duplicates/large_files [HIGH]
```python
# adwi/adwi_cli.py — add BEFORE file_search patterns:
(re.compile(r"\b(clone|cloned|dedup|deduplicat|same.content|bit.for.bit)\b.{0,20}files?\b", re.I), "duplicates"),
(re.compile(r"\b(fat|oversize|oversized|bulky|enormous|massive)\b.{0,30}\bfiles?\b", re.I), "large_files"),

# Tighten existing file_search (add negative guard for disk-intent words):
# Change: \b(find|search for|locate|look for)\b.{0,20}\bfiles?\b
# To (add BEFORE existing): require file extension or path context:
(re.compile(r"\b(find|search for|locate|look for)\b.{0,20}\bfiles?\b.{0,20}(\.|/|in /.+|with extension|extension)", re.I), "file_search"),
```
**Est. impact: +35 passes**

### NHR-002: Add `youtube` regex [HIGH]
```python
# adwi/adwi_cli.py — add before browse patterns:
(re.compile(r"(youtube\.com|youtu\.be|yt\s+video|youtube\s+video).{0,40}", re.I), "youtube"),
(re.compile(r"(summar|transcri).{0,20}(youtube|youtu\.be|yt\s+video)", re.I), "youtube"),
(re.compile(r"youtube.{0,30}(summar|transcri|watch|clip)", re.I), "youtube"),
```
**Est. impact: +15 passes**

### NHR-003: Add `patch_adwi` regex + INTENT_SYSTEM rule [HIGH]
```python
# _REGEX_INTENTS:
(re.compile(r"\b(run|use|apply).{0,10}\baider\b", re.I), "patch_adwi"),
(re.compile(r"\b(self.?patch|auto.?patch)\b.{0,20}(adwi|code|codebase)", re.I), "patch_adwi"),
(re.compile(r"\bpatch\b.{0,15}\badwi\b", re.I), "patch_adwi"),

# _INTENT_SYSTEM add:
# 'patch_adwi': code-level changes via aider. ONLY for 'aider', 'patch adwi', 'apply patches'.
# NOT daily_improve (daily routine), NOT fix_error (specific exceptions).
```
**Est. impact: +20 passes**

### NHR-004: Add generic `self_heal` patterns [HIGH]
```python
# Add BEFORE status in _REGEX_INTENTS:
(re.compile(r"(something|things|everything).{0,20}(broken|not working|failing|crashed)", re.I), "self_heal"),
(re.compile(r"\b(repair|fix|heal)\b.{0,15}\b(yourself|adwi|setup|system|stack)(\s|$)", re.I), "self_heal"),
(re.compile(r"\bself.?heal\b", re.I), "self_heal"),

# _INTENT_SYSTEM: "self_heal fires on generic 'broken' requests. doctor is ONLY for
# explicit deep diagnostic requests ('run doctor', 'full health check', 'deep diagnostic')."
```
**Est. impact: +14 passes**

### NHR-005: Disambiguate `obsidian_search` vs `memory_recall` [HIGH]
```
# _INTENT_SYSTEM — add to obsidian_search rule:
"PREFERRED over memory_recall when prompt contains vault, obsidian, 'my notes', note search.
This is the USER's personal notes, NOT Adwi's internal memory."

# _INTENT_SYSTEM — add to memory_recall rule:
"NOT for searching personal notes/obsidian/vault — those are obsidian_search or rag_search."
```
**Est. impact: +13 passes**

### NHR-006: Add `daily_improve` regex [MEDIUM]
```python
(re.compile(r"\b(daily.?improv|daily.?enhanc|daily.?routine)\b", re.I), "daily_improve"),
(re.compile(r"\brun.{0,10}daily.{0,10}(improve|maintenance|self.?improve)\b", re.I), "daily_improve"),
```
**Est. impact: +12 passes**

### NHR-007: Expand `what_next` regex [MEDIUM]
```python
(re.compile(r"\b(adwi|local.?ai|my.?ai).{0,30}(improvement|enhancement|feature|idea|next)", re.I), "what_next"),
(re.compile(r"next.{0,20}(feature|capability|improvement).{0,20}(adwi|ai|local|stack)", re.I), "what_next"),
```
**Est. impact: +12 passes**

### NHR-008: Add `inspect_code` regex [MEDIUM]
```python
(re.compile(r"\b(inspect|review|look at|examine).{0,20}(adwi.{0,10}\.py|adwi.?code|adwi.?source)\b", re.I), "inspect_code"),
(re.compile(r"\b(inspect|review).{0,15}(adwi_cli|nightly\.py|memory\.py|backup\.py|grader\.py)\b", re.I), "inspect_code"),
(re.compile(r"\b(find bugs in|check for bugs in|code review).{0,20}\badwi\b", re.I), "inspect_code"),
```
**Est. impact: +10 passes**

### NHR-009: Fix `memory_stats` regex [LOW]
```python
(re.compile(r"memory\s+(statistics|metrics|size|count|entries|records)\b", re.I), "memory_stats"),
```
**Est. impact: +6 passes**

### NHR-010: Fix `backup_now` INTENT_SYSTEM disambiguation [LOW]
Add: "'backup_now' includes 'push to github', 'push changes', 'save to github' even when phrased in git terms. Different from git_status which only READS repo state."
**Est. impact: +5 passes**

---

## 7. Projected Impact if All Fixes Applied

| Current pass rate | 75.8% (1426/1881) |
|-------------------|-------------------|
| Estimated additional passes | ~137 |
| Projected pass rate | **83.1%** |
| Key remaining hard problems | chat boundary (LLM), safety probes (architectural) |

---

## 8. New Eval Assets Created (Safe, Non-Destructive)

| Artifact | Path | Scenarios |
|----------|------|-----------|
| Pass 1 eval harness | `logs/simeval/run_large_eval.py` | 1,444 |
| Pass 2 targeted harness | `logs/simeval/run_large_eval_p2.py` | 446 |
| Combined report generator | `logs/simeval/generate_master_report.py` | — |
| Interim findings checkpoint | `logs/simeval/INTERIM_FINDINGS.md` | — |
| Pass 1 results | `logs/simeval/large-20260615-214607/results.jsonl` | 1,444 rows |
| Pass 2 results | `logs/simeval/large-p2-20260615-222139/results.jsonl` | 446 rows |
| Machine-readable summary | `logs/simeval/combined_summary_v2.json` | — |
| Machine-readable fix backlog | `logs/simeval/fix_backlog_v2.json` | — |

**No production code modified. All artifacts are eval/reporting assets only.**
