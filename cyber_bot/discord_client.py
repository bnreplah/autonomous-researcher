"""Minimal Discord webhook poster.

Uses the plain HTTP webhook API — no bot token, no gateway. Splits long
content into multiple messages and respects the 10-embed-per-message and
~2000-character limits.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from .config import color_for_tags
from .researcher import Brief
from .sources import Item


DISCORD_MAX_CONTENT = 1900       # leave headroom under the 2000 char limit
DISCORD_MAX_EMBEDS = 10


def _webhook_url() -> str:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is not set. Configure it as a GitHub "
            "Actions secret or in your local .env file."
        )
    return url


def _post(payload: dict, max_retries: int = 4) -> None:
    url = _webhook_url()
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=20)
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise
            print(f"[cyber_bot] Discord post error ({exc}); retry in {delay}s")
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "2"))
            print(f"[cyber_bot] Discord rate-limited; sleeping {retry_after}s")
            time.sleep(retry_after)
            continue
        if 200 <= resp.status_code < 300:
            return
        if resp.status_code >= 500 and attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(
            f"Discord webhook failed: {resp.status_code} {resp.text[:300]}"
        )


def _embed_for_brief(brief: Brief) -> dict:
    item = brief.item
    description_parts = [brief.summary]
    if brief.why_it_matters:
        description_parts.append(f"**Why it matters:** {brief.why_it_matters}")
    description = "\n\n".join(p for p in description_parts if p)

    fields = []
    if item.extra.get("cvss") is not None:
        fields.append({
            "name": "CVSS",
            "value": f"{item.extra['cvss']} ({item.extra.get('severity') or 'N/A'})",
            "inline": True,
        })
    fields.append({
        "name": "Source",
        "value": item.source_name,
        "inline": True,
    })
    fields.append({
        "name": "Score",
        "value": f"{brief.score}/10",
        "inline": True,
    })

    embed = {
        "title": brief.headline[:250],
        "url": item.url,
        "description": description[:2000],
        "color": color_for_tags(item.tags),
        "fields": fields,
        "footer": {"text": " · ".join(item.tags) or "intel"},
    }
    if item.published:
        embed["timestamp"] = item.published
    return embed


def post_digest(briefs: list[Brief], header: Optional[str] = None) -> int:
    """Post a digest of briefs. Returns the number of items posted."""
    if not briefs:
        if header:
            _post({"content": header + "\n_No new high-signal items in this window._"})
        return 0

    if header is None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        header = f"**🛡️ Cyber Research Digest — {now}**"

    # First message: header + first batch of embeds.
    first = True
    for chunk_start in range(0, len(briefs), DISCORD_MAX_EMBEDS):
        chunk = briefs[chunk_start:chunk_start + DISCORD_MAX_EMBEDS]
        payload: dict = {
            "username": "Cyber Research Bot",
            "embeds": [_embed_for_brief(b) for b in chunk],
        }
        if first:
            payload["content"] = header
            first = False
        _post(payload)
    return len(briefs)


def _chunk_text(text: str, max_len: int = DISCORD_MAX_CONTENT) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    return chunks


def post_deep_dive(topic: str, report: str, sources: list[Item]) -> None:
    """Post an on-demand research writeup with cited sources."""
    header = f"**🔬 Deep Dive: {topic}**"
    body = report.strip() or "_The model returned no content._"
    chunks = _chunk_text(body, DISCORD_MAX_CONTENT - len(header) - 4)

    first_payload = {
        "username": "Cyber Research Bot",
        "content": f"{header}\n\n{chunks[0]}",
    }
    _post(first_payload)
    for extra in chunks[1:]:
        _post({"username": "Cyber Research Bot", "content": extra})

    if sources:
        lines = ["**Sources**"]
        for i, item in enumerate(sources, start=1):
            lines.append(f"[{i}] [{item.source_name}] {item.title} — <{item.url}>")
        for chunk in _chunk_text("\n".join(lines)):
            _post({"username": "Cyber Research Bot", "content": chunk})
