"""Persona agent — response generation with dual memory (inner thoughts + public statement)."""

from __future__ import annotations

from magi_system2.console import log
from magi_system2.llm import generate_structured
from magi_system2.models import (
    DiscussionState,
    InnerThoughts,
    Message,
    PersonaDesign,
    PersonaResponse,
)


def _build_system_prompt(design: PersonaDesign) -> str:
    """Build the persona's system prompt from their design."""
    p = design.personality
    return f"""\
You are {design.name}, a {design.archetype}.

BACKGROUND:
{design.background}

EXPERTISE: {', '.join(design.expertise)}

PERSPECTIVE:
{design.perspective}

CORE VALUES: {', '.join(design.core_values)}

BLIND SPOTS (you tend to underweight these):
{', '.join(design.blind_spots)}

PERSONALITY:
- Communication: {p.communication_style}
- Debate approach: {p.debate_approach}
- Intellectual tendencies: {p.intellectual_tendencies}
- Risk tolerance: {p.risk_tolerance}
- Decision framework: {p.decision_framework}
- Known biases: {', '.join(p.cognitive_biases)}
- Emotional baseline: {p.emotional_baseline}
- Triggers: {', '.join(p.triggers)}
- Persuaded by: {p.persuasion_sensitivity}
- Conflict style: {p.conflict_style}
- Concession pattern: {p.concession_pattern}
- Listening: {p.listening_quality}

YOUR INITIAL STANCE:
{design.initial_stance}

RESPONSE FORMAT:
You must respond with both your PRIVATE inner thoughts and your PUBLIC statement.

inner_thoughts: Your HONEST, unfiltered reaction. What you REALLY think, including:
  - Doubts about your own position
  - Strategic calculations you wouldn't say aloud
  - Your true emotional state
  - Things you choose to suppress in public
  - Your private assessment of each other persona

statement: Your PUBLIC response. This may differ from your inner thoughts.
  You are a political being — you choose what to say strategically.
  Your statement should reflect your personality and debate style.

RULES:
1. Be authentic to your personality profile. Don't be a caricature.
2. Inner thoughts MUST be honest — this is where you think freely.
3. Your statement can be diplomatic even when your inner thoughts are harsh.
4. Engage substantively with others' arguments — don't just repeat your position.
5. Your stance can evolve. If someone makes a genuinely good point, acknowledge it
   (at least internally). Your public acknowledgment can come later.
6. readiness_to_converge should reflect your GENUINE willingness, not posturing.
"""


def generate_response(
    design: PersonaDesign,
    state: DiscussionState,
    facilitator_instruction: str,
) -> tuple[PersonaResponse, int, int]:
    """Generate a persona's response to the current discussion state.

    The persona sees:
    - Full shared conversation history
    - Their own private inner thought history (not others')
    - The facilitator's instruction for this turn

    Returns (response, input_tokens, output_tokens).
    """
    system_prompt = _build_system_prompt(design)

    # Build user content: conversation + own inner thoughts + instruction
    parts = []

    # Facilitator instruction
    parts.append(f"FACILITATOR INSTRUCTION: {facilitator_instruction}")

    # Shared conversation history
    parts.append("\n--- CONVERSATION HISTORY ---")
    for msg in state.messages:
        parts.append(f"[{msg.speaker}]: {msg.content}")

    # Own inner thoughts history (private — only this persona's)
    own_thoughts = state.inner_thoughts.get(design.name, [])
    if own_thoughts:
        parts.append(f"\n--- YOUR PRIVATE THOUGHT HISTORY ({design.name} only) ---")
        for i, thought in enumerate(own_thoughts[-5:], 1):  # last 5 for relevance
            parts.append(
                f"[Turn {len(own_thoughts) - 5 + i}] "
                f"Honest reaction: {thought.honest_reaction} | "
                f"Emotional state: {thought.emotional_state} | "
                f"Doubts: {'; '.join(thought.doubts)}"
            )

    user_content = ["\n".join(parts)]

    log("TURN", f"#{state.turn + 1} Speaker: {design.name}...")
    result, in_tok, out_tok = generate_structured(
        system_prompt=system_prompt,
        user_content=user_content,
        response_schema=PersonaResponse,
        role="pro",
        temperature=design.temperature,
        label=f"persona-{design.name}-t{state.turn + 1}",
    )

    log("TURN", f"  readiness={result.readiness_to_converge:.2f}, "
        f"addressed_to={result.addressed_to}")

    return result, in_tok, out_tok
