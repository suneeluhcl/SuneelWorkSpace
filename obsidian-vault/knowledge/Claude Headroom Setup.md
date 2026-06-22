---
type: reference
status: active
tags: [claude, headroom, context-compression, token-efficiency]
updated: 2026-06-22
---

# Claude Headroom Setup

Headroom is a local context compression proxy that reduces the tokens sent to Anthropic by 60–95%, with no accuracy loss. It runs entirely on your Mac — data never leaves your machine.

---

## What was installed

| Item | Detail |
|------|--------|
| Package | `headroom-ai[proxy]` v0.27.0 |
| Install method | `pipx install --python /opt/homebrew/bin/python3.12 "headroom-ai[proxy]"` |
| Python | 3.12.13 (isolated pipx venv — does not touch adwi/.venv) |
| Binary | `~/.local/bin/headroom` |
| Config modified | None at install time |

---

## How Claude is configured

Headroom does **not** permanently modify Claude config. Instead:

1. `headroom wrap claude` starts a local proxy on port 8787
2. It temporarily writes `ANTHROPIC_BASE_URL=http://127.0.0.1:8787` into `.claude/settings.local.json` (project-local, not global)
3. Claude Code sends all API calls through the proxy, which compresses context before forwarding to Anthropic
4. When the wrap session exits, the settings.local.json entry is automatically removed

---

## How to launch Claude with Headroom

```bash
# From your workspace terminal:
headroom wrap claude

# With a specific model:
headroom wrap claude -- --model claude-sonnet-4-6
```

This replaces a bare `claude` invocation. You get the same Claude experience, with compression running transparently.

**Without Headroom (fallback):** Just run `claude` normally. Everything works as before. Headroom is purely additive.

---

## Verify it is working

During a `headroom wrap claude` session, open a second terminal and run:

```bash
# Check proxy and routing:
headroom doctor

# See compression savings:
headroom perf

# Run the local validator:
adwi/.venv/bin/python3 adwi/scripts/validate_claude_headroom.py

# Compact status:
adwi/.venv/bin/python3 adwi/scripts/claude_headroom_status.py
```

When the proxy is running, `headroom doctor` shows all green. `headroom perf` shows token savings per session.

---

## What Headroom compresses

| Content type | Algorithm | Savings |
|---|---|---|
| JSON tool outputs | SmartCrusher | 70–90% |
| Source code | CodeCompressor (AST) | 40–75% |
| Prose / logs | Kompress-base (text) | 60–85% |
| Git/search results | RTK shell filters | 60–92% |

The RTK shell filter (`rtk <cmd>`) is also available and reduces what gets into context in the first place. Add `rtk` as a prefix to common commands:

```bash
rtk git status    # 59% smaller
rtk git diff      # 80% smaller
rtk grep <pat>    # filtered
```

---

## Proxy details

| Property | Value |
|---|---|
| Default port | 8787 |
| Backend | Direct Anthropic API (forwarded with compression) |
| Data location | Local only — no data leaves your Mac |
| CCR cache | Originals stored locally; LLM retrieves via headroom_retrieve if needed |

---

## Rollback / uninstall

To stop using Headroom:
1. Exit the `headroom wrap claude` session (Ctrl+C or close terminal)
2. Verify `.claude/settings.local.json` no longer has `ANTHROPIC_BASE_URL` — it is cleaned up automatically
3. If anything was injected globally: `headroom unwrap` removes Headroom entries from `~/.claude/settings.json`
4. To uninstall entirely: `pipx uninstall headroom-ai`

**Normal `claude` invocations are never affected** — only `headroom wrap claude` sessions route through the proxy.

---

## Known limitations

- Headroom reduces token usage but cannot guarantee Claude will never hit context limits — it extends the effective window, not eliminates it.
- The proxy must be running (`headroom wrap claude`) for compression to be active. If the proxy is not running, Claude falls back to direct Anthropic API silently.
- Python 3.12 is used for the Headroom venv (pipx-isolated). The adwi `.venv` (Python 3.14) is untouched.
- The `[proxy]` extra is installed. ML-based Kompress compression (requires `torch`) is not included — SmartCrusher + CodeCompressor + RTK still give 60–90% savings on coding workloads.
- `headroom perf` shows accurate stats only after sessions routed through the proxy.

---

## Validation scripts

| Script | Purpose |
|---|---|
| `adwi/scripts/validate_claude_headroom.py` | 8-check static validator (stdlib-only, read-only) |
| `adwi/scripts/claude_headroom_status.py` | Compact one-screen status |

---

## Related

- [[Adwi Home]]
- [[knowledge/Automation Map]]
- `CLAUDE.md` — Headroom Usage section (workspace Claude instructions)
- `adwi/scripts/validate_claude_headroom.py`
- `adwi/scripts/claude_headroom_status.py`
