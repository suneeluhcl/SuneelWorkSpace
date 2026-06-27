# Workflow: Convert a Message to a Workspace Task

## Pattern

When a message creates an action item, convert it to a task rather than losing it in the chat.

## Steps

```bash
# 1. Find the message
imsg-recent
# or: imsg-search "project deadline"

# 2. In Claude, call:
#    comms_triage_item("imessage", "message_id", "brief summary")
#    comms_convert_to_task("imessage", "message_id", "Task description", "high")

# 3. Verify task was added
cat ~/SuneelWorkSpace/heart/tasks/ACTIVE_TASKS.md
```

## Goal conversion (larger items)

For a message that implies a larger initiative:

```
comms_convert_to_goal("imessage", "message_id", "Research X as mentioned by contact", "medium")
```

Then:
```bash
goal-plan G001
goal-execute G001
```
