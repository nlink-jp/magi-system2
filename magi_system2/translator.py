"""Output translation — Gemini Flash translation with caching."""

from __future__ import annotations

from magi_system2.console import log
from magi_system2.llm import generate_text


def translate_text(text: str, target_lang: str, context: str = "") -> tuple[str, int, int]:
    """Translate text to target language using Gemini Flash.

    Args:
        text: Text to translate.
        target_lang: Target language code (e.g. "ja", "ko").
        context: Optional context to help translation (e.g. "discussion about AI ethics").

    Returns:
        (translated_text, input_tokens, output_tokens)
    """
    system_prompt = (
        f"Translate the following text into {target_lang}. "
        f"Preserve technical terms, names, and formatting. "
        f"Be natural and accurate."
    )
    if context:
        system_prompt += f"\nContext: {context}"

    log("TRANS", f"Translating to {target_lang} ({len(text)} chars)...")
    result, in_tok, out_tok = generate_text(
        system_prompt=system_prompt,
        user_content=[text],
        role="flash",
        temperature=0.2,
        label=f"translate-{target_lang}",
    )
    return result, in_tok, out_tok
