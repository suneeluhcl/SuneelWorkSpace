# Workflow: Reply to an iMessage

## In VS Code Terminal

```bash
# 1. See recent messages
imsg-recent

# 2. Optionally search for context
imsg-search "meeting"

# 3. Ask Claude to draft a reply (in claude session or comms MCP):
#    comms_create_imessage_draft("+1XXXXXXXXXX", "draft text")

# 4. Review the draft
cat ~/SuneelWorkSpace/mouth/comms/imessage/state/drafts/draft_*.json | tail -1

# 5. Send (terminal only, requires confirmation)
imsg-send-confirmed draft_YYYYMMDD_HHMMSS
# → Type: SEND
```

## Via Claude / MCP

```
1. comms_list_recent_imessages()  — see recent messages
2. comms_generate_reply_draft(context, tone="friendly")  — get draft suggestion
3. comms_create_imessage_draft(recipient, message)  — save draft
4. comms_review_outbound(draft_id)  — safety check
5. In terminal: imsg-send-confirmed <draft_id>
```

## Safety checkpoints

- Is the recipient correct?
- Is the message appropriate?
- No sensitive workspace info in the message?
- Not replying to spam?
