# Changelog

## [0.1.0] - 2026-04-01

### Added
- Core discussion engine with dynamic persona generation via Gemini Flash
- Rich personality profiles (communication style, cognitive traits, emotional tendencies, interpersonal patterns)
- Dual memory: private inner thoughts + public statements per persona
- Adaptive facilitator agent reading inner thoughts for flow control
- Streaming output with Chain of Thought (CoT) display
- Multimodal input support (text, Markdown, PDF, images, audio, video)
- Native language mode (`--lang ja` — LLM generates directly in target language)
- Gradient convergence detection (0.0–1.0) with consensus check for low-readiness personas
- Facilitator announcement before closing statements
- Web UI with WebSocket real-time updates
- Persona panels with icon, archetype, readiness bar, stance evolution
- Thought bubble toggle (💭) and facilitator insight toggle (🎯)
- CoT display (🧠) with auto-scroll during streaming
- Activity indicator showing who is currently thinking
- Token usage counter (Pro/Flash/Total) in status bar
- Convergence gauge with gradient fill
- Light theme (原稿用紙/manuscript paper warm palette) and dark theme (墨色/sumi-ink)
- Theme toggle with localStorage persistence
- Markdown report download button
- Replay mode (`magi2 replay --state file.json`) for LLM-free UI testing
- Console system monitoring (API calls, tokens, latency, cost)
- Markdown/HTML/JSON export
- Prompt injection defense (nonce-tagged XML wrapping)
- 9 tests (models + serialization)
