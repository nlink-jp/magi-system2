"""Console system log — terminal output for monitoring API calls, tokens, and errors."""

from __future__ import annotations

import sys
from datetime import datetime

# ANSI colors for categories
_COLORS = {
    "INIT": "\033[36m",   # cyan
    "WEB": "\033[35m",    # magenta
    "TURN": "\033[32m",   # green
    "FLOW": "\033[33m",   # yellow
    "CONV": "\033[34m",   # blue
    "SYNTH": "\033[36m",  # cyan
    "TRANS": "\033[35m",  # magenta
    "COST": "\033[33m",   # yellow
    "API": "\033[90m",    # gray
    "ERR": "\033[31m",    # red
    "SAVE": "\033[32m",   # green
}
_RESET = "\033[0m"


def log(category: str, message: str, *, level: str = "info") -> None:
    """Write a categorized log line to stderr.

    Args:
        category: Log category (INIT, TURN, FLOW, etc.)
        message: Log message.
        level: "info", "warn", or "error".
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = _COLORS.get(category, "")
    prefix = f"[{ts}] {color}[{category}]{_RESET}"

    if level == "error":
        prefix = f"[{ts}] \033[31m[{category}]{_RESET}"
    elif level == "warn":
        prefix = f"[{ts}] \033[33m[{category}]{_RESET}"

    print(f"{prefix} {message}", file=sys.stderr)


def log_token_summary(pro_input: int, pro_output: int, flash_input: int, flash_output: int) -> None:
    """Log a session token usage summary."""
    pro_total = pro_input + pro_output
    flash_total = flash_input + flash_output
    total = pro_total + flash_total
    log("COST", f"Session total: Pro {pro_total:,} ({pro_input:,}in/{pro_output:,}out) "
        f"Flash {flash_total:,} ({flash_input:,}in/{flash_output:,}out) "
        f"Total {total:,}")
