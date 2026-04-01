# CLAUDE.md — magi-system2

**Organization rules (mandatory): https://github.com/nlink-jp/.github/blob/main/CONVENTIONS.md**

## Purpose

Multi-persona AI discussion system. Dynamically generates 3 personas per topic,
runs structured debates with dual memory (inner thoughts + public statements),
and guides toward consensus via an adaptive facilitator agent.

## Architecture

```
magi_system2/
  cli.py              — CLI entry point (discuss, replay, export, render)
  facilitator.py      — Topic analysis, persona design, flow control, synthesis
  persona.py          — Response generation with dual memory + streaming
  discussion.py       — Main loop, state management, convergence detection
  models.py           — Pydantic data models
  llm.py              — Vertex AI Gemini client (structured, streaming, multimodal)
  media.py            — Attachment loading, MIME detection
  translator.py       — Output translation (Gemini Flash)
  console.py          — Terminal system log (API calls, tokens, latency)
  web.py              — FastAPI + WebSocket real-time UI + replay mode
  save.py             — Markdown/HTML/JSON export
  templates/index.html — Web UI template
  static/style.css    — Light (原稿用紙) / Dark (墨色) themes
```

## LLM Configuration

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"   # Required
export GOOGLE_CLOUD_LOCATION="us-central1"       # Optional
export MAGI2_PRO_MODEL="gemini-2.5-pro"          # Persona model
export MAGI2_FLASH_MODEL="gemini-2.5-flash"      # Facilitator model
```

## Key Design Decisions

### Dual Memory
Each persona has inner_thoughts (private) and statement (public). The facilitator
reads inner thoughts to guide flow but never reveals them to other personas.

### Native Language Mode
`--lang ja` instructs all LLMs to generate directly in Japanese (or any language).
No post-hoc translation — eliminates extra API calls and latency.

### Streaming + CoT
`generate_structured_stream()` uses `include_thoughts=True` with `thinking_budget=4096`.
Thinking chunks stream as 🧠 CoT display, text chunks as incremental card preview.
Final JSON is parsed after stream completes.

### Consensus Check
When convergence is near but some personas are below threshold, the facilitator
asks them directly before closing. This prevents premature convergence.

### Facilitator as Separate Agent
Not system messages at fixed turns. The facilitator is a Flash-based LLM that
reads the full conversation + inner thoughts and decides flow adaptively.

## CLI Commands

| Command | Description |
|---------|-------------|
| `discuss "topic"` | Start discussion with Web UI |
| `discuss --file topic.md --attach spec.pdf` | Multimodal input |
| `discuss --lang ja --show-thoughts` | Japanese mode with thought bubbles |
| `discuss "topic" --output ./results` | Save to specific directory |
| `replay --state file.json` | Replay saved discussion (no LLM) |
| `export --state file.json --markdown` | Export report + 議事録 (full inner thoughts, facilitator analysis) |
| `export --state file.json --html` | Export as static HTML |
| `render --state file.json --lang ko` | Re-render in another language |

### Auto-saved State

Every discussion saves `magi2_YYYYMMDD_HHMMSS.json` on completion.
Contains full state: messages, inner thoughts, facilitator actions, convergence history, token usage.

## Development

```bash
uv sync                        # Install dependencies
uv run pytest tests/ -v        # Run tests
uv run magi2 replay --state tests/fixtures/sample_discussion.json  # UI dev (no LLM)
```

## Security

- Topic input wrapped in nonce-tagged XML (`<user_data_{nonce}>`)
- No credentials in output files
- Vertex AI authentication via ADC
- Web UI binds to 127.0.0.1 by default
