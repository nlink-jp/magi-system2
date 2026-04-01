# Changelog

## [0.2.1] - 2026-04-01

### Added
- Stop button (■) to cancel discussion from Web UI
- Cancelled discussions save state and emit completion event

### Fixed
- UI state restored correctly on page reload during discussion
- Button, checkbox, and status bar reflect current discussion progress
- Error logging in discussion thread (no longer silently swallowed)

## [0.2.0] - 2026-04-01

### Added
- Auto-save discussion state JSON (`magi2_YYYYMMDD_HHMMSS.json`) on completion
- Markdown report now includes full 議事録 (minutes):
  - All inner thoughts per turn (honest reaction, doubts, suppressed opinions, strategic thinking, emotional state, assessment of others)
  - Facilitator Analysis Log (hidden dynamics, strategic intent per action)
  - Convergence History table (per-turn facilitator + persona readiness)
  - Token usage metadata footer
- `--output` directory option for state file output location

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
