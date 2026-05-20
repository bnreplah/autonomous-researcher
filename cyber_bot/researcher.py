"""LLM-driven relevance scoring + summarization.

Two operations:

- `score_and_brief(items)` — for the scheduled digest. The model is given
  a batch of candidate headlines and returns a JSON ranking with one-line
  briefings, so the bot only posts the highest-signal items.
- `deep_dive(topic, items)` — for on-demand research requests filed as
  GitHub issues. The model synthesises a longer analyst-style writeup
  from gathered material on a specific topic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from .sources import Item


DEFAULT_MODEL = os.environ.get("CYBER_BOT_MODEL", "claude")
# Accepted values: "claude", "gemini"


@dataclass
class Brief:
    item: Item
    score: int               # 0–10 relevance/importance
    headline: str            # rewritten, neutral headline
    summary: str             # 1–3 sentence analyst brief
    why_it_matters: str      # 1 sentence "so what"


SCORING_SYSTEM = (
    "You are a senior cyber threat-intel analyst triaging incoming items "
    "for a defender-focused Discord channel. Your audience: blue-teamers, "
    "security engineers, and researchers. Score items for operational "
    "importance to defenders right now. Boost: actively exploited CVEs, "
    "widely deployed software, novel attacker techniques, supply-chain "
    "compromise, credible academic results. Penalize: vendor marketing, "
    "rehashes, low-confidence rumors, region-specific consumer scams. "
    "Output strictly valid JSON — no markdown, no prose outside JSON."
)


def _items_for_prompt(items: list[Item]) -> str:
    lines = []
    for i, it in enumerate(items):
        summary = it.summary[:500].replace("\n", " ")
        lines.append(
            f"[{i}] source={it.source_name} tags={','.join(it.tags) or '-'} "
            f"title={it.title!r} summary={summary!r}"
        )
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Strip code fences / preamble around a JSON payload."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_claude(system: str, user: str, max_tokens: int = 4000) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("CYBER_BOT_CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _call_gemini(system: str, user: str, max_tokens: int = 4000) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = os.environ.get("CYBER_BOT_GEMINI_MODEL", "gemini-2.5-flash")
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
    )
    resp = client.models.generate_content(
        model=model, contents=user, config=cfg,
    )
    return resp.text or ""


def _call_llm(system: str, user: str, max_tokens: int = 4000) -> str:
    backend = DEFAULT_MODEL.lower()
    if backend == "gemini":
        return _call_gemini(system, user, max_tokens)
    return _call_claude(system, user, max_tokens)


def score_and_brief(items: list[Item], top_k: int = 8,
                    min_score: int = 6) -> list[Brief]:
    """Score a batch of candidate items and return the strongest briefs."""
    if not items:
        return []

    user_prompt = (
        f"Score and brief the following {len(items)} security intel items. "
        "Return JSON with this exact shape:\n"
        '{ "items": [ {"index": <int>, "score": <0-10 int>, '
        '"headline": "<rewritten neutral headline, <=120 chars>", '
        '"summary": "<1-3 sentences, factual, no hype>", '
        '"why_it_matters": "<1 sentence operational impact>"} ] }\n'
        f"Include all {len(items)} indices. Items:\n\n"
        + _items_for_prompt(items)
    )

    raw = _call_llm(SCORING_SYSTEM, user_prompt, max_tokens=6000)
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        print(f"[cyber_bot] LLM returned non-JSON, falling back. Raw: {raw[:300]}")
        return []

    briefs: list[Brief] = []
    for row in data.get("items", []):
        try:
            idx = int(row["index"])
            score = int(row["score"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 0 <= idx < len(items):
            continue
        if score < min_score:
            continue
        briefs.append(Brief(
            item=items[idx],
            score=score,
            headline=str(row.get("headline") or items[idx].title)[:200],
            summary=str(row.get("summary") or "")[:600],
            why_it_matters=str(row.get("why_it_matters") or "")[:300],
        ))

    briefs.sort(key=lambda b: b.score, reverse=True)
    return briefs[:top_k]


DEEP_DIVE_SYSTEM = (
    "You are a senior threat-intel analyst writing a tight situational "
    "report for a defender-focused Discord channel. Tone: neutral, "
    "evidence-based, no marketing. Cite sources inline by their numeric "
    "index in brackets like [3]. Structure your reply as Markdown with "
    "these sections: ### TL;DR (2-3 bullets), ### What we know, "
    "### Why it matters, ### Recommended actions, ### Open questions. "
    "Stay under 1800 characters total so it fits in a Discord message. "
    "Do not invent CVE numbers, victim names, or facts not in sources."
)


def deep_dive(topic: str, items: list[Item]) -> tuple[str, list[Item]]:
    """Produce a longer analyst writeup for a specific topic.

    Returns (markdown_report, sources_used_in_order_of_citation).
    """
    if not items:
        return (
            f"_No relevant material found in current feeds for_ **{topic}**. "
            "Try a broader query or re-run later.",
            [],
        )

    numbered = []
    for i, it in enumerate(items, start=1):
        snippet = it.summary[:600].replace("\n", " ")
        numbered.append(
            f"[{i}] ({it.source_name}) {it.title}\nURL: {it.url}\n{snippet}"
        )
    user_prompt = (
        f"Research topic: {topic}\n\n"
        f"Sources ({len(items)} items):\n\n" + "\n\n".join(numbered)
    )
    report = _call_llm(DEEP_DIVE_SYSTEM, user_prompt, max_tokens=3000).strip()
    return report, items
