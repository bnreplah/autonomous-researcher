"""Main CLI: propose new entries for a RESOURCES_DB.js category.

Pipeline:
  1. Load existing DB summary (titles + URLs) from JSON.
  2. Optionally pull a handful of recent feed items for grounding.
  3. Ask the LLM to propose at most N new durable entries for a target
     category, matching that category's schema, avoiding duplicates.
  4. Validate the response against the schema.
  5. Verify each proposed URL is reachable.
  6. Write a JSON file the cybersecuritylibrary workflow can consume.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

from .llm import call_llm, extract_json
from .schema import (
    BADGE_CLASSES, CATEGORIES, CATEGORY_DESCRIPTIONS,
    CATEGORY_FIELDS, DEFAULT_BADGE,
)
from .verify import check_url

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv(*_a, **_kw) -> None:  # noqa: D401, ANN001
        return None


@dataclass
class Proposal:
    category: str
    entry: dict[str, Any]
    verification: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "entry": self.entry,
            "verification": self.verification,
        }


CURATOR_SYSTEM = (
    "You curate a public cybersecurity reference library "
    "(github.com/bnreplah/cybersecuritylibrary). Your job is to propose "
    "durable, evergreen additions: production tools, frameworks, "
    "research databases, training platforms, recurring conferences, or "
    "long-lived RSS feeds. Never propose individual news stories, blog "
    "posts, or one-off advisories. Refuse to invent entries — only "
    "propose real, verifiable resources you are confident about. Match "
    "the exact JSON schema requested. Output JSON only, no markdown "
    "fences, no prose outside the JSON."
)


def _format_existing(existing: dict[str, list[dict[str, Any]]]) -> str:
    blocks: list[str] = []
    for cat, entries in existing.items():
        names: list[str] = []
        for e in entries[:60]:
            name = e.get("title") or e.get("name") or ""
            url = e.get("url") or e.get("rss") or e.get("site") or ""
            if name:
                names.append(f"- {name} | {url}")
        if names:
            blocks.append(f"## {cat}\n" + "\n".join(names))
    return "\n\n".join(blocks) or "(empty)"


def _format_feed_items(items: list[Any], max_items: int = 30) -> str:
    if not items:
        return "(none)"
    out = []
    for it in items[:max_items]:
        source = getattr(it, "source", "?")
        title = getattr(it, "title", "")
        url = getattr(it, "url", "")
        summary = (getattr(it, "summary", "") or "")[:200].replace("\n", " ")
        out.append(f"- ({source}) {title} — {url}\n  {summary}")
    return "\n".join(out)


def _existing_hosts(existing: dict[str, list[dict[str, Any]]]) -> set[str]:
    hosts: set[str] = set()
    for entries in existing.values():
        for e in entries:
            for field_name in ("url", "site", "rss"):
                val = e.get(field_name) or ""
                m = re.match(r"https?://([^/]+)", val)
                if m:
                    hosts.add(m.group(1).lower().lstrip("www."))
    return hosts


def _existing_titles(existing: dict[str, list[dict[str, Any]]]) -> set[str]:
    titles: set[str] = set()
    for entries in existing.values():
        for e in entries:
            t = (e.get("title") or e.get("name") or "").strip().lower()
            if t:
                titles.add(t)
    return titles


def _is_duplicate(entry: dict[str, Any],
                  titles: set[str], hosts: set[str]) -> bool:
    title = (entry.get("title") or entry.get("name") or "").strip().lower()
    if title and title in titles:
        return True
    for field_name in ("url", "site", "rss"):
        val = entry.get(field_name) or ""
        m = re.match(r"https?://([^/]+)", val)
        if m:
            host = m.group(1).lower().lstrip("www.")
            if host in hosts:
                return True
    return False


def _apply_defaults(entry: dict[str, Any], category: str) -> dict[str, Any]:
    default = DEFAULT_BADGE.get(category)
    if default:
        entry.setdefault("badge", default[0])
        entry.setdefault("badgeClass", default[1])
    if entry.get("badgeClass") and entry["badgeClass"] not in BADGE_CLASSES:
        entry["badgeClass"] = (default[1] if default else "badge-cyan")
    return entry


def _missing_fields(entry: dict[str, Any], category: str) -> list[str]:
    required = CATEGORY_FIELDS.get(category, [])
    return [f for f in required if not entry.get(f)]


def _build_user_prompt(category: str,
                       existing: dict[str, list[dict[str, Any]]],
                       feed_items: list[Any], max_entries: int,
                       topic: str) -> str:
    fields = CATEGORY_FIELDS.get(category)
    if not fields:
        raise ValueError(f"Unsupported category: {category!r}")

    schema_hint = ", ".join(fields)
    cat_hint = CATEGORY_DESCRIPTIONS.get(category, "")
    badge_palette = ", ".join(BADGE_CLASSES)

    return (
        f"Target category: {category}\n"
        f"What belongs here: {cat_hint}\n"
        f"Required JSON fields per entry: {schema_hint}\n"
        f"Allowed badgeClass values: {badge_palette}\n"
        f"Topic focus (optional): {topic or 'general'}\n"
        f"Propose at most {max_entries} new entries.\n\n"
        "Do not duplicate anything already in the library — check both "
        "by display name AND by URL host. If you can't think of strong "
        "new candidates, return fewer entries rather than padding.\n\n"
        f"=== Existing library entries ===\n{_format_existing(existing)}\n\n"
        "=== Recent items from security feeds (for inspiration only — "
        "do NOT propose individual articles as library entries) ===\n"
        f"{_format_feed_items(feed_items)}\n\n"
        "Return JSON of the form:\n"
        '{ "entries": [ { /* one object per proposed entry, using '
        "exactly the required fields listed above */ } ] }\n"
        "Tags should be a list of 2-5 short lowercase strings. "
        "Descriptions should be 1-2 sentences, neutral and factual."
    )


def discover(category: str, existing: dict[str, list[dict[str, Any]]],
             max_entries: int = 5, topic: str = "",
             include_feeds: bool = True,
             verify_urls: bool = True) -> list[Proposal]:
    feed_items: list[Any] = []
    if include_feeds:
        try:
            from .feeds import fetch_recent
            feed_items = fetch_recent()
            print(f"[resource_finder] pulled {len(feed_items)} feed items "
                  "for grounding", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"[resource_finder] feed fetch failed (non-fatal): {exc}",
                  file=sys.stderr)

    user_prompt = _build_user_prompt(
        category, existing, feed_items, max_entries, topic,
    )

    raw = call_llm(CURATOR_SYSTEM, user_prompt, max_tokens=4000)
    try:
        data = json.loads(extract_json(raw))
    except json.JSONDecodeError:
        print(f"[resource_finder] LLM returned non-JSON: {raw[:300]!r}",
              file=sys.stderr)
        return []

    raw_entries = data.get("entries") or []
    titles = _existing_titles(existing)
    hosts = _existing_hosts(existing)

    proposals: list[Proposal] = []
    for e in raw_entries:
        if not isinstance(e, dict):
            continue
        if _is_duplicate(e, titles, hosts):
            continue
        entry = _apply_defaults(dict(e), category)
        ver: dict[str, Any] = {
            "missing_fields": _missing_fields(entry, category),
        }
        if verify_urls:
            primary = (entry.get("url") or entry.get("rss")
                       or entry.get("site") or "")
            if primary:
                check = check_url(primary)
                ver.update({
                    "url_checked": primary,
                    "status": check.status,
                    "reachable": check.reachable,
                    "final_url": check.final_url,
                    "page_title": check.title,
                    "error": check.error,
                })
            else:
                ver.update({
                    "url_checked": None, "reachable": False,
                    "error": "no url/rss/site field",
                })
        proposals.append(Proposal(category=category, entry=entry,
                                  verification=ver))
        if len(proposals) >= max_entries:
            break
    return proposals


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="python -m resource_finder.discover",
        description=("Propose new resources for "
                     "bnreplah/cybersecuritylibrary RESOURCES_DB.js."),
    )
    parser.add_argument("--existing-db", required=True,
                        help=("Path to a JSON export of the current "
                              "RESOURCES_DB.js (produced by "
                              "scripts/extract_db.js in the library repo)."))
    parser.add_argument("--category", required=True, choices=CATEGORIES,
                        help="Which category to curate.")
    parser.add_argument("--max", type=int, default=5,
                        help="Max proposed entries (default: 5).")
    parser.add_argument("--topic", default="",
                        help="Optional topic focus, e.g. 'AI security'.")
    parser.add_argument("--no-feeds", action="store_true",
                        help="Skip pulling recent feed items for context.")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip URL verification (faster, less safe).")
    parser.add_argument("--out", required=True,
                        help="Path to write the proposed-entries JSON.")
    args = parser.parse_args(argv)

    with open(args.existing_db, "r", encoding="utf-8") as f:
        existing = json.load(f)

    proposals = discover(
        category=args.category, existing=existing,
        max_entries=args.max, topic=args.topic,
        include_feeds=not args.no_feeds,
        verify_urls=not args.no_verify,
    )

    payload = {
        "category": args.category,
        "topic": args.topic or None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_backend": os.environ.get("RESOURCE_FINDER_MODEL",
                                        os.environ.get("CYBER_BOT_MODEL",
                                                       "claude")),
        "proposals": [p.to_dict() for p in proposals],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    n_reachable = sum(
        1 for p in proposals if p.verification.get("reachable")
    )
    print(f"[resource_finder] wrote {len(proposals)} proposal(s) "
          f"({n_reachable} reachable) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
