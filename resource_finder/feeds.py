"""Optional: pull recent items from public security feeds for grounding.

The curator's primary judgement comes from the LLM, but giving it a
sample of recent activity helps surface newly-released tools / shifts
in the landscape it might not yet have in training data.

This is a lightweight subset of cyber_bot.sources, intentionally
self-contained so resource_finder works without that module installed.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

USER_AGENT = (
    "cybersecuritylibrary-curator/1.0 "
    "(+https://github.com/bnreplah/autonomous-researcher)"
)

# A short list of high-signal feeds. Keep small — the LLM only needs hints,
# not a full digest.
DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/"),
    ("Cisco Talos", "https://blog.talosintelligence.com/rss/"),
    ("Unit 42", "https://unit42.paloaltonetworks.com/feed/"),
    ("Project Zero",
     "https://googleprojectzero.blogspot.com/feeds/posts/default"),
]

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class FeedItem:
    source: str
    title: str
    url: str
    summary: str
    published: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


def _strip(text: str, max_len: int = 600) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len].rstrip()


def fetch_feed(name: str, url: str, max_items: int = 8) -> list[FeedItem]:
    try:
        import feedparser  # type: ignore
    except ImportError:
        return []

    parsed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
    out: list[FeedItem] = []
    for entry in parsed.entries[:max_items]:
        link = getattr(entry, "link", "") or ""
        if not link:
            continue
        title = _strip(getattr(entry, "title", "") or "(untitled)", 240)
        summary = _strip(
            getattr(entry, "summary", "")
            or getattr(entry, "description", "") or "",
            600,
        )
        published = None
        for key in ("published_parsed", "updated_parsed"):
            val = getattr(entry, key, None)
            if val:
                try:
                    published = datetime(*val[:6],
                                         tzinfo=timezone.utc).isoformat()
                    break
                except (TypeError, ValueError):
                    continue
        out.append(FeedItem(source=name, title=title, url=link,
                            summary=summary, published=published))
    return out


def fetch_recent(
    feeds: list[tuple[str, str]] = DEFAULT_FEEDS,
    max_per_feed: int = 6,
    throttle: float = 0.3,
) -> list[FeedItem]:
    out: list[FeedItem] = []
    for name, url in feeds:
        try:
            out.extend(fetch_feed(name, url, max_items=max_per_feed))
        except Exception as exc:  # noqa: BLE001 — one bad feed shouldn't kill the run
            print(f"[resource_finder.feeds] {name} failed: {exc}")
        time.sleep(throttle)
    return out
