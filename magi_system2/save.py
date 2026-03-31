"""Save and export — Markdown, static HTML, JSON state."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from magi_system2.models import DiscussionState


def save_state(state: DiscussionState, output_dir: str) -> str:
    """Save complete discussion state as JSON for re-rendering.

    Returns the output file path.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = state.started_at.strftime("%Y%m%d_%H%M%S")
    path = str(Path(output_dir) / f"magi2_{ts}.json")
    Path(path).write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path


def export_markdown(
    state: DiscussionState,
    lang: str = "",
    show_thoughts: bool = False,
) -> str:
    """Export discussion as Markdown report.

    Translation is applied if lang is specified (requires LLM call).
    """
    lines = ["# MAGI System 2 — Discussion Report", ""]

    # Metadata
    lines.append(f"**Topic**: {state.topic_analysis.summary}")
    if state.started_at:
        lines.append(f"**Date**: {state.started_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Turns**: {state.turn}")
    convergence_label = "Achieved" if state.is_converged else "Not reached"
    if state.convergence_history:
        final_level = state.convergence_history[-1].facilitator_assessment
        convergence_label += f" ({final_level:.2f})"
    lines.append(f"**Convergence**: {convergence_label}")
    lines.append(f"**Tokens**: Pro {state.token_usage.pro_total:,} / Flash {state.token_usage.flash_total:,}")
    lines.append("")

    # Attachments
    if state.topic_analysis.attachment_digests:
        lines.append("## Attachments")
        lines.append("")
        lines.append("| # | File | Summary |")
        lines.append("|---|------|---------|")
        for d in state.topic_analysis.attachment_digests:
            lines.append(f"| {d.reference_label} | {d.filename} | {d.summary} |")
        lines.append("")

    # Participants
    lines.append("## Participants")
    lines.append("")
    for p in state.topic_analysis.personas:
        lines.append(f"### {p.name} — {p.archetype}")
        lines.append(f"**Background**: {p.background}")
        lines.append(f"**Core Values**: {', '.join(p.core_values)}")
        lines.append(f"**Initial Stance**: {p.initial_stance}")
        lines.append("")

    # Discussion
    lines.append("## Discussion")
    lines.append("")
    for msg in state.messages:
        if msg.content.startswith("[Synthesis Report]"):
            continue  # Handled separately

        if msg.role == "facilitator":
            lines.append(f"**Facilitator**: {msg.content}")
            lines.append("")
        else:
            prefix = ""
            if msg.content.startswith("[Final Statement]"):
                prefix = " (Final)"
            lines.append(f"### Turn {msg.turn + 1} — {msg.speaker}{prefix}")
            content = msg.content.replace("[Final Statement] ", "")
            lines.append(content)
            lines.append("")

            # Inner thoughts (optional)
            if show_thoughts:
                thoughts_list = state.inner_thoughts.get(msg.speaker, [])
                # Find the matching thought for this turn
                # Inner thoughts are stored sequentially per persona
                persona_turns = [m for m in state.messages if m.speaker == msg.speaker and m.role == "persona"]
                idx = None
                for i, pt in enumerate(persona_turns):
                    if pt.turn == msg.turn:
                        idx = i
                        break
                if idx is not None and idx < len(thoughts_list):
                    t = thoughts_list[idx]
                    lines.append(f"> 💭 *Inner thoughts*: {t.honest_reaction}")
                    if t.doubts:
                        lines.append(f"> *Doubts*: {'; '.join(t.doubts)}")
                    lines.append(f"> *Emotional state*: {t.emotional_state}")
                    lines.append("")

    # Synthesis
    synthesis_msgs = [m for m in state.messages if m.content.startswith("[Synthesis Report]")]
    if synthesis_msgs:
        lines.append("## Synthesis")
        lines.append("")
        report_text = synthesis_msgs[-1].content.replace("[Synthesis Report]\n\n", "")
        lines.append(report_text)
        lines.append("")

    # Final positions
    lines.append("## Final Positions")
    lines.append("")
    lines.append("| Persona | Readiness | Key Stance |")
    lines.append("|---------|-----------|-----------|")
    if state.convergence_history:
        final = state.convergence_history[-1]
        for p in state.topic_analysis.personas:
            readiness = final.persona_readiness.get(p.name, 0.0)
            # Find last statement
            last_stmt = ""
            for m in reversed(state.messages):
                if m.speaker == p.name and m.role == "persona":
                    last_stmt = m.content[:100] + "..." if len(m.content) > 100 else m.content
                    break
            lines.append(f"| {p.name} | {readiness:.2f} | {last_stmt} |")
    lines.append("")

    return "\n".join(lines)


def export_html(
    state: DiscussionState,
    lang: str = "",
    show_thoughts: bool = False,
) -> str:
    """Export discussion as self-contained static HTML.

    TODO: Implement full HTML template with CSS/JS inlined.
    For now, wraps the Markdown in a basic HTML structure.
    """
    md = export_markdown(state, lang=lang, show_thoughts=show_thoughts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MAGI System 2 — Discussion Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
pre {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{md}</pre>
</body>
</html>"""
