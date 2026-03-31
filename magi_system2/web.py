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


def _sync_broadcast(event_type: str, data: dict) -> None:
    """Synchronous wrapper for broadcast (called from discussion thread)."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_broadcast(event_type, data))
    else:
        loop.run_until_complete(_broadcast(event_type, data))


def create_app(
    topic_text: str,
    attachment_paths: list[str],
    max_turns: int = 30,
    lang: str = "",
    native_discussion: bool = False,
    show_thoughts: bool = False,
    show_facilitator: bool = False,
    save: bool = False,
    output_dir: str = "",
) -> FastAPI:
    """Create the FastAPI application."""
    global _discussion_config

    app = FastAPI(title="magi-system2", docs_url=None, redoc_url=None)

    # Store config for later use
    _discussion_config = {
        "topic_text": topic_text,
        "attachment_paths": attachment_paths,
        "max_turns": max_turns,
        "lang": lang,
        "native_discussion": native_discussion,
        "show_thoughts": show_thoughts,
        "show_facilitator": show_facilitator,
        "save": save,
        "output_dir": output_dir,
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
        await ws.accept()
        _clients.append(ws)
        log("WEB", f"Client connected ({len(_clients)} total)")

        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)

                if msg.get("action") == "start":
                    # Run discussion in background thread
                    asyncio.get_event_loop().run_in_executor(
                        None, _run_discussion_thread
                    )
                elif msg.get("action") == "get_config":
                    await ws.send_text(json.dumps({
                        "type": "config",
                        "data": {
                            "topic": _discussion_config["topic_text"][:200],
                            "attachments": _discussion_config["attachment_paths"],
                            "max_turns": _discussion_config["max_turns"],
                            "show_thoughts": _discussion_config["show_thoughts"],
                            "show_facilitator": _discussion_config["show_facilitator"],
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

    def on_event(event_type: str, data: dict) -> None:
        """Bridge discussion events to WebSocket broadcast."""
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(_broadcast(event_type, data), loop)
        except Exception:
            pass  # Event loop may not be available during shutdown

    _state = run_discussion(
        topic_text=config["topic_text"],
        attachment_paths=config["attachment_paths"],
        max_turns=config["max_turns"],
        on_event=on_event,
    )

    # Auto-save if requested
    if config["save"] and config["output_dir"]:
        path = save_state(_state, config["output_dir"])
        log("SAVE", f"State saved to {path}")
