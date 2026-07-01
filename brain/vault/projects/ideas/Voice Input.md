---
type: idea
status: planned
tags: [idea, roadmap, voice, whisper]
updated: 2026-06-21
---

# Voice Input

#idea #roadmap #voice

## Status
🔵 Planned — not started

## Why It Matters
Lets you prompt Adwi without typing. Especially useful when [[hands]] are occupied, during debugging sessions, or for quick queries. The M4 Max's CoreML support makes whisper.cpp fast on-device.

## Existing Related Files

| File | Relevance |
|------|-----------|
| `adwi/voice.py` | Already has STT (faster-whisper) + TTS (piper-tts) |
| `adwi/adwi_cli.py` | `/voice`, `/voice-in`, `/voice-brief`, `/listen` already wired |
| `adwi/bin/adwi` | Entry point to integrate voice trigger |

*Note: `voice.py` already exists with faster-whisper. The gap is making it the default input path and testing it end-to-end.*

## Implementation Sketch

1. Confirm faster-whisper `base.en` model is working on M4 Max via CoreML
2. Add a `--voice` flag to `bin/adwi` that launches with `/listen` active by default
3. Test the STT → handle() dispatch loop for latency
4. Add wake-word detection (optional, later)
5. Ensure `/voice-out` TTS responds to all outputs in voice mode

## Risks

- Latency: STT + LLM + TTS may feel slow; measure end-to-end
- False activations in `/listen` silence-detection (sox 3% threshold)
- Model size: faster-whisper base.en is ~150 MB — already available

## Next Action

Run `/listen` and test a complete voice prompt → response → TTS cycle. Measure latency.

## Related Notes

- [[knowledge/System Map]]
- [[knowledge/Ideas Index]]
- [adwi/voice.py](../../../adwi/voice.py)
