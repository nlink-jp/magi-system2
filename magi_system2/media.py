"""Attachment loading and multimodal content parts builder."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from google.genai import types

from magi_system2.console import log

# Supported media types for Gemini
_SUPPORTED_TYPES = {
    # Documents
    "application/pdf",
    # Images
    "image/png", "image/jpeg", "image/gif", "image/webp",
    # Audio
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/flac",
    "audio/mp4", "audio/webm",
    # Video
    "video/mp4", "video/mpeg", "video/webm", "video/quicktime",
}


def detect_mime(path: str) -> str:
    """Detect MIME type from file extension."""
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def load_attachment(path: str) -> types.Part:
    """Load a file as a Gemini content Part.

    Returns a Part with inline_data containing the file bytes and MIME type.
    Raises ValueError if the file type is not supported by Gemini.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Attachment not found: {path}")

    mime = detect_mime(path)
    if mime not in _SUPPORTED_TYPES:
        raise ValueError(
            f"Unsupported media type '{mime}' for {file_path.name}. "
            f"Supported: PDF, images (PNG/JPEG/GIF/WebP), audio (MP3/WAV/OGG/FLAC), "
            f"video (MP4/WebM/MOV)"
        )

    data = file_path.read_bytes()
    log("INIT", f"Loaded attachment: {file_path.name} ({mime}, {len(data):,} bytes)")

    return types.Part.from_bytes(data=data, mime_type=mime)


def build_content_parts(
    text: str,
    attachment_paths: list[str] | None = None,
) -> list:
    """Build a list of content parts for a Gemini API call.

    Combines text content with any attached files into a multimodal
    content parts list.

    Args:
        text: The text content (topic, prompt, etc.)
        attachment_paths: Optional list of file paths to attach.

    Returns:
        List of content parts (strings and Parts).
    """
    parts: list = []

    if text:
        parts.append(text)

    for path in attachment_paths or []:
        parts.append(load_attachment(path))

    return parts
