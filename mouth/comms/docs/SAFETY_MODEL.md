# Communications Safety Model

## Core Principles

1. **No auto-send** — Nothing is ever sent without explicit human confirmation
2. **No auto-reply** — No daemon replies to incoming messages automatically
3. **Drafts first** — All outbound messages go through a draft stage
4. **Confirmation required** — Terminal prompt must receive literal `SEND` to execute
5. **Minimal logging** — Logs record metadata (recipient hash, timestamp, status), never message bodies
6. **No credential storage** — No passwords, tokens, or API keys in workspace files
7. **No bulk send** — Single recipient per send command; no broadcast mode

## Send Flow

```
1. User requests draft       comms_create_imessage_draft() / imsg-draft
2. Draft saved to state/     mouth/comms/imessage/state/drafts/<id>.json
3. User reviews draft        cat mouth/comms/imessage/state/drafts/<id>.json
4. User runs send-confirmed  imsg-send-confirmed <draft_id>
5. Terminal prompts: "Type SEND to send"
6. User types SEND
7. AppleScript sends via Messages.app
8. Log entry written         (metadata only: timestamp, recipient prefix, body hash)
```

## What is logged

| Field | Logged? |
|-------|---------|
| Timestamp | YES |
| Draft ID | YES |
| Recipient (first 4 chars + ****) | YES — partially redacted |
| Body hash (SHA-256, first 16 chars) | YES |
| Full message body | NO |
| Outcome (SENT/FAILED) | YES |
| Error message | YES |

## Allowlist

The outbound allowlist is empty by default (`outbound_policy.json: allowlist_enforced: false`).

To restrict sends to known contacts only:
1. Edit `mouth/comms/config/access_policy.json`
2. Set `allowlist.enabled: true`
3. Add phone numbers/emails to `allowlist.recipients`

The send script will check the allowlist before proceeding.

## Debug Mode

Full message body logging is disabled by default. To enable (development only):
1. Set `comms_config.json: safety.body_logging_debug_mode: true`
2. Remember to disable again when done

## MCP Tool Safety Boundaries

- `comms_create_imessage_draft` — creates draft, does NOT send
- `comms_send_imessage_confirmed` — dry-run preview only, returns terminal command
- All actual sends require terminal execution of `imsg-send-confirmed`
- No MCP tool can send a message directly — this is intentional

## Why MCP send is dry-run only

Allowing MCP tools to send iMessages directly would mean an AI agent given the right context could trigger outbound sends without human awareness. The dry-run boundary ensures every real send is a deliberate human action in a terminal.
