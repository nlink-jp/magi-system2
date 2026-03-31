"""Web UI — FastAPI app with WebSocket for real-time discussion updates."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from magi_system2.console import log
from magi_system2.discussion import run_discussion
from magi_system2.models import DiscussionState
from magi_system2.save import save_state

_HERE = Path(__file__).parent

# Connected WebSocket clients
_clients: list[WebSocket] = []

# Discussion state (shared across the app)
_state: DiscussionState | None = None
_discussion_config: dict[str, Any] = {}
_event_loop: asyncio.AbstractEventLoop | None = None


async def _broadcast(event_type: str, data: dict) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    message = json.dumps({"type": event_type, "data": data}, default=str)
    disconnected = []
    for ws in _clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _clients.remove(ws)


def create_replay_app(state: DiscussionState) -> FastAPI:
    """Create a replay-mode app from a saved discussion state."""
    return create_app(
        topic_text=state.topic_analysis.summary,
        attachment_paths=[],
        show_thoughts=True,
        show_facilitator=True,
        _replay_state=state,
    )


def create_app(
    topic_text: str = "",
    attachment_paths: list[str] | None = None,
    max_turns: int = 30,
    lang: str = "",
    native_discussion: bool = False,
    show_thoughts: bool = False,
    show_facilitator: bool = False,
    save: bool = False,
    output_dir: str = "",
    _replay_state: DiscussionState | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    global _discussion_config

    app = FastAPI(title="magi-system2", docs_url=None, redoc_url=None)

    # Store config for later use
    _discussion_config = {
        "topic_text": topic_text,
        "attachment_paths": attachment_paths or [],
        "max_turns": max_turns,
        "lang": lang,
        "native_discussion": native_discussion,
        "show_thoughts": show_thoughts,
        "show_facilitator": show_facilitator,
        "save": save,
        "output_dir": output_dir,
        "replay_mode": _replay_state is not None,
        "_replay_state": _replay_state,
    }

    # Static files
    static_dir = _HERE / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        template = (_HERE / "templates" / "index.html").read_text(encoding="utf-8")
        return template

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        global _event_loop
        await ws.accept()
        _clients.append(ws)
        _event_loop = asyncio.get_running_loop()
        log("WEB", f"Client connected ({len(_clients)} total)")

        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)

                if msg.get("action") == "start":
                    log("WEB", "Discussion start requested")
                    _event_loop.run_in_executor(None, _run_discussion_thread)
                elif msg.get("action") == "get_config":
                    await ws.send_text(json.dumps({
                        "type": "config",
                        "data": {
                            "topic": _discussion_config.get("topic_text", "")[:200],
                            "attachments": _discussion_config.get("attachment_paths", []),
                            "max_turns": _discussion_config.get("max_turns", 30),
                            "show_thoughts": _discussion_config.get("show_thoughts", False),
                            "show_facilitator": _discussion_config.get("show_facilitator", False),
                            "replay_mode": _discussion_config.get("replay_mode", False),
                        },
                    }))

        except WebSocketDisconnect:
            _clients.remove(ws)
            log("WEB", f"Client disconnected ({len(_clients)} total)")

    @app.get("/api/state")
    async def api_state():
        if _state is None:
            return {"status": "not_started"}
        return _state.model_dump(mode="json")

    return app


def _run_discussion_thread() -> None:
    """Run the discussion in a background thread."""
    global _state

    config = _discussion_config

    if config.get("replay_mode"):
        _replay_from_state()
        return

    def on_event(event_type: str, data: dict) -> None:
        """Bridge discussion events to WebSocket broadcast."""
        if _event_loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(_broadcast(event_type, data), _event_loop)
        except Exception as e:
            log("ERR", f"Broadcast failed: {e}", level="warn")

    _state = run_discussion(
        topic_text=config["topic_text"],
        attachment_paths=config["attachment_paths"],
        max_turns=config["max_turns"],
        on_event=on_event,
        lang=config.get("lang", ""),
    )

    # Auto-save if requested
    if config.get("save") and config.get("output_dir"):
        path = save_state(_state, config["output_dir"])
        log("SAVE", f"State saved to {path}")


def _replay_from_state() -> None:
    """Replay a saved discussion state as WebSocket events (no LLM calls)."""
    import time

    global _state
    config = _discussion_config
    state = config.get("_replay_state")
    if state is None:
        return

    _state = state

    def emit(event_type: str, data: dict) -> None:
        if _event_loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(_broadcast(event_type, data), _event_loop)
        except Exception:
            pass
        time.sleep(0.3)  # Pacing for visual effect

    # Topic analyzed
    emit("topic_analyzed", {
        "summary": state.topic_analysis.summary,
        "personas": [{"name": p.name, "archetype": p.archetype} for p in state.topic_analysis.personas],
        "attachments": [d.reference_label for d in state.topic_analysis.attachment_digests],
    })

    persona_map = {p.name: p for p in state.topic_analysis.personas}
    turn_thoughts: dict[str, int] = {p.name: 0 for p in state.topic_analysis.personas}
    pro_tokens = 0
    flash_tokens = 0

    for msg in state.messages:
        if msg.content.startswith("[Synthesis Report]"):
            emit("activity", {"who": "Facilitator", "what": "Writing synthesis report..."})
            time.sleep(0.5)
            report = msg.content.replace("[Synthesis Report]\n\n", "")
            emit("discussion_complete", {
                "report": report,
                "turns": state.turn,
                "converged": state.is_converged,
                "token_usage": {
                    "pro": state.token_usage.pro_total,
                    "flash": state.token_usage.flash_total,
                    "total": state.token_usage.total,
                },
            })
            continue

        if msg.role == "facilitator":
            emit("facilitator_intervention", {
                "content": msg.content,
                "phase": state.phase,
            })
        elif msg.role == "persona":
            # Get inner thoughts
            thoughts_data = {}
            thought_idx = turn_thoughts.get(msg.speaker, 0)
            thoughts_list = state.inner_thoughts.get(msg.speaker, [])
            if thought_idx < len(thoughts_list):
                thoughts_data = thoughts_list[thought_idx].model_dump()
                turn_thoughts[msg.speaker] = thought_idx + 1

            # Find convergence for this turn (cs.turn is 1-indexed)
            readiness = 0.0
            convergence_val = 0.0
            for cs in state.convergence_history:
                if cs.turn >= msg.turn + 1:
                    readiness = cs.persona_readiness.get(msg.speaker, 0.0)
                    convergence_val = cs.facilitator_assessment
                    break

            pro_tokens += 3000  # Approximate
            flash_tokens += 1500

            is_final = msg.content.startswith("[Final Statement]")
            statement = msg.content.replace("[Final Statement] ", "") if is_final else msg.content

            if is_final:
                emit("closing_statement", {
                    "speaker": msg.speaker,
                    "statement": statement,
                    "readiness_to_converge": readiness,
                    "inner_thoughts": thoughts_data,
                })
            else:
                emit("persona_turn", {
                    "speaker": msg.speaker,
                    "archetype": persona_map.get(msg.speaker, state.topic_analysis.personas[0]).archetype,
                    "statement": statement,
                    "key_points": [],
                    "inner_thoughts": thoughts_data,
                    "readiness_to_converge": readiness,
                    "stance_evolution": "",
                    "turn": msg.turn + 1,
                    "phase": state.phase,
                    "token_usage": {
                        "pro": pro_tokens,
                        "flash": flash_tokens,
                        "total": pro_tokens + flash_tokens,
                    },
                })

                emit("convergence_update", {
                    "turn": msg.turn + 1,
                    "facilitator_assessment": convergence_val,
                    "persona_readiness": {p.name: 0.0 for p in state.topic_analysis.personas},
                    "is_converged": False,
                })

    log("WEB", "Replay complete")
