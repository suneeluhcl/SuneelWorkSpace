# Communications Permissions Guide

## iMessage

### Full Disk Access (REQUIRED for reading messages)

Your terminal (or VS Code) needs Full Disk Access to read `~/Library/Messages/chat.db`.

**How to grant:**
1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Click the lock icon (if locked) and authenticate
3. Click **+** and add:
   - `/Applications/Utilities/Terminal.app` (if using Terminal)
   - `/Applications/Visual Studio Code.app` (if using VS Code terminal)
   - `/Applications/iTerm.app` (if using iTerm2)
4. Toggle the switch to ON for each app
5. Restart the terminal application

**Verification:**
```bash
comms-permissions-check
```
Expected output: `[OK] Full Disk Access (chat.db readable)`

**Status:** FDA was confirmed granted during setup (June 2026).

---

### Automation Permission for Messages.app (REQUIRED for sending)

Your terminal needs Automation access to control Messages.app via AppleScript.

**How to grant:**
1. Open **System Settings** → **Privacy & Security** → **Automation**
2. Find **Terminal** (or iTerm2/VS Code)
3. Enable the checkbox next to **Messages**

**When you'll see the prompt:**
macOS will show a permission dialog the first time a script tries to control Messages.app. Click **OK** to grant.

**Verification:**
Run `imsg-draft "+1XXXXXXXXXX" "test"` followed by `imsg-send-confirmed <draft_id>` — if it fails with an Automation error, the permission hasn't been granted yet.

---

## Mail

Mail.app is **not installed** on this system. No Mail permissions are needed until it is installed.

**Options:**
1. Install Apple Mail.app from the App Store (free) — then Automation permission for Mail will be needed
2. Use the Gmail plugin (`claude plugin install gmail@claude-plugins-official`) — requires Google OAuth
3. Configure IMAP/SMTP manually — requires credentials, not recommended for first setup

See: `mouth/comms/reports/plugin_recommendations.md` for evaluation of each option.

---

## Quick Reference

| Permission | Where | For |
|------------|-------|-----|
| Full Disk Access | System Settings → Privacy & Security → Full Disk Access | Reading iMessages |
| Automation → Messages | System Settings → Privacy & Security → Automation | Sending iMessages |
| Automation → Mail | System Settings → Privacy & Security → Automation | Sending email (if Mail.app installed) |
| Accessibility | Not required for current setup | Only if UI automation needed later |

---

## Troubleshooting

**"Operation not permitted" when reading chat.db:**
→ Full Disk Access not granted. Follow steps above.

**"AppleEvent handler failed" when sending:**
→ Automation permission for Messages not granted. Follow steps above.

**"Messages app not running" error:**
→ Open Messages.app manually, sign in with your Apple ID, then retry.
