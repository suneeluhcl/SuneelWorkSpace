# Tool And Workflow Recommendations

Generated: 2026-07-01T23:47:01.779078-05:00

No external tools were installed. These are proposals for explicit future approval.

## 1. Communication

- Build opt-in Mail and Messages playbooks around existing `mail-*`, `imessage-*`, and `comms-*` commands.
- Add approval gates for sending, deleting, archiving, forwarding, and contacting people.
- Add digest generation that stores summaries, not private message bodies, unless explicitly requested.

## 2. Research

- Use `research-engine` for idea capture, planning, comparison, and decision records.
- Add web research only when explicitly requested or when freshness materially matters.
- Promote accepted decisions into `brain/memory/DECISIONS.md`.

## 3. Automation

- Connect `improve-system` to scheduled maintenance only after several manual runs are trusted.
- Add bounded AppleScript/Shortcuts integrations per app, one workflow at a time.
- Keep writes reversible with timestamped backups for important files.

## 4. Development

- Add smoke tests for every workspace command and report failures in `agent-doctor`.
- Keep RTK as the default output filter for shell-heavy sessions.
- Use `gh` for GitHub inspection and require explicit approval for publishing changes.

## 5. System Management

- Add retention summaries for `.agent-backups`, `snapshots`, `lab/autolab/quarantine`, and logs.
- Keep system awareness metadata-only unless Suneel explicitly asks for deeper indexing.

## 6. Data Organization

- Start with metadata-only download/file triage: names, extensions, sizes, and dates.
- Add move/rename actions only after preview and explicit approval.

## 7. Assistant Intelligence

- Treat `spine/audit/gap_analysis.md` as an input to autolab and goal planning.
- Register new durable knowledge files in MCP resource maps.
- Use `idea-run` to transform rough ideas into plans, tradeoffs, and decisions.

## Inventory Summary

- Tool entries discovered: 251
- CLI tools available: 19
- Installed app names captured: 25
