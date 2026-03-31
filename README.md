# magi-system2

Multi-persona AI discussion system with dynamic persona generation, dual memory, and adaptive facilitation — powered by Vertex AI Gemini.

[日本語版 README はこちら](README.ja.md)

## Concept

Three dynamically generated AI personas debate a topic under the guidance of an autonomous facilitator. Each persona maintains private inner thoughts alongside public statements, creating rich discussion dynamics with natural convergence toward consensus.

Built on [magi-system](https://github.com/nlink-jp/magi-system) (v1), redesigned from scratch for Gemini's 1M context window and advanced reasoning capabilities.

```
                    ┌──────────────────┐
                    │   Facilitator    │
                    │  (Gemini Flash)  │
                    │                  │
                    │  Analyze topic   │
                    │  Design personas │
                    │  Control flow    │
                    │  Detect consensus│
                    └────────┬─────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │Persona A │  │Persona B │  │Persona C │
        │(Gem Pro) │  │(Gem Pro) │  │(Gem Pro) │
        │          │  │          │  │          │
        │ 💭 inner │  │ 💭 inner │  │ 💭 inner │
        │ 💬 public│  │ 💬 public│  │ 💬 public│
        └──────────┘  └──────────┘  └──────────┘
```

## Features

- **Dynamic persona generation** — Facilitator analyzes the topic and designs 3 personas with rich personality profiles, tailored to the subject
- **Dual memory** — Each persona has private inner thoughts (honest reactions, doubts, strategy) and public statements (diplomatic, strategic)
- **Adaptive facilitator** — Separate LLM agent that reads inner thoughts to guide discussion flow, never revealing private thoughts to other personas
- **Streaming + CoT display** — Real-time token-by-token output with Chain of Thought (Gemini's reasoning process) visible
- **Multimodal input** — Text, Markdown, PDF, images, audio, video as discussion topics
- **Gradient convergence** — Continuous 0.0–1.0 convergence signals instead of binary votes
- **Web UI** — Real-time discussion visualization via WebSocket, with thought bubble toggle
- **Hybrid language** — Internal reasoning in English for maximum quality, output translation on demand
- **Console monitoring** — API calls, token usage, latency, cost tracking in terminal
- **Replay mode** — Re-watch saved discussions without LLM calls

## Quick Start

```bash
# Install
git clone https://github.com/nlink-jp/magi-system2.git
cd magi-system2
uv sync

# Configure
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud auth application-default login

# Run a discussion
magi2 discuss "Should organizations adopt zero-trust security architecture?"
# Open http://127.0.0.1:8080 in your browser
```

## CLI

```bash
# Simple topic
magi2 discuss "Your topic here"

# Markdown input with attachments
magi2 discuss --file proposal.md --attach spec.pdf --attach diagram.png

# Language and display options
magi2 discuss --file topic.md --lang ja --show-thoughts

# Control
magi2 discuss "Topic" --max-turns 20 --port 8081

# Replay saved discussion (no LLM needed)
magi2 replay --state discussion.json

# Export
magi2 export --state discussion.json --markdown
magi2 export --state discussion.json --html --lang ja --show-thoughts

# Re-render in another language
magi2 render --state discussion.json --lang ko
```

## Web UI

| Feature | Description |
|---------|-------------|
| Discussion timeline | Real-time streaming of persona statements |
| Persona panels | Name, archetype, readiness bar, stance evolution |
| Thought bubbles | Toggle to show private inner thoughts (💭) |
| CoT display | Gemini's Chain of Thought reasoning (🧠) during streaming |
| Convergence gauge | 0.0–1.0 progress bar with facilitator assessment |
| Token counter | Pro/Flash/Total token usage in real-time |
| Activity indicator | Shows who is currently thinking |
| Theme toggle | Light (default) / Dark mode |

## Configuration

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"   # Required
export GOOGLE_CLOUD_LOCATION="us-central1"       # Optional
export MAGI2_PRO_MODEL="gemini-2.5-pro"          # Persona model
export MAGI2_FLASH_MODEL="gemini-2.5-flash"      # Facilitator model
```

## Architecture

```
magi_system2/
  cli.py              — CLI entry point (discuss, replay, export, render)
  facilitator.py      — Topic analysis, persona design, flow control, synthesis
  persona.py          — Response generation with dual memory + streaming
  discussion.py       — Main loop, state management, convergence detection
  models.py           — Pydantic data models (PersonalityProfile, InnerThoughts, etc.)
  llm.py              — Vertex AI Gemini client (structured, streaming, multimodal)
  media.py            — Attachment loading, MIME detection
  translator.py       — Output translation (Gemini Flash)
  console.py          — Terminal system log
  web.py              — FastAPI + WebSocket real-time UI
  save.py             — Markdown/HTML/JSON export
```

## Key Differences from magi-system v1

| Aspect | v1 | v2 |
|--------|----|----|
| LLM | Local (OpenAI-compatible) | Vertex AI Gemini (1M context) |
| Personas | Fixed 3 (MELCHIOR/BALTHASAR/CASPER) | Dynamic, topic-appropriate |
| Personality | 3-line description | Rich profile (communication, cognition, emotion, interpersonal) |
| Memory | Truncated history (16 turns) | Full history + private inner thoughts |
| Facilitator | System messages at fixed turns | Separate LLM agent reading inner thoughts |
| Convergence | Binary votes + markers | Gradient 0.0–1.0 signals |
| Input | Single-line text | Multimodal (text, PDF, images, audio, video) |
| Output | TUI (Rich) | Web UI (WebSocket) + Console monitoring |
| Streaming | None | Real-time with Chain of Thought |

## Design Documents

- [Architecture](docs/design/architecture.md) — Full system design, data models, language strategy

## License

MIT — see [LICENSE](LICENSE)
