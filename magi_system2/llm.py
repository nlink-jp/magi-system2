"""Vertex AI Gemini client wrapper with multimodal support."""

from __future__ import annotations

import json
import os
import secrets
import sys
from typing import Any, Callable

from google import genai
from google.genai import types
from pydantic import BaseModel

from magi_system2.console import log

_PRO_MODEL = "gemini-2.5-pro"
_FLASH_MODEL = "gemini-2.5-flash"
_MAX_RETRIES = 3


def _make_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )


def _model_name(role: str) -> str:
    """Return the model name for a given role."""
    if role == "pro":
        return os.environ.get("MAGI2_PRO_MODEL", _PRO_MODEL)
    return os.environ.get("MAGI2_FLASH_MODEL", _FLASH_MODEL)


def generate_structured(
    system_prompt: str,
    user_content: list[Any],
    response_schema: type[BaseModel],
    role: str = "pro",
    temperature: float = 0.5,
    label: str = "",
) -> tuple[BaseModel, int, int]:
    """Generate a structured response from Gemini.

    Args:
        system_prompt: System instruction.
        user_content: List of content parts (text strings, media Parts, etc.)
        response_schema: Pydantic model for structured output.
        role: "pro" or "flash" — selects the model.
        temperature: Sampling temperature.
        label: Label for console logging.

    Returns:
        (parsed_response, input_tokens, output_tokens)
    """
    client = _make_client()
    model = _model_name(role)

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=4096,
                    ),
                ),
            )

            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            data = json.loads(response.text)
            result = response_schema(**data)

            log("API", f"{label} ({role}, {input_tokens + output_tokens} tokens)")
            return result, input_tokens, output_tokens

        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                log("ERR", f"{label} attempt {attempt + 1} failed: {e}", level="warn")
                continue
            log("ERR", f"{label} failed after {_MAX_RETRIES} attempts: {e}", level="error")
            raise


def generate_text(
    system_prompt: str,
    user_content: list[Any],
    role: str = "flash",
    temperature: float = 0.3,
    label: str = "",
) -> tuple[str, int, int]:
    """Generate a plain text response from Gemini.

    Returns:
        (text, input_tokens, output_tokens)
    """
    client = _make_client()
    model = _model_name(role)

    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            thinking_config=types.ThinkingConfig(
                thinking_budget=4096,
            ),
        ),
    )

    input_tokens = 0
    output_tokens = 0
    if response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    log("API", f"{label} ({role}, {input_tokens + output_tokens} tokens)")
    return response.text, input_tokens, output_tokens


# Callback type for streaming chunks
# (chunk_type: "thought" | "text", text: str) -> None
StreamCallback = Callable[[str, str], None]


def generate_structured_stream(
    system_prompt: str,
    user_content: list[Any],
    response_schema: type[BaseModel],
    on_chunk: StreamCallback | None = None,
    role: str = "pro",
    temperature: float = 0.5,
    label: str = "",
) -> tuple[BaseModel, int, int]:
    """Generate a structured response with streaming + CoT display.

    Streams thinking and text chunks via on_chunk callback for real-time display.
    Parses the complete JSON response after stream finishes.

    Args:
        on_chunk: Callback receiving ("thought", text) or ("text", text) for each chunk.

    Returns:
        (parsed_response, input_tokens, output_tokens)
    """
    client = _make_client()
    model = _model_name(role)

    for attempt in range(_MAX_RETRIES):
        try:
            stream = client.models.generate_content_stream(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=4096,
                    ),
                ),
            )

            full_text = ""
            input_tokens = 0
            output_tokens = 0

            for chunk in stream:
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    continue

                for part in candidate.content.parts:
                    if not part.text:
                        continue
                    is_thought = getattr(part, "thought", False)
                    if is_thought:
                        if on_chunk:
                            on_chunk("thought", part.text)
                    else:
                        full_text += part.text
                        if on_chunk:
                            on_chunk("text", part.text)

                # Capture token usage from the last chunk
                if chunk.usage_metadata:
                    if chunk.usage_metadata.prompt_token_count:
                        input_tokens = chunk.usage_metadata.prompt_token_count
                    if chunk.usage_metadata.candidates_token_count:
                        output_tokens = chunk.usage_metadata.candidates_token_count

            data = json.loads(full_text)
            result = response_schema(**data)

            log("API", f"{label} ({role}, {input_tokens + output_tokens} tokens, streamed)")
            return result, input_tokens, output_tokens

        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                log("ERR", f"{label} attempt {attempt + 1} failed: {e}", level="warn")
                continue
            log("ERR", f"{label} failed after {_MAX_RETRIES} attempts: {e}", level="error")
            raise


def make_nonce_tag(content: str) -> tuple[str, str]:
    """Wrap content in nonce-tagged XML for prompt injection defense.

    Returns:
        (wrapped_content, nonce) — the nonce is embedded in the tag name.
    """
    nonce = secrets.token_hex(8)
    tag = f"user_data_{nonce}"
    return f"<{tag}>\n{content}\n</{tag}>", nonce
