"""Minimal Claude / Gemini wrappers used by the resource finder.

Keeps this module self-contained so it can run on any GitHub Actions
runner with just an Anthropic or Google API key. Mirrors the call
shape used by cyber_bot.researcher so the prompts feel familiar.
"""

from __future__ import annotations

import os
import re

DEFAULT_BACKEND = os.environ.get("RESOURCE_FINDER_MODEL",
                                 os.environ.get("CYBER_BOT_MODEL", "claude"))


def extract_json(text: str) -> str:
    """Strip Markdown code fences around a JSON payload."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_claude(system: str, user: str, max_tokens: int = 4000) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get(
        "RESOURCE_FINDER_CLAUDE_MODEL",
        os.environ.get("CYBER_BOT_CLAUDE_MODEL",
                       "claude-haiku-4-5-20251001"),
    )
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _call_gemini(system: str, user: str, max_tokens: int = 4000) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = os.environ.get(
        "RESOURCE_FINDER_GEMINI_MODEL",
        os.environ.get("CYBER_BOT_GEMINI_MODEL", "gemini-2.5-flash"),
    )
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
    )
    resp = client.models.generate_content(
        model=model, contents=user, config=cfg,
    )
    return resp.text or ""


def call_llm(system: str, user: str, max_tokens: int = 4000) -> str:
    backend = (DEFAULT_BACKEND or "claude").lower()
    if backend == "gemini":
        return _call_gemini(system, user, max_tokens)
    return _call_claude(system, user, max_tokens)
