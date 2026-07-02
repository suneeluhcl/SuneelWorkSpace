# Communications Recovery Guide

## If reading iMessages fails

**Symptom:** `[ERROR] Cannot read chat.db: OperationalError`

1. Check Full Disk Access:
   ```bash
   comms-permissions-check
   ```
2. If FDA denied:
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal/VS Code and toggle ON
   - Restart terminal and retry

**Symptom:** `chat.db not found`
- Messages.app may not be configured on this Mac
- Check: is iMessage signed in? Open Messages → Preferences → Accounts

---

## If sending iMessages fails

**Symptom:** `AppleEvent handler failed` or `Not authorized`

1. Grant Automation permission:
   - System Settings → Privacy & Security → Automation
   - Find Terminal → enable Messages checkbox
2. Verify Messages.app is open and signed in

**Symptom:** `Draft not found: draft_20260624_XXXXXX`
- Check: `ls ~/SuneelWorkSpace/mouth/comms/imessage/state/drafts/`
- Re-create the draft: `imsg-draft <recipient> <message>`

---

## If MCP comms tools are missing

```bash
mcp-doctor
```

If `comms_*` tools not found:
1. MCP server needs restart: `mcp-stop && mcp-start`
2. Check: `grep -c "comms_" ~/SuneelWorkSpace/nervous/mcp/server/main.py`
   - Should return ~20

---

## If Mail.app was just installed

1. Open Mail.app and configure your email account
2. Run: `comms-doctor` — should show Mail.app present
3. Test: `mail-status` — should show enabled
4. If still failing, check Automation permission for Mail in System Settings

---

## State files and where they live

| File | Purpose |
|------|---------|
| `mouth/comms/imessage/state/imessage_state.json` | Draft list and session state |
| `mouth/comms/imessage/state/drafts/` | Individual draft JSON files |
| `mouth/comms/imessage/logs/imessage_outbound.log` | Send audit log |
| `mouth/comms/mail/state/mail_state.json` | Mail subsystem state |
| `mouth/comms/config/comms_config.json` | Main config |

---

## Complete reset (preserves logs)

If the subsystem is in a bad state:

```bash
# Clear drafts (they haven't been sent)
rm ~/SuneelWorkSpace/mouth/comms/imessage/state/drafts/*.json 2>/dev/null

# Reset state
echo '{"drafts": [], "last_checked": null}' > \
  ~/SuneelWorkSpace/mouth/comms/imessage/state/imessage_state.json

# Verify
comms-doctor
```
