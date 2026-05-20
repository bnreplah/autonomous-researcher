"""Fetchers for the various intel sources.

Returns a normalized list of `Item` dicts so downstream code (LLM
scoring, Discord embeds, dedup state) doesn't care about source type.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import feedparser  # type: ignore
import requests

from .config import Source, SOURCES


NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
USER_AGENT = "cyber-research-bot/1.0 (+https://github.com/bnreplah/autonomous-researcher)"


@dataclass
class Item:
    source_id: str
    source_name: str
    item_id: str           # stable id for dedup (URL, CVE id, arXiv id)
    title: str
    url: str
    summary: str
    published: Optional[str]  # ISO 8601 or None
    tags: tuple[str, ...] = field(default_factory=tuple)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str, max_len: int = 800) -> str:
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def _parse_published(entry: Any) -> Optional[str]:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key) if isinstance(entry, dict) else getattr(entry, key, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                continue
    return None


def _fetch_rss(source: Source) -> list[Item]:
    parsed = feedparser.parse(
        source.url,
        request_headers={"User-Agent": USER_AGENT},
    )
    items: list[Item] = []
    for entry in parsed.entries[:25]:
        link = getattr(entry, "link", "") or ""
        guid = getattr(entry, "id", None) or link
        if not guid:
            continue
        title = _strip_html(getattr(entry, "title", "") or "(untitled)", 300)
        summary = _strip_html(
            getattr(entry, "summary", "") or getattr(entry, "description", "") or "",
            1200,
        )
        items.append(Item(
            source_id=source.id,
            source_name=source.name,
            item_id=guid,
            title=title,
            url=link,
            summary=summary,
            published=_parse_published(entry),
            tags=source.tags,
        ))
    return items


def _fetch_nvd(source: Source, min_cvss: float = 7.0,
               lookback_hours: int = 36) -> list[Item]:
    end = datetime.now(timezone.utc)
    start = end.timestamp() - lookback_hours * 3600
    start_dt = datetime.fromtimestamp(start, tz=timezone.utc)
    params = {
        "pubStartDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage": 50,
    }
    try:
        resp = requests.get(
            NVD_API, params=params,
            headers={"User-Agent": USER_AGENT}, timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[cyber_bot] NVD fetch failed: {exc}")
        return []

    items: list[Item] = []
    for entry in payload.get("vulnerabilities", []):
        cve = entry.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue

        descriptions = cve.get("descriptions", [])
        en_desc = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "",
        )

        metrics = cve.get("metrics", {})
        cvss_score: Optional[float] = None
        cvss_severity: Optional[str] = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            blocks = metrics.get(key) or []
            if blocks:
                data = blocks[0].get("cvssData", {})
                cvss_score = data.get("baseScore")
                cvss_severity = data.get("baseSeverity") or blocks[0].get("baseSeverity")
                break

        if cvss_score is None or cvss_score < min_cvss:
            continue

        title = f"{cve_id} — CVSS {cvss_score} ({cvss_severity or 'N/A'})"
        items.append(Item(
            source_id=source.id,
            source_name=source.name,
            item_id=cve_id,
            title=title,
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            summary=_strip_html(en_desc, 1200),
            published=cve.get("published"),
            tags=source.tags,
            extra={"cvss": cvss_score, "severity": cvss_severity},
        ))
    return items


def _fetch_arxiv(source: Source) -> list[Item]:
    try:
        resp = requests.get(
            source.url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[cyber_bot] arXiv fetch failed: {exc}")
        return []

    parsed = feedparser.parse(resp.content)
    items: list[Item] = []
    for entry in parsed.entries[:15]:
        arxiv_id = getattr(entry, "id", "")
        link = getattr(entry, "link", "") or arxiv_id
        title = _strip_html(getattr(entry, "title", "") or "(untitled)", 300)
        summary = _strip_html(getattr(entry, "summary", "") or "", 1200)
        items.append(Item(
            source_id=source.id,
            source_name=source.name,
            item_id=arxiv_id or link,
            title=title,
            url=link,
            summary=summary,
            published=_parse_published(entry),
            tags=source.tags,
        ))
    return items


def fetch_source(source: Source) -> list[Item]:
    if source.kind == "rss":
        return _fetch_rss(source)
    if source.kind == "nvd":
        return _fetch_nvd(source)
    if source.kind == "arxiv":
        return _fetch_arxiv(source)
    raise ValueError(f"Unknown source kind: {source.kind}")


def fetch_all(sources: Iterable[Source] = SOURCES,
              throttle_seconds: float = 0.5) -> list[Item]:
    out: list[Item] = []
    for src in sources:
        try:
            items = fetch_source(src)
            print(f"[cyber_bot] {src.name}: {len(items)} item(s)")
            out.extend(items)
        except Exception as exc:  # noqa: BLE001 — one bad feed shouldn't kill the run
            print(f"[cyber_bot] {src.name} failed: {exc}")
        time.sleep(throttle_seconds)
    return out
