# Communications Subsystem

Read, draft, and reply to iMessages and email from the VS Code workspace terminal.

## Quick Start

```bash
comms-status          # overall status
comms-permissions-check  # check what macOS permissions are granted

# iMessage
imsg-recent           # recent messages (last 24h)
imsg-search "query"   # search messages
imsg-draft "+15551234567" "Hi there"  # create draft (no send)
imsg-send-confirmed draft_20260624_HHMMSS  # send after review

# Mail (disabled — Mail.app not installed)
mail-status           # shows why disabled + options
```

## Architecture

```
bin/         Short-form terminal aliases
  imsg-recent
  imsg-search
  imsg-draft
  imsg-send-confirmed
  mail-*
  comms-status
  comms-doctor
  comms-report
  comms-permissions-check
  install-imessage-plugin
  use-claude-imessage

mouth/comms/
  config/    Configuration and policy
  imessage/  iMessage scripts, logs, drafts
  mail/      Mail scripts (stubs until Mail.app installed)
  workflows/ Agent workflow guides
  spine/docs/      HOW_IT_WORKS, SAFETY_MODEL, PERMISSIONS, RECOVERY
  reports/   Comms status reports, plugin recommendations

nervous/nervous/mcp/server/main.py   comms_* tools and resources registered here
heart/orchestrator/        imessage_read, imessage_reply, email_read, email_reply task types
heart/goals/         comms goals supported via comms_convert_to_goal()
```

## Safety Rules (non-negotiable)

- No auto-send, ever
- No auto-reply, ever
- All sends require explicit terminal confirmation (`SEND`)
- Drafts are local JSON files — review before sending
- Message bodies are never logged
- MCP send tools are dry-run only

## Docs

- `mouth/comms/spine/docs/HOW_IT_WORKS.md` — full architecture
- `mouth/comms/spine/docs/SAFETY_MODEL.md` — safety rules
- `mouth/comms/spine/docs/PERMISSIONS.md` — macOS permissions guide
- `mouth/comms/spine/docs/RECOVERY.md` — troubleshooting
- `mouth/comms/reports/plugin_recommendations.md` — email/plugin options
