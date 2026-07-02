# CSO Security Audit — SuneelWorkSpace
**Date:** 2026-06-24  
**Branch:** feat/gstack-integration  
**Auditor:** /cso (gstack Chief Security Officer)  
**Scope:** ~/SuneelWorkSpace — agent-system, mcp, orchestrator, goal-engine, autolab, bin, automation  

---

## Executive Summary

**Stack:** Python (FastMCP server), Shell scripts (bin/, automation/), JSON state files, SQLite  
**Exposure:** stdio MCP (local-only), no network listeners, no CI/CD pipeline  
**Auth surface:** None (single-user local system, stdio transport)  
**External dependencies:** `mcp`/`fastmcp` package (unpinned), gstack skill repo (garrytan/gstack)  

Overall posture: **GOOD** for a local personal workspace. Two critical findings from the previous session are already fixed. Three new findings require attention.

---

## Findings

### F1 — MEDIUM: `_read_workspace_file` has no workspace boundary guard
**File:** `nervous/mcp/server/main.py:89`  
**Status:** No current exploit path (all callers use hardcoded paths) — but UNGUARDED for future.

```python
# Current (vulnerable by design):
def _read_workspace_file(rel_or_abs: str) -> str:
    p = pathlib.Path(rel_or_abs)
    if not p.is_absolute():
        p = WORKSPACE / rel_or_abs
    # ← NO .resolve() + startswith(WORKSPACE) check
    return p.read_text(errors="replace")
```

**Risk:** Any future MCP tool or resource that passes user-supplied input to `_read_workspace_file` will be immediately path-traversal vulnerable (e.g., `../../../etc/passwd` works). Currently no tool does this, but the function signature invites it.

**Fix:** Add workspace boundary guard (same pattern as autolab-core's `_safe_restore_path`).

---

### F2 — MEDIUM: gstack skills are an unpinned external supply chain dependency
**File:** `~/.claude/skills/gstack/` (cloned from garrytan/gstack, no pinned commit)  
**Status:** Active — 10 skills symlinked, consumed by Claude Code as executable instructions.

**Risk:** gstack skills are executed as trusted instructions by Claude Code. If garrytan/gstack repo is compromised (maintainer account takeover, typosquatting of a future fork, malicious PR merged), skill updates would silently modify Claude's reasoning behaviour. There's no integrity check — `git pull` in setup is the entire install mechanism.

**Fix options:**  
- Pin to a specific commit hash in your setup  
- Mirror a personal fork and pull-request review updates before merging  
- Add a checksum file and verify on each use

---

### F3 — LOW: Autolab mutation scope includes `bin/` without code-level enforcement
**File:** `lab/autolab/mutation_policy.md` line 12  
**Status:** Policy-only — no code enforces the "explicitly queued or agent-approved" constraint.

```markdown
# mutation_policy.md line 12:
- Selected workspace scripts in `bin/` when explicitly queued or agent-approved.
```

**Risk:** `autolab-core`'s `SNAPSHOT_PATHS` allowlist controls what can be *restored*, but the *mutation* itself (autolab writing to `bin/` scripts) is only governed by policy text. A buggy or manipulated experiment could modify `agent-start`, `agent-finish`, or `agent-autoclose` — the scripts that control session boundaries and safety closeouts.

**Fix:** Add `bin/` to `autolab-core`'s `MUTATE_DENYLIST` (hard-code it) unless the experiment explicitly passes a `--allow-bin` flag that requires human confirmation.

---

### F4 — LOW: Python dependency unpinned (`mcp`/`fastmcp`)
**File:** `nervous/mcp/server/main.py` (imports `from nervous.mcp.server.fastmcp import FastMCP`)  
**Status:** No `requirements.txt` — any `pip install mcp` gets latest.

**Risk:** Breaking API changes or a compromised release of `mcp` package would silently affect the MCP server. Severity is low because `mcp` is published by Anthropic.

**Fix:** Add `nervous/mcp/server/requirements.txt` with pinned version (e.g. `mcp==1.x.x`).

---

## Previously Fixed (this session series)

| ID | Issue | Fix Commit |
|----|-------|------------|
| F-FIXED-1 | FAIL-OPEN in route-task: missing safety keywords with no floor | `_SAFETY_FLOOR` (13 hard-coded keywords), commit e5592b7 |
| F-FIXED-2 | PATH TRAVERSAL in autolab-core restore: `manifest["dst"]` not validated | `_safe_restore_path()` + SNAPSHOT_PATHS allowlist, commit e5592b7 |

---

## Cleared / Non-Findings

| Check | Result |
|-------|--------|
| Hardcoded secrets / tokens in code or git history | None found |
| Shell injection via subprocess | All subprocess calls use list form, no `shell=True` |
| SQLite injection | FTS5 query sanitized via `re.findall(r"\w+", query)` |
| Network exposure | MCP is stdio-only, no TCP listeners |
| `.env` / credential files committed | None committed, `.gitignore` covers `.env`, `secrets/` |
| CI/CD pipeline attacks | No CI/CD pipeline exists |
| Docker / K8s misconfig | No containers |
| World-writable scripts | None |
| Webhook exposure | None |

---

## Recommended Actions (Priority Order)

1. **[MEDIUM] Fix `_read_workspace_file`** — add the boundary guard before any future tool exposes it
2. **[MEDIUM] Pin gstack to a commit hash** — protect against supply chain drift
3. **[LOW] Add `bin/` hard-denylist in autolab-core** — convert policy → code enforcement
4. **[LOW] Create `nervous/mcp/server/requirements.txt`** — pin `mcp` package version
