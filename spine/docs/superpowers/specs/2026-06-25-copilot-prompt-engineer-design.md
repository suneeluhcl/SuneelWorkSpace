# Copilot Prompt Engineer — Design Spec
Date: 2026-06-25

## Goal

Add a `copilot_prompt_engineer` MCP tool to the existing workspace-brain MCP server so Claude automatically delegates prompt writing and improvement tasks to Microsoft 365 Copilot Chat (personal account, Mac) via a headless Playwright browser session.

## Trigger Behaviour

Claude auto-invokes this tool when the user asks it to write, improve, or engineer a prompt, skill, or system instruction. No explicit "use Copilot" instruction is needed — Claude recognises prompt engineering tasks and calls the tool automatically.

## Architecture

```
nervous/nervous/mcp/server/
├── main.py                  — add one @mcp.tool() entry point
├── copilot_browser.py       — NEW: all Playwright + Copilot session logic
├── sessions/
│   └── copilot_cookies.json — NEW: persisted login cookies (gitignored)
└── requirements.txt         — add playwright

bin/
└── copilot-login            — NEW: one-time visible-browser login helper
```

## Components

### `nervous/nervous/mcp/server/copilot_browser.py`

Single class with two public methods:

```python
class CopilotSession:
    COOKIE_FILE = SERVER / "sessions" / "copilot_cookies.json"
    COPILOT_URL = "https://copilot.microsoft.com"

    def ensure_session(self) -> bool
        # Returns True if valid cookie file exists, False otherwise

    def ask(self, prompt: str, timeout: int = 60) -> str
        # Launches headless Chromium, loads cookies, sends prompt,
        # waits for response, returns plain text.
        # Raises LoginRequired if cookies are missing or expired.
```

### `nervous/nervous/mcp/server/main.py` — new tool

```python
@mcp.tool()
def copilot_prompt_engineer(task: str, context: str = "") -> str:
    """
    Delegate a prompt engineering task to Microsoft Copilot.
    task: what prompt to write or improve
    context: optional existing prompt text to improve
    Returns the engineered prompt as plain text.
    """
```

### `bin/copilot-login`

One-time setup script:
1. Opens a visible Chromium window
2. User logs into copilot.microsoft.com normally
3. Script saves cookies to `nervous/nervous/mcp/server/sessions/copilot_cookies.json`
4. Exits — all future tool calls use the saved session headlessly

## Data Flow

1. User asks Claude to write or improve a prompt
2. Claude calls `copilot_prompt_engineer(task="...", context="...")`
3. `copilot_browser.py` starts headless Chromium and loads saved cookies
4. Navigates to `copilot.microsoft.com`
5. Sends this framed request:
   ```
   You are an expert prompt engineer. Your only job is to return a single,
   ready-to-use prompt — no explanation, no preamble, no markdown wrapper.

   Task: {task}
   {context if provided}
   ```
6. Waits up to 60 seconds for Copilot's response text to appear
7. Returns the plain text response to Claude
8. Claude uses the engineered prompt directly

## Auth & Session Management

- Cookies last approximately 30 days
- Cookie file is stored at `nervous/nervous/mcp/server/sessions/copilot_cookies.json`
- The `sessions/` directory is gitignored — cookies are never committed
- When cookies expire the tool returns a clear error string; user reruns `bin/copilot-login`

## Error Handling

| Condition | Tool returns |
|---|---|
| Cookie file missing | `"LOGIN_REQUIRED: run bin/copilot-login first"` |
| Session expired | `"SESSION_EXPIRED: run bin/copilot-login to refresh"` |
| No response in 60s | `"TIMEOUT: Copilot did not respond"` |
| Empty response | `"EMPTY_RESPONSE: Copilot returned no text"` |

Claude surfaces these as actionable messages to the user.

## Dependencies

- `playwright` added to `nervous/nervous/mcp/server/requirements.txt`
- `playwright install chromium` run once at setup (~130MB Chromium binary)
- No other new dependencies

## Setup Steps (for implementation plan)

1. `pip install playwright && playwright install chromium`
2. Run `bin/copilot-login` once to save session cookies
3. Restart the MCP server to pick up the new tool
4. Verify with a test call: `copilot_prompt_engineer(task="write a one-sentence system prompt for a helpful assistant")`

## Out of Scope

- Enterprise / Graph API integration (user has personal account)
- Visible browser mode during tool calls (always headless after login)
- Caching or deduplicating identical prompt requests
- Multi-turn Copilot conversations (single-shot request/response only)
