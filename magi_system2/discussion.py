"""Discussion engine — main loop, state management, convergence detection."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from magi_system2.console import log, log_token_summary
from magi_system2.facilitator import analyze_topic, decide_next_action, synthesize_report
from magi_system2.models import (
    ConvergenceSnapshot,
    DiscussionState,
    Message,
    PersonaDesign,
    TopicAnalysis,
)
from magi_system2.persona import generate_response

DEFAULT_MAX_TURNS = 30
MIN_TURNS_BEFORE_CONVERGENCE = 8
CONVERGENCE_THRESHOLD = 0.8
PERSONA_READINESS_AVG = 0.7
PERSONA_READINESS_MIN = 0.5

# Callback type for real-time UI updates
EventCallback = Callable[[str, dict], None]


def run_discussion(
    topic_text: str,
    attachment_paths: list[str] | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    on_event: EventCallback | None = None,
) -> DiscussionState:
    """Run a complete multi-persona discussion.

    Args:
        topic_text: The topic to discuss (plain text or markdown).
        attachment_paths: Optional file paths for multimodal input.
        max_turns: Maximum number of persona turns.
        on_event: Callback for real-time UI updates.

    Returns:
        Complete DiscussionState for export/rendering.
    """
    def emit(event_type: str, data: dict) -> None:
        if on_event:
            on_event(event_type, data)

    # ── Phase 0: Topic analysis & persona design ──
    emit("activity", {"who": "Facilitator", "what": "Analyzing topic and designing personas..."})
    analysis, in_tok, out_tok = analyze_topic(topic_text, attachment_paths)

    state = DiscussionState(
        topic_analysis=analysis,
        started_at=datetime.now(),
    )
    state.token_usage.add_flash(in_tok, out_tok)

    # Initialize inner thoughts storage for each persona
    for persona in analysis.personas:
        state.inner_thoughts[persona.name] = []

    emit("topic_analyzed", {
        "summary": analysis.summary,
        "personas": [{"name": p.name, "archetype": p.archetype} for p in analysis.personas],
        "attachments": [d.reference_label for d in analysis.attachment_digests],
    })

    # Map persona names to designs for quick lookup
    persona_map: dict[str, PersonaDesign] = {p.name: p for p in analysis.personas}

    # ── Phase 1: Discussion loop ──
    log("INIT", f"Discussion starting: {len(analysis.personas)} personas, max {max_turns} turns")

    while state.turn < max_turns and not state.is_converged:
        # Step 1: Facilitator decides next action
        emit("activity", {"who": "Facilitator", "what": "Deciding next speaker..."})
        action, in_tok, out_tok = decide_next_action(state, max_turns)
        state.token_usage.add_flash(in_tok, out_tok)
        state.facilitator_actions.append(action)
        state.phase = action.discussion_status

        # Step 2: Inject facilitator intervention if any
        if action.intervention:
            fac_msg = Message(
                turn=state.turn,
                speaker="facilitator",
                role="facilitator",
                content=action.intervention,
            )
            state.messages.append(fac_msg)
            emit("facilitator_intervention", {
                "content": action.intervention,
                "phase": action.discussion_status,
            })

        # Step 3: Selected persona generates response
        speaker_name = action.next_speaker
        if speaker_name not in persona_map:
            log("ERR", f"Facilitator selected unknown persona: {speaker_name}", level="error")
            # Fallback to first persona
            speaker_name = analysis.personas[0].name

        design = persona_map[speaker_name]
        emit("activity", {"who": speaker_name, "what": f"Thinking... (Turn {state.turn + 1})"})
        response, in_tok, out_tok = generate_response(
            design=design,
            state=state,
            facilitator_instruction=action.instruction,
        )
        state.token_usage.add_pro(in_tok, out_tok)

        # Step 4: Store inner thoughts (private)
        state.inner_thoughts[speaker_name].append(response.inner_thoughts)

        # Step 5: Append public statement to shared history
        persona_msg = Message(
            turn=state.turn,
            speaker=speaker_name,
            role="persona",
            content=response.statement,
        )
        state.messages.append(persona_msg)
        state.turn += 1

        emit("persona_turn", {
            "speaker": speaker_name,
            "archetype": design.archetype,
            "statement": response.statement,
            "key_points": response.key_points,
            "inner_thoughts": response.inner_thoughts.model_dump(),
            "readiness_to_converge": response.readiness_to_converge,
            "stance_evolution": response.stance_evolution,
            "turn": state.turn,
            "phase": state.phase,
        })

        # Step 6: Update convergence tracking
        persona_readiness = {}
        # Collect readiness from latest responses
        for p_name in persona_map:
            # Find latest readiness for each persona
            for fa in reversed(state.facilitator_actions):
                # Use the action's convergence as a proxy for now
                break
            # Use the current response's readiness if it's this persona
            if p_name == speaker_name:
                persona_readiness[p_name] = response.readiness_to_converge
            else:
                # Use last known readiness from convergence history
                if state.convergence_history:
                    prev = state.convergence_history[-1].persona_readiness
                    persona_readiness[p_name] = prev.get(p_name, 0.0)
                else:
                    persona_readiness[p_name] = 0.0

        avg_readiness = sum(persona_readiness.values()) / len(persona_readiness) if persona_readiness else 0.0
        min_readiness = min(persona_readiness.values()) if persona_readiness else 0.0

        snapshot = ConvergenceSnapshot(
            turn=state.turn,
            facilitator_assessment=action.convergence_assessment,
            persona_readiness=persona_readiness,
            average_readiness=avg_readiness,
            is_converged=False,
        )

        # Check convergence conditions
        if (
            state.turn >= MIN_TURNS_BEFORE_CONVERGENCE
            and action.convergence_assessment >= CONVERGENCE_THRESHOLD
            and avg_readiness >= PERSONA_READINESS_AVG
            and min_readiness >= PERSONA_READINESS_MIN
        ):
            snapshot.is_converged = True
            state.is_converged = True
            log("CONV", f"Convergence reached at turn {state.turn}: "
                f"facilitator={action.convergence_assessment:.2f}, "
                f"avg_readiness={avg_readiness:.2f}")

        state.convergence_history.append(snapshot)

        emit("convergence_update", {
            "turn": state.turn,
            "facilitator_assessment": action.convergence_assessment,
            "persona_readiness": persona_readiness,
            "is_converged": state.is_converged,
        })

    # ── Phase 2: Closing ──
    if state.is_converged:
        log("CONV", "Discussion converged. Generating closing statements...")
    else:
        log("CONV", f"Max turns ({max_turns}) reached without convergence.")

    # Generate closing statements from each persona
    for persona in analysis.personas:
        emit("activity", {"who": persona.name, "what": "Writing final statement..."})
        closing_instruction = (
            "The discussion is concluding. Give your FINAL STATEMENT: "
            "what you agree with, what you still disagree on, and your "
            "recommendation. Be honest and specific."
        )
        response, in_tok, out_tok = generate_response(
            design=persona,
            state=state,
            facilitator_instruction=closing_instruction,
        )
        state.token_usage.add_pro(in_tok, out_tok)
        state.inner_thoughts[persona.name].append(response.inner_thoughts)

        closing_msg = Message(
            turn=state.turn,
            speaker=persona.name,
            role="persona",
            content=f"[Final Statement] {response.statement}",
        )
        state.messages.append(closing_msg)
        state.turn += 1

        emit("closing_statement", {
            "speaker": persona.name,
            "statement": response.statement,
            "readiness_to_converge": response.readiness_to_converge,
            "inner_thoughts": response.inner_thoughts.model_dump(),
        })

    # ── Phase 3: Synthesis ──
    emit("activity", {"who": "Facilitator", "what": "Writing synthesis report..."})
    report, in_tok, out_tok = synthesize_report(state)
    state.token_usage.add_pro(in_tok, out_tok)

    # Store report as a facilitator message
    state.messages.append(Message(
        turn=state.turn,
        speaker="facilitator",
        role="facilitator",
        content=f"[Synthesis Report]\n\n{report}",
    ))

    state.ended_at = datetime.now()
    state.phase = "completed"

    emit("discussion_complete", {
        "report": report,
        "turns": state.turn,
        "converged": state.is_converged,
        "token_usage": state.token_usage.model_dump(),
    })

    log_token_summary(
        state.token_usage.pro_input,
        state.token_usage.pro_output,
        state.token_usage.flash_input,
        state.token_usage.flash_output,
    )

    return state
