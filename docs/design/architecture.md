# Architecture — magi-system2

## Background

magi-system (v1) was designed for local LLMs with limited context windows.
magi-system2 is a clean-room redesign leveraging Vertex AI Gemini (1M context)
for richer reasoning, dynamic persona generation, and autonomous facilitation.

### Key Differences from v1

| Aspect | magi-system (v1) | magi-system2 |
|--------|-------------------|--------------|
| LLM | Local (OpenAI-compatible) | Vertex AI Gemini 2.5 Pro/Flash |
| Context | ~4K–32K, truncated history | 1M tokens, full history preserved |
| Input | Single-line topic text | Markdown document (or simple text) |
| Personas | Fixed 3 (MELCHIOR/BALTHASAR/CASPER) | Dynamic 3, generated per topic |
| Roles | Fixed 3 (advocate/skeptic/alternative) | Dynamic, topic-appropriate roles |
| Facilitator | System messages at fixed turns | Separate LLM persona, adaptive |
| Emotional model | Simple sentiment + intensity | Rich reasoning with full context |
| History | Truncated (16 recent turns) | Full conversation in context |

## Core Concept

```
                    ┌──────────────────────┐
                    │     Facilitator      │
                    │   (Gemini Flash)     │
                    │                      │
                    │  • Analyze topic     │
                    │  • Design personas   │
                    │  • Control flow      │
                    │  • Detect consensus  │
                    │  • Synthesize report │
                    └──────┬───────────────┘
                           │ directs
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ Persona A  │ │ Persona B  │ │ Persona C  │
       │(Gemini Pro)│ │(Gemini Pro)│ │(Gemini Pro)│
       │            │ │            │ │            │
       │ Dynamically│ │ Dynamically│ │ Dynamically│
       │ generated  │ │ generated  │ │ generated  │
       │ per topic  │ │ per topic  │ │ per topic  │
       └────────────┘ └────────────┘ └────────────┘
```

## Architecture Overview

### Phase 0: Topic Analysis & Persona Design (Facilitator)

Input: Multimodal — any combination of:

| Type | CLI flag | Examples |
|------|----------|---------|
| Text | positional arg | `magi2 "Should we adopt microservices?"` |
| Markdown | `--file` | `magi2 --file proposal.md` |
| PDF | `--attach` | `--attach spec.pdf` |
| Image | `--attach` | `--attach design.png --attach alternative.jpg` |
| Audio | `--attach` | `--attach meeting-recording.mp3` |
| Video | `--attach` | `--attach demo.mp4` |
| Mixed | combined | `--file brief.md --attach contract.pdf --attach diagram.png` |

All inputs are passed to the Facilitator as multimodal content parts.
The Facilitator analyzes the full input (text + attachments) and produces:

1. **Topic summary** — structured understanding of the subject,
   including descriptions of key content from attachments
   (e.g. "The PDF proposes X. The diagram shows architecture Y.")
2. **Attachment digest** — per-attachment summary for persona context
   (so personas can reference specific parts: "As shown in the design PDF, section 3...")
3. **Key dimensions** — the axes along which disagreement is likely
4. **Three personas** — each with full personality profile and initial stance
5. **Discussion strategy** — suggested phases and focus areas

Attachments are included in the initial LLM call (Phase 0) where the full
content is analyzed. During the discussion (Phase 1), attachments are NOT
re-sent on every turn — instead, the Facilitator's attachment digest serves
as a compressed reference. This keeps per-turn token costs manageable while
preserving the ability to reference specific details.

If a persona needs to re-examine a specific attachment during discussion,
the Facilitator can inject the relevant attachment in that turn's context.

This replaces v1's fixed MELCHIOR/BALTHASAR/CASPER with topic-appropriate voices.

### Phase 1: Discussion (Personas + Facilitator)

```
┌─────────────────────────────────────────────────────┐
│                  Discussion Loop                     │
│                                                     │
│  1. Facilitator selects next speaker + gives prompt │
│  2. Persona generates response (opinion + meta)     │
│  3. Facilitator analyzes response:                  │
│     - Update discussion state                       │
│     - Check for convergence signals                 │
│     - Decide intervention (redirect, deepen, etc.)  │
│  4. Repeat until consensus or max turns             │
│                                                     │
│  Facilitator interventions:                         │
│  • "Deepen this point"                              │
│  • "Address X's concern about Y"                    │
│  • "Propose a concrete compromise"                  │
│  • "Summarize areas of agreement"                   │
│  • "Final statements please"                        │
└─────────────────────────────────────────────────────┘
```

Key design decisions:

- **Full history in context** — No truncation. 1M context can hold hundreds of turns.
  Personas see the entire conversation, enabling genuine memory and reference.
- **Facilitator as active agent** — Not fixed-turn system messages, but an LLM
  that reads the full conversation and decides when/how to intervene.
- **Speaker selection by Facilitator** — Instead of v1's maximum-disagreement
  heuristic, the Facilitator chooses who speaks next based on:
  - Who has an unaddressed concern
  - Who hasn't spoken recently
  - What the discussion needs (challenge, support, synthesis)
- **Structured persona response** — JSON with opinion, stance evolution,
  key points, and readiness-to-converge signal.

### Phase 2: Synthesis (Facilitator)

After convergence or max turns:

1. Facilitator generates **executive summary**
2. Facilitator produces **per-persona final positions**
3. Facilitator identifies **areas of consensus** and **remaining disagreements**
4. Facilitator writes **recommendations** based on the discussion

## Module Structure

```
magi_system2/
  cli.py              — CLI entry point (argparse)
  facilitator.py      — Facilitator agent (topic analysis, persona design,
                         discussion control, synthesis)
  persona.py          — Persona agent (response generation, dual memory)
  discussion.py       — Discussion engine (main loop, state management)
  models.py           — Pydantic data models
  llm.py              — Vertex AI Gemini client wrapper (multimodal support)
  media.py            — Attachment loading, MIME detection, content parts builder
  translator.py       — Output translation (Gemini Flash, cached)
  web.py              — FastAPI app (WebSocket for real-time updates)
  console.py          — Terminal system log (API calls, tokens, errors)
  save.py             — Markdown export + JSON state persistence + static HTML
  templates/
    facilitator_prompts.py  — Facilitator prompt templates
    persona_prompts.py      — Persona prompt templates
```

## Data Models

### Persona Design (Generated by Facilitator)

```python
class PersonalityProfile(BaseModel):
    """Rich personality model for nuanced discussion behavior."""

    # ── Identity ──
    communication_style: str    # e.g. "formal and precise", "passionate and direct"
    debate_approach: str        # e.g. "builds arguments incrementally with evidence",
                                #       "challenges assumptions head-on"
    intellectual_tendencies: str # e.g. "seeks first principles", "draws from case studies"

    # ── Cognitive traits ──
    risk_tolerance: str         # e.g. "highly risk-averse, demands proof before change"
    decision_framework: str     # e.g. "utilitarian cost-benefit", "precautionary principle"
    cognitive_biases: list[str] # Tendencies to watch for (self-aware)
                                # e.g. ["status quo bias", "anchoring to regulations"]

    # ── Emotional tendencies ──
    emotional_baseline: str     # e.g. "measured and calm, but firm under pressure"
    triggers: list[str]         # What makes them passionate or frustrated
                                # e.g. ["dismissal of safety concerns", "vague claims"]
    persuasion_sensitivity: str # What kind of argument they find compelling
                                # e.g. "data and precedent", "human stories and impact"

    # ── Interpersonal style ──
    conflict_style: str         # e.g. "diplomatic but persistent", "confrontational"
    concession_pattern: str     # How they compromise
                                # e.g. "will concede on implementation details but not principles"
    listening_quality: str      # e.g. "actively references others' points",
                                #       "tends to reframe others' arguments to fit own view"


class PersonaDesign(BaseModel):
    """Complete persona specification generated per topic."""

    name: str                          # Display name (e.g. "Dr. Keiko Tanaka")
    archetype: str                     # Short label (e.g. "Regulatory Expert")
    background: str                    # Professional/personal background (3-5 sentences)
    expertise: list[str]               # Areas of expertise relevant to the topic
    perspective: str                    # How they see the topic (worldview lens)
    core_values: list[str]             # Priority values driving their stance
    blind_spots: list[str]             # What they tend to underweight or miss
    initial_stance: str                # Opening position on the topic
    personality: PersonalityProfile    # Rich personality model
    temperature: float                 # LLM temperature (0.2-0.8)


class AttachmentDigest(BaseModel):
    """Summary of an attached file for persona reference."""
    filename: str                      # Original filename
    media_type: str                    # MIME type (application/pdf, image/png, etc.)
    summary: str                       # What this attachment contains
    key_points: list[str]              # Specific details personas may reference
    reference_label: str               # Short label for in-discussion citation
                                       # e.g. "[Design-PDF]", "[Screenshot-A]"


class TopicAnalysis(BaseModel):
    summary: str
    attachment_digests: list[AttachmentDigest]  # Per-attachment summaries
    key_dimensions: list[str]          # Axes of disagreement
    personas: list[PersonaDesign]      # exactly 3
    discussion_strategy: str           # Suggested phases and focus
    expected_tensions: list[str]       # Predicted friction points between personas
```

### Dual Memory: Inner Thoughts + Public Statement

Each persona maintains two distinct streams of thought per turn:

```
┌─────────────────────────────────────────────────────┐
│  Persona Turn Processing                             │
│                                                     │
│  1. Read full conversation history                  │
│  2. Read own private inner_thought history           │
│  3. Generate:                                       │
│     ┌───────────────────────────────────────────┐   │
│     │ inner_thoughts (private, never shared)     │   │
│     │  • What I really think about their points  │   │
│     │  • My doubts and uncertainties              │   │
│     │  • Strategic considerations                 │   │
│     │  • Emotional reactions I won't express      │   │
│     │  • What I wish I could say but shouldn't    │   │
│     └───────────────────────────────────────────┘   │
│     ┌───────────────────────────────────────────┐   │
│     │ statement (public, added to discussion)    │   │
│     │  • Diplomatic, strategic public response   │   │
│     │  • May differ significantly from inner     │   │
│     │    thoughts — personas are political       │   │
│     └───────────────────────────────────────────┘   │
│  4. Inner thoughts stored in persona's private log  │
│     → Only visible to: the persona itself           │
│     → Invisible to: other personas, facilitator*    │
│  5. Statement appended to shared conversation       │
│                                                     │
│  * Facilitator sees inner thoughts for flow control │
│    but never reveals them to other personas         │
└─────────────────────────────────────────────────────┘
```

```python
class InnerThoughts(BaseModel):
    """Private internal monologue — never shared with other personas."""

    honest_reaction: str          # True reaction to recent arguments
    doubts: list[str]             # Own position's weaknesses they recognize
    strategic_thinking: str       # What they're trying to achieve tactically
    emotional_state: str          # How they actually feel (vs. what they show)
    suppressed_opinions: list[str]# Things they think but choose not to say
    assessment_of_others: dict[str, str]  # Private evaluation of each persona
    willingness_to_move: str      # Real flexibility (may differ from public)


class PersonaResponse(BaseModel):
    """Complete persona output per turn — inner + public."""

    # ── Private (stored in persona's memory only) ──
    inner_thoughts: InnerThoughts

    # ── Public (added to shared conversation) ──
    statement: str                      # The spoken opinion
    key_points: list[str]               # Main arguments in this turn
    addressed_to: str                   # Primarily responding to whom
    stance_evolution: str               # How their public position has shifted

    # ── Convergence signals (visible to facilitator) ──
    readiness_to_converge: float        # 0.0 (far apart) to 1.0 (ready)
    convergence_conditions: str         # "I could agree if..."
```

### Why Dual Memory?

Real discussions involve a gap between what people think and what they say.
This gap creates richer dynamics:

- A persona might privately agree with a rival's point but publicly challenge
  it to maintain credibility — then gradually shift their public stance later.
- A persona might suppress doubts about their own position in public but the
  Facilitator can detect these doubts and guide the discussion toward them.
- Strategic thinking (e.g. "if I concede this point, I can push harder on that
  one") creates natural negotiation dynamics.
- The display can optionally show inner thoughts (like a "thought bubble" view)
  for the user to see the full picture.

### Facilitator's Access to Inner Thoughts

The Facilitator reads inner thoughts to make better flow decisions:

- If a persona privately doubts their own position → steer discussion toward
  that weak point to accelerate convergence.
- If a persona is strategically withholding a concession → create conditions
  for them to offer it gracefully.
- If emotions are running high internally but personas are being diplomatic →
  the Facilitator can tell the discussion is more contentious than it appears.

**Critical rule**: The Facilitator NEVER reveals inner thoughts to other personas
or quotes from them. They inform flow decisions only.

### FacilitatorAction

```python
class FacilitatorAction(BaseModel):
    # ── Flow control ──
    next_speaker: str               # Persona name
    instruction: str                # Guidance for next speaker
    intervention: str               # Optional facilitator statement to inject
    discussion_status: str          # Phase label

    # ── Analysis (informed by inner thoughts) ──
    convergence_assessment: float   # 0.0-1.0 overall convergence
    hidden_dynamics: str            # What the facilitator sees beneath the surface
                                    # e.g. "Persona A privately agrees with B but
                                    # won't say it yet. Persona C's doubts are growing."
    strategic_intent: str           # Why this action — what the facilitator is trying
                                    # to unlock or accelerate
```

### DiscussionState

```python
class DiscussionState(BaseModel):
    topic: TopicAnalysis
    messages: list[Message]         # Full conversation history
    turn: int
    phase: str                      # Current phase label
    convergence_level: float        # 0.0-1.0
    is_converged: bool
```

## LLM Configuration

### Model Assignment

| Role | Model | Rationale |
|------|-------|-----------|
| Facilitator | Gemini 2.5 Flash | Fast, cost-efficient for meta-analysis |
| Personas | Gemini 2.5 Pro | Deep reasoning for substantive arguments |
| Synthesis | Gemini 2.5 Pro | Quality final report |

### Why Not Flash for Everything?

Personas need deep, nuanced reasoning about complex topics. Pro's stronger
analytical capabilities produce more insightful arguments. Flash is sufficient
for the Facilitator's meta-analysis (who speaks next, is the discussion
progressing, when to intervene).

### Environment Variables

```bash
GOOGLE_CLOUD_PROJECT="your-project-id"      # Required
GOOGLE_CLOUD_LOCATION="us-central1"          # Optional
MAGI2_PRO_MODEL="gemini-2.5-pro"             # Persona model
MAGI2_FLASH_MODEL="gemini-2.5-flash"         # Facilitator model
```

## CLI Interface

```bash
# Interactive mode
magi2

# Direct topic (simple text)
magi2 "AIの倫理的課題について"

# Markdown input
magi2 --file topic.md

# Multimodal input
magi2 --file proposal.md --attach spec.pdf
magi2 --file brief.md --attach design-a.png --attach design-b.png
magi2 "Evaluate this recording" --attach meeting.mp3

# Language control
magi2 --file topic.md --lang ja            # English discussion, Japanese output
magi2 --native-discussion --lang ja        # Japanese discussion for nuance-critical topics

# Display modes
magi2 --show-thoughts                      # Show inner thought bubbles
magi2 --show-thoughts --show-facilitator   # + facilitator's hidden analysis

# Output & Export
magi2 --file topic.md --save --output ./results    # Auto-save all formats
magi2 --max-turns 30

# Export from completed discussion
magi2 export --state discussion.json --markdown     # Markdown report
magi2 export --state discussion.json --html         # Static HTML (self-contained)
magi2 export --state discussion.json --html --lang ja --show-thoughts

# Re-render in another language
magi2 render --state discussion.json --lang ko
```

## Discussion Flow Detail

### Turn Lifecycle

```
1. Facilitator reads full history + current state
   → Produces FacilitatorAction:
     - Who speaks next
     - What instruction/focus to give them
     - Whether to inject a facilitator statement
     - Current convergence assessment

2. If facilitator statement exists:
   → Append to message history as facilitator message
   → Display to user

3. Selected persona reads:
   - Full shared message history (including facilitator's instruction)
   - Own private inner_thoughts history (past turns' inner monologue)
   - Their persona design (system prompt with personality profile)
   → Produces PersonaResponse (inner_thoughts + statement)

4. Store inner_thoughts in persona's private log
   → Pass to facilitator for next-turn analysis
   → Optionally display to user (thought-bubble mode)

5. Append statement to shared conversation history
   → Display to user
   → Update convergence tracking

5. Check convergence:
   - facilitator.convergence_assessment > 0.8
   - All personas have readiness_to_converge > 0.7
   - At least MIN_TURNS elapsed
   → If met: enter closing phase
```

### Convergence Detection

v1 used binary votes + markers. v2 uses a gradient approach:

- Each persona reports `readiness_to_converge` (0.0–1.0)
- The Facilitator independently assesses `convergence_assessment` (0.0–1.0)
- Convergence triggers when:
  - Facilitator assessment > 0.8 AND
  - Average persona readiness > 0.7 AND
  - min(persona readiness) > 0.5 AND
  - turns >= MIN_TURNS (default: 8)

This allows natural, gradual convergence instead of sudden vote-flipping.

### Closing Phase

1. Facilitator announces convergence
2. Each persona gives a final statement (what they agree with, what they still disagree on)
3. Facilitator generates the synthesis report

## Output Formats

Three output formats, all generated from the same discussion state:

### 1. Web UI (Live + Archive)

- **Live**: Real-time during discussion via WebSocket
- **Static HTML export** (`magi2 export --html`): Self-contained single file
  (same pattern as ir-tracker). CSS/JS/data inlined. Works from `file://`.
  Includes thought bubble toggle, facilitator insight toggle, attachment
  previews, and convergence visualization.

### 2. Markdown Report (`magi2 export --markdown`)

```markdown
# MAGI System 2 — Discussion Report

**Topic**: [title]
**Date**: 2026-04-01 14:30
**Turns**: 24
**Convergence**: Achieved (0.87)
**Language**: ja (translated from English)

## Topic Analysis

[Facilitator's initial analysis]

## Attachments

| # | File | Summary |
|---|------|---------|
| [Design-PDF] | proposal.pdf | Proposes microservice migration... |
| [Screenshot-A] | current-arch.png | Current monolithic architecture... |

## Participants

### Dr. Keiko Tanaka — Regulatory Expert
**Background**: [background]
**Core Values**: [values]
**Initial Stance**: [stance]

### Prof. Min-jun Kim — Innovation Evangelist
...

## Discussion

### Turn 1 — Dr. Tanaka
[statement]

> 💭 *Inner thoughts*: [inner thoughts — included when --show-thoughts]

**Facilitator**: [intervention if any]

### Turn 2 — Prof. Kim
...

## Synthesis

### Areas of Consensus
- ...

### Remaining Disagreements
- ...

### Recommendations
- ...

### Final Positions

| Persona | Final Stance | Readiness | Key Concessions |
|---------|-------------|-----------|-----------------|
| Dr. Tanaka | ... | 0.85 | ... |
| Prof. Kim | ... | 0.92 | ... |
| Alex Chen | ... | 0.78 | ... |
```

### 3. JSON State (`discussion.json`)

Complete discussion state for re-rendering, analysis, or archival:

```json
{
  "topic_analysis": { ... },
  "personas": [ ... ],
  "messages": [ ... ],
  "inner_thoughts": { "persona_name": [ ... ] },
  "facilitator_actions": [ ... ],
  "convergence_history": [ ... ],
  "token_usage": { "pro": 45200, "flash": 12100 },
  "metadata": { "started_at": "...", "ended_at": "...", "version": "..." }
}
```

Enables:
- `magi2 render --state discussion.json --lang ko` — re-render in Korean
- `magi2 render --state discussion.json --html` — generate static HTML
- Post-hoc analysis of discussion dynamics

## Language Strategy: Native Language Mode

### Principle

When `--lang` is specified, all LLMs generate directly in the target language.
No post-hoc translation — eliminates extra API calls and latency entirely.

### Processing Pipeline

```
Input (any language)
  │
  ▼
--lang ja specified?
  ├─ Yes → LANGUAGE directive appended to all system prompts
  │        All LLM output generated directly in Japanese
  └─ No  → Default English output
```

### How It Works

Each system prompt receives a LANGUAGE directive when `--lang` is set:

| Component | Directive |
|-----------|-----------|
| Topic analysis (facilitator) | "Write ALL output in {lang}" — names, archetypes, stances all in target language |
| Flow control (facilitator) | "Write the 'intervention' field in {lang}" — internal fields stay English |
| Persona response | "Write statement, key_points, stance_evolution, convergence_conditions in {lang}" |
| Synthesis report | "Write the entire report in {lang}" |

### What Stays in English

Even with `--lang ja`, these remain English (internal only, not displayed):
- Facilitator's `next_speaker`, `strategic_intent`, `hidden_dynamics`
- Persona's `inner_thoughts` (LLM chooses naturally, often English)
- Convergence signals (numerical)

### Design Decision: Why Not Post-hoc Translation?

Initially designed with an English-internal + translation-at-output approach
(ir-tracker pattern). Abandoned because:
1. Translation added 4-5 extra API calls per turn → unacceptable latency
2. Gemini Pro/Flash generate high-quality output in Japanese directly
3. Native generation preserves cultural nuance better than translation
4. Simpler architecture — no translator module in the critical path

## Security

- Prompt injection defense: topic input wrapped in nonce-tagged XML
- No credentials in output files
- Vertex AI authentication via ADC (gcloud auth)

## UI Architecture: Web + Console Split

### Principle

- **Web UI (browser)** — Discussion visualization, interaction, all user-facing output
- **Console (terminal)** — System monitoring, API call logs, token usage, errors

```
┌───────────────┐     ┌──────────────────────────────────┐
│   Terminal     │     │        Browser (Web UI)           │
│               │     │                                  │
│ System log:   │     │ ┌──────────────────────────────┐ │
│ [API] POST    │     │ │ Discussion Timeline           │ │
│  gemini-pro   │     │ │                              │ │
│  tokens: 2.4K │     │ │ 💬 Dr. Tanaka: "We must..." │ │
│  latency: 1.2s│     │ │ 💬 Prof. Kim: "However..."  │ │
│ [API] POST    │     │ │ 🎯 Facilitator: "Let's..."  │ │
│  gemini-flash │     │ │                              │ │
│  tokens: 800  │     │ ├──────────────────────────────┤ │
│  latency: 0.4s│     │ │ Persona Cards (3 panels)     │ │
│ [CONV] Turn 5 │     │ │ ┌────┐ ┌────┐ ┌────┐       │ │
│  convergence: │     │ │ │ A  │ │ B  │ │ C  │       │ │
│  0.35         │     │ │ └────┘ └────┘ └────┘       │ │
│ [TOKEN] Total │     │ ├──────────────────────────────┤ │
│  pro: 45.2K   │     │ │ Controls & Status Bar        │ │
│  flash: 12.1K │     │ └──────────────────────────────┘ │
│  cost: ~$0.08 │     │                                  │
└───────────────┘     └──────────────────────────────────┘
     stderr                    http://127.0.0.1:8080
```

### Web UI Features

#### Discussion View (Main)

- **Timeline** — Real-time discussion stream (newest at bottom, auto-scroll)
- **Persona cards** — 3 floating panels showing:
  - Name, archetype, portrait placeholder
  - Current stance (live-updating)
  - Readiness to converge (0.0–1.0 progress bar)
  - Convergence conditions
- **Facilitator interventions** — Visually distinct cards between persona turns
- **Convergence gauge** — Overall convergence level in the status bar
- **Phase indicator** — Current discussion phase label

#### Thought Bubble Toggle

Toggle button in the UI to show/hide inner thoughts alongside public statements:

```
┌──────────────────────────────────────────┐
│ Dr. Tanaka (Regulatory Expert)     Turn 5│
│                                          │
│ 💭 "Their cost argument is actually      │
│    valid but I can't concede that yet.   │
│    If I acknowledge costs now, I lose     │
│    leverage on the safety requirements." │
│                                          │
│ 💬 "While cost considerations are        │
│    important, we must prioritize safety  │
│    frameworks before discussing budget." │
└──────────────────────────────────────────┘
```

When hidden, only the 💬 statement is shown. Toggle applies retroactively
to all past turns (data is already in the state).

#### Facilitator Insight Toggle

Shows the facilitator's hidden_dynamics and strategic_intent alongside each
flow decision. Reveals *why* the facilitator chose a particular speaker or
injected a particular intervention.

#### Attachment Preview

For multimodal discussions, embedded previews of attached files:
- PDF: first page thumbnail
- Images: inline preview
- Audio/Video: player widget
- All: original filename + facilitator's digest summary

#### Controls

- **Start Discussion** — Input topic text + file attachments
- **Pause/Resume** — Pause the discussion loop
- **Language toggle** — Switch display language (EN/JA/etc.) live
- **Export** — Download as Markdown or static HTML

#### Real-time Updates (WebSocket)

The discussion engine pushes events via WebSocket:

```python
class WSEvent(BaseModel):
    type: str           # "persona_turn", "facilitator_action",
                        # "convergence_update", "phase_change",
                        # "discussion_complete"
    data: dict          # Event-specific payload
```

Browser receives events and updates the DOM incrementally.
No polling, no full-page refresh.

### Console Output (Terminal / stderr)

The terminal serves as a system monitoring dashboard:

```
[2026-04-01 14:30:00] [INIT] Topic analyzed (flash, 1.2K tokens, 0.8s)
[2026-04-01 14:30:01] [INIT] 3 personas designed: Dr. Tanaka, Prof. Kim, Alex Chen
[2026-04-01 14:30:01] [INIT] 2 attachments digested: [Design-PDF], [Screenshot-A]
[2026-04-01 14:30:02] [WEB]  Server started at http://127.0.0.1:8080
[2026-04-01 14:30:05] [TURN] #1 Speaker: Dr. Tanaka (pro, 2.4K tokens, 1.2s)
[2026-04-01 14:30:07] [FLOW] Facilitator action (flash, 800 tokens, 0.4s)
[2026-04-01 14:30:07] [FLOW]   next_speaker=Prof. Kim, convergence=0.12
[2026-04-01 14:30:09] [TURN] #2 Speaker: Prof. Kim (pro, 2.1K tokens, 1.1s)
[2026-04-01 14:30:11] [FLOW] Facilitator action (flash, 820 tokens, 0.3s)
[2026-04-01 14:30:11] [FLOW]   next_speaker=Alex Chen, convergence=0.18
...
[2026-04-01 14:35:22] [CONV] Convergence reached: 0.87 (turn 24)
[2026-04-01 14:35:30] [SYNTH] Report generated (pro, 4.2K tokens, 2.1s)
[2026-04-01 14:35:30] [COST] Session total: pro=45.2K flash=12.1K tokens
[2026-04-01 14:35:30] [SAVE] Exported to results/magi2_20260401_143000.md
```

Categories:
- `[INIT]` — Startup, topic analysis, persona design
- `[WEB]` — Server lifecycle
- `[TURN]` — Persona turn (model, tokens, latency)
- `[FLOW]` — Facilitator action (convergence level, next speaker)
- `[CONV]` — Convergence events
- `[SYNTH]` — Report generation
- `[TRANS]` — Translation calls
- `[COST]` — Token usage and estimated cost
- `[ERR]` — Errors and retries

## Differences from v1 Summary

1. **Rich personality model** — v1 had 3-line descriptions. v2 has full personality
   profiles with communication, cognition, emotion, interpersonal patterns, blind spots.
2. **Dual memory (inner/public)** — Private thoughts + public statements. Creates
   natural gaps between thinking and speaking, enabling strategic behavior.
3. **Facilitator reads inner thoughts** — Intelligent flow control based on subtext.
4. **Streaming + CoT** — Real-time token-by-token output with Gemini thinking visible.
5. **Consensus check** — Before closing, facilitator asks low-readiness personas directly.
6. **Native language mode** — `--lang ja` generates directly in target language. No translation latency.
7. **Persona icons** — Emoji icons assigned per persona, displayed in UI.
8. **Web UI** — WebSocket real-time, not TUI. Thought bubbles, CoT, convergence gauge.
9. **原稿用紙/墨色 themes** — Warm manuscript paper light theme, sumi-ink dark theme.
10. **Multimodal input** — PDF, images, audio, video as discussion topics.
11. **Replay mode** — Re-watch saved discussions without LLM calls.
12. **No speaker heuristic** — Facilitator LLM decides, informed by inner thoughts.
13. **No history truncation** — 1M tokens eliminates the need.
14. **Gradient convergence** — Replaces binary votes with continuous 0.0–1.0 signals.
