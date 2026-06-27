# Plugin and Connector Recommendations

## iMessage

| Option | Source | Local/Remote | Credentials | Read | Write | Risk | Recommendation |
|--------|--------|-------------|-------------|------|-------|------|----------------|
| Local SQLite (current) | ~/Library/Messages/chat.db | Local | None (FDA) | YES | NO | Low — read-only local DB | **ACTIVE — use this now** |
| AppleScript send | System osascript | Local | None (Automation perm) | NO | YES | Low — requires explicit confirmation | **ACTIVE — use for sends** |
| imessage@claude-plugins-official | anthropics/claude-plugins-official | Local | None | YES | YES | Low — official plugin, review changelog | **RECOMMENDED — install when ready** |

### Installing the official iMessage plugin

```bash
install-imessage-plugin    # shows guide
# then in a Claude session:
/plugin install imessage@claude-plugins-official
```

---

## Email

### Apple Mail.app (not installed)

| Option | Status | Risk | Recommendation |
|--------|--------|------|----------------|
| Apple Mail.app (App Store) | Not installed | Low — local, well-audited | **Install first if you want email** |

After installing Mail.app, the `mail-*` scripts will automatically start working via AppleScript.

### Gmail

| Option | Source | Local/Remote | Credentials | Risk | Recommendation |
|--------|--------|-------------|-------------|------|----------------|
| gmail@claude-plugins-official | anthropics/claude-plugins-official | Remote OAuth | Google OAuth | Medium — Google OAuth scope review needed | Evaluate after iMessage is stable |
| mcp__claude_ai_Gmail (built-in) | Claude.ai built-in | Remote | Google OAuth (already available in session) | Low — official, already seen in tool list | May already be available |

Note: `mcp__claude_ai_Gmail__authenticate` appears in your Claude Code tool list — Gmail may already be accessible via the built-in MCP. Try `mcp__claude_ai_Gmail__authenticate` in a Claude session to check.

### Microsoft 365 / Outlook

| Option | Source | Risk | Recommendation |
|--------|--------|------|----------------|
| outlook@claude-plugins-official | anthropics/claude-plugins-official | Medium — MSAL OAuth | Evaluate if you use Outlook |

### IMAP/SMTP (Generic)

| Option | Risk | Recommendation |
|--------|------|----------------|
| Python imaplib + smtplib | Low (local) but requires app password | Configure as follow-up if no Mail.app |

To configure IMAP/SMTP, ask the agent to set up `mouth/comms/mail/scripts/mail-imap.py`. You'll provide an app password (not your main password).

---

## Evaluated but not recommended

| Plugin | Reason not recommended |
|--------|----------------------|
| SMTP relay services (SendGrid, etc.) | Require API keys, not local, overshoot for personal use |
| Telegram bot | Not relevant to your current setup |
| WhatsApp unofficial bridges | No official Claude plugin, high supply chain risk |

---

## Next steps

1. Test iMessage read/send (local — already works)
2. Install `imessage@claude-plugins-official` for dedicated Claude iMessage mode
3. Decide on email: Apple Mail (local, simple) vs Gmail plugin (remote, no install)
4. If Gmail: run `mcp__claude_ai_Gmail__authenticate` to check if built-in MCP already supports it
