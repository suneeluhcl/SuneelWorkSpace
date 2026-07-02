---
entity: Llm Wiki Concept
type: concept
created: 2026-06-29T05:03:21.640837+00:00
updated: 2026-07-02T06:02:00+00:00
---

# Llm Wiki Concept

## Facts

- The LLM-Wiki pattern: an LLM maintains a persistent, plain-file knowledge wiki — ingesting sources into entity notes, linting link health, and answering queries from the compounded notes instead of raw context.
- Originates from a gist by [[Karpathy]]; implemented in this workspace as `brain/vault/wiki/` with ingest (`wiki-ingest`), lint (`wiki_lint.py`, run nightly by the night-shift pipeline), and query pipelines.
- Notes are markdown with YAML frontmatter; double-bracket wikilinks form the knowledge graph, and each note carries Facts and Backlinks sections.
- A deep comparison of this pattern against hosted alternatives lives in [[synthesis-20260629-050559-explain-the-llm-wiki-pattern-and-compare]].

## Related

- Concepts: [[LLM]], [[LLM-Wiki]], [[RAG]], [[Personal-Knowledge-Base]], [[Research]]
- Tools: [[ChatGPT]], [[OpenAI-Codex]], [[NotebookLM]], [[Obsidian]]
- People: [[Karpathy]]

## Backlinks
