# How Communications Works

## Architecture

```
VS Code Terminal
      ↓
  bin/ shortcuts (imsg-recent, mail-recent, etc.)
      ↓
  mouth/comms/imessage/scripts/ or mouth/comms/mail/scripts/
      ↓
  ┌─────────────────────────────────────────┐
  │  iMessage         │  Mail               │
  │  SQLite read      │  AppleScript (stub) │
  │  ~/Library/       │  /Applications/     │
  │  Messages/chat.db │  Mail.app (missing) │
  └─────────────────────────────────────────┘
      ↓
  MCP workspace-brain (comms_* tools)
      ↓
  Claude/Codex agents (reads context, drafts replies)
      ↓
  Orchestrator (routes comms tasks to right agent)
      ↓
  Goal Engine (converts messages → goals/tasks)
```

## iMessage

### Reading (works now)

Direct SQLite read from `~/Library/Messages/chat.db`. Full Disk Access required.

```bash
imsg-recent              # last 24h
imsg-recent --hours 48   # last 48h
imsg-recent --limit 50   # more messages
imsg-search "meeting"    # search text
```

### Sending (AppleScript — requires Automation permission)

All sends go through a 2-step draft-and-confirm flow:

```bash
imsg-draft "+15551234567" "Hi, just checking in"
# → shows: Draft ID: draft_20260624_143000

imsg-send-confirmed draft_20260624_143000
# → asks: Type SEND to confirm
```

### Via Claude / MCP

From inside a Claude session:
- `comms_list_recent_imessages()` — read recent messages
- `comms_search_imessages("query")` — search
- `comms_create_imessage_draft("+1...", "text")` — create draft
- `comms_send_imessage_confirmed("draft_id")` — get the terminal command (dry-run)

Then in terminal: `imsg-send-confirmed <draft_id>`

## Mail

Mail.app is not installed. To enable:
1. Install Apple Mail.app from App Store
2. Configure your email account in Mail
3. Re-run `comms-doctor` to verify
4. The `mail-*` scripts will then work via AppleScript

For Gmail without Mail.app, see `mouth/comms/reports/plugin_recommendations.md`.

## Claude iMessage Plugin

The official `imessage@claude-plugins-official` plugin enables a dedicated iMessage conversation channel in Claude.

Status: Not installed.

To install:
```bash
install-imessage-plugin    # shows step-by-step guide
```

Then launch Claude with the plugin:
```bash
use-claude-imessage
```

## Task/Goal Conversion

Convert messages into workspace items:

```bash
# From MCP (inside Claude):
comms_convert_to_task("imessage", "rowid_123", "Follow up with John about the proposal", "high")
comms_convert_to_goal("email", "email_id", "Research competitors mentioned in email", "medium")
```

Or use the terminal goal commands:
```bash
goal-create "Follow up from message" --complexity simple
```
