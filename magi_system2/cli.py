"""CLI entry point for magi-system2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from magi_system2.console import log


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-persona AI discussion system",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── discuss (default) ──
    discuss_p = subparsers.add_parser("discuss", help="Start a discussion")
    discuss_p.add_argument("topic", nargs="?", default="", help="Topic text (simple mode)")
    discuss_p.add_argument("--file", "-f", default="", help="Topic from markdown file")
    discuss_p.add_argument("--attach", action="append", default=[], help="Attach file (repeatable)")
    discuss_p.add_argument("--max-turns", type=int, default=30, help="Max discussion turns")
    discuss_p.add_argument("--lang", default="", help="Output language (e.g. ja)")
    discuss_p.add_argument("--native-discussion", action="store_true",
                           help="Run discussion in input language instead of English")
    discuss_p.add_argument("--show-thoughts", action="store_true",
                           help="Show inner thought bubbles in Web UI")
    discuss_p.add_argument("--show-facilitator", action="store_true",
                           help="Show facilitator hidden analysis in Web UI")
    discuss_p.add_argument("--save", "-s", action="store_true", help="Auto-save results")
    discuss_p.add_argument("--output", "-o", default="", help="Output directory")
    discuss_p.add_argument("--port", "-p", type=int, default=8080, help="Web UI port")
    discuss_p.add_argument("--host", default="127.0.0.1", help="Web UI host")

    # ── export ──
    export_p = subparsers.add_parser("export", help="Export discussion from saved state")
    export_p.add_argument("--state", required=True, help="Path to discussion.json")
    export_p.add_argument("--markdown", action="store_true", help="Export as Markdown")
    export_p.add_argument("--html", action="store_true", help="Export as static HTML")
    export_p.add_argument("--lang", default="", help="Output language")
    export_p.add_argument("--show-thoughts", action="store_true")
    export_p.add_argument("-o", "--output", default="", help="Output file path")

    # ── render ──
    render_p = subparsers.add_parser("render", help="Re-render in another language")
    render_p.add_argument("--state", required=True, help="Path to discussion.json")
    render_p.add_argument("--lang", required=True, help="Target language")
    render_p.add_argument("-o", "--output", default="", help="Output file path")

    args = parser.parse_args()

    # Default to discuss if no subcommand
    if args.command is None:
        # Check if there's a positional arg (topic)
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            args.command = "discuss"
            args.topic = sys.argv[1]
            args.file = ""
            args.attach = []
            args.max_turns = 30
            args.lang = ""
            args.native_discussion = False
            args.show_thoughts = False
            args.show_facilitator = False
            args.save = False
            args.output = ""
            args.port = 8080
            args.host = "127.0.0.1"
        else:
            parser.print_help()
            sys.exit(1)

    if args.command == "discuss":
        _run_discuss(args)
    elif args.command == "export":
        _run_export(args)
    elif args.command == "render":
        _run_render(args)


def _run_discuss(args) -> None:
    from magi_system2.discussion import run_discussion
    from magi_system2.web import create_app
    import uvicorn

    # Resolve topic text
    topic = args.topic
    if args.file:
        topic = Path(args.file).read_text(encoding="utf-8")
    if not topic:
        print("Error: provide a topic as argument or via --file", file=sys.stderr)
        sys.exit(1)

    # Create web app with discussion config
    app = create_app(
        topic_text=topic,
        attachment_paths=args.attach or [],
        max_turns=args.max_turns,
        lang=args.lang,
        native_discussion=args.native_discussion,
        show_thoughts=args.show_thoughts,
        show_facilitator=args.show_facilitator,
        save=args.save,
        output_dir=args.output,
    )

    log("WEB", f"Starting at http://{args.host}:{args.port}")
    log("INIT", f"Topic: {topic[:100]}...")
    if args.attach:
        log("INIT", f"Attachments: {', '.join(args.attach)}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


def _run_export(args) -> None:
    from magi_system2.save import export_markdown, export_html
    from magi_system2.models import DiscussionState

    state_data = json.loads(Path(args.state).read_text(encoding="utf-8"))
    state = DiscussionState(**state_data)

    if args.markdown:
        md = export_markdown(state, lang=args.lang, show_thoughts=args.show_thoughts)
        output = args.output or "discussion.md"
        Path(output).write_text(md, encoding="utf-8")
        log("SAVE", f"Markdown exported to {output}")

    if args.html:
        html = export_html(state, lang=args.lang, show_thoughts=args.show_thoughts)
        output = args.output or "discussion.html"
        Path(output).write_text(html, encoding="utf-8")
        log("SAVE", f"HTML exported to {output}")


def _run_render(args) -> None:
    from magi_system2.save import export_markdown
    from magi_system2.models import DiscussionState

    state_data = json.loads(Path(args.state).read_text(encoding="utf-8"))
    state = DiscussionState(**state_data)

    md = export_markdown(state, lang=args.lang)
    output = args.output or f"discussion-{args.lang}.md"
    Path(output).write_text(md, encoding="utf-8")
    log("SAVE", f"Rendered to {output}")


if __name__ == "__main__":
    main()
