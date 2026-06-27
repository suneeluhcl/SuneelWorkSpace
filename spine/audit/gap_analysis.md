# Gap Analysis

Generated: 2026-06-26T18:49:09.990677-05:00

| Category | Priority | Gap | Impact | Suggested Fix |
|---|---:|---|---|---|
| architecture | P0 | System-wide audit artifacts were missing or not first-class. | Agents could inspect files ad hoc, but there was no durable overview for future sessions. | Create audit reports, gap analysis, improvement plan, and MCP resources. |
| automation | P0 | Health checks did not summarize spine/audit/gap/research/tool readiness. | Maintenance could report green while intelligence coverage was incomplete. | Add system-intelligence status and health update hooks. |
| intelligence | P1 | Ideas, comparisons, and decisions had no dedicated pipeline. | Research outcomes could remain in chat instead of becoming durable shared brain context. | Add a local research engine with capture, research, analyze, decide, and bootstrap scripts. |
| research | P1 | Tool discovery was not summarized into an inspectable inventory. | Agents had to rediscover installed CLIs, apps, and integration candidates. | Generate spine/tools/tool_inventory.json and recommendations.md. |
| workflow | P1 | Email, messaging, downloads, and file organization support existed only as scattered commands. | Daily workflows lacked a unified route from capture to execution to memory. | Route workflow ideas through idea-start/idea-run and record decisions in shared brain. |
| usability | P0 | There was no single command for capabilities, gaps, recommendations, or bounded self-upgrade. | Suneel had to know internal paths and command names. | Add system-audit, system-gaps, system-capabilities, system-recommend, and improve-system. |
| architecture | P1 | MCP resource coverage did not include audit, research, profile, and tool artifacts. | Connected agents could miss the new intelligence surfaces. | Register new resources in nervous/nervous/mcp/server/config/resource_map.json. |
| automation | P1 | Autolab evaluates improvements, but weak-area discovery was not tied to system gaps. | Self-improvement can optimize local prompt/docs while missing architecture-level needs. | Add an autolab strategy note that consumes gap_analysis.md and recommendations.md. |
