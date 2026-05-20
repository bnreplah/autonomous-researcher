"""On-demand research entry point — triggered by GitHub Issues.

Workflow:

1. A user files an issue with the `research-request` label. The issue
   title (or body, if `topic:` line present) becomes the topic.
2. GitHub Actions runs this script with the issue topic.
3. The script gathers candidate material from feeds, narrows to items
   semantically related to the topic (lightweight keyword + LLM rerank),
   asks the LLM for a deep-dive writeup, and posts it to Discord.
4. The script writes a short status comment back on the issue and closes
   it (workflow handles the GitHub API calls).

Run directly:
    python -m cyber_bot.on_demand "supply chain attacks on npm"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from typing import Iterable

from dotenv import load_dotenv

from .discord_client import post_deep_dive
from .researcher import _call_llm, deep_dive
from .sources import Item, fetch_all


RERANK_SYSTEM = (
    "You are a librarian for a cybersecurity research desk. Given a topic "
    "and a list of recent intel items, pick the items most directly "
    "relevant to the topic. Prefer primary sources and technical depth. "
    "Output strictly valid JSON: {\"indices\": [<int>, ...]} with no prose."
)


def _keyword_prefilter(topic: str, items: list[Item],
                       limit: int = 40) -> list[Item]:
    """Cheap lexical filter so we don't ship 200 items to the LLM."""
    terms = [t.lower() for t in re.findall(r"[A-Za-z0-9\-]+", topic) if len(t) > 2]
    if not terms:
        return items[:limit]

    scored: list[tuple[int, Item]] = []
    for it in items:
        haystack = f"{it.title} {it.summary} {it.source_name}".lower()
        hits = sum(haystack.count(t) for t in terms)
        if hits > 0:
            scored.append((hits, it))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    if scored:
        return [it for _, it in scored[:limit]]
    # Fallback: nothing matched, hand newest items to the LLM rerank anyway.
    items_sorted = sorted(items, key=lambda it: it.published or "", reverse=True)
    return items_sorted[:limit]


def _llm_rerank(topic: str, items: list[Item], keep: int = 15) -> list[Item]:
    if not items:
        return []
    listing = "\n".join(
        f"[{i}] ({it.source_name}) {it.title}\n  {it.summary[:300]}"
        for i, it in enumerate(items)
    )
    user = (
        f"Topic: {topic}\n\nItems (pick at most {keep} indices, most relevant first):\n"
        + listing
    )
    raw = _call_llm(RERANK_SYSTEM, user, max_tokens=1000)
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        indices = data.get("indices", [])
    except (json.JSONDecodeError, AttributeError):
        return items[:keep]

    out: list[Item] = []
    seen: set[int] = set()
    for idx in indices:
        try:
            i = int(idx)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(items) and i not in seen:
            seen.add(i)
            out.append(items[i])
        if len(out) >= keep:
            break
    return out or items[:keep]


def parse_topic_from_issue(title: str, body: str) -> str:
    """Extract a research topic from a GitHub issue.

    Priority: a line in the body matching `topic: <something>`, else the
    issue title with a leading `[research]`/`research:` prefix stripped.
    """
    body = body or ""
    match = re.search(r"^\s*topic\s*:\s*(.+)$", body, flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    cleaned = re.sub(r"^\s*\[?research[\]:]?\s*", "", title, flags=re.IGNORECASE)
    return cleaned.strip() or title.strip()


def run(topic: str, max_sources: int = 12,
        dry_run: bool = False) -> tuple[str, list[Item]]:
    print(f"[cyber_bot] Deep-dive topic: {topic!r}")
    all_items = fetch_all()
    print(f"[cyber_bot] Fetched {len(all_items)} total items")
    candidates = _keyword_prefilter(topic, all_items, limit=40)
    print(f"[cyber_bot] {len(candidates)} candidate(s) after lexical filter")
    chosen = _llm_rerank(topic, candidates, keep=max_sources)
    print(f"[cyber_bot] {len(chosen)} item(s) chosen by LLM rerank")

    report, sources = deep_dive(topic, chosen)
    if dry_run:
        print("---- REPORT ----")
        print(report)
        print("---- SOURCES ----")
        for i, it in enumerate(sources, 1):
            print(f"[{i}] {it.source_name} — {it.title} — {it.url}")
        return report, sources

    post_deep_dive(topic, report, sources)
    return report, sources


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Cyber Research Bot — on-demand")
    parser.add_argument("topic", nargs="?", default=None,
                        help="Research topic. Falls back to env vars when omitted.")
    parser.add_argument("--issue-title", default=os.environ.get("ISSUE_TITLE", ""))
    parser.add_argument("--issue-body", default=os.environ.get("ISSUE_BODY", ""))
    parser.add_argument("--max-sources", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-summary",
                        default=os.environ.get("GITHUB_STEP_SUMMARY"),
                        help="If set, append the report to this file (used for "
                             "the GitHub Actions step summary / issue reply).")
    args = parser.parse_args()

    topic = (args.topic
             or parse_topic_from_issue(args.issue_title, args.issue_body))
    if not topic:
        print("[cyber_bot] No topic supplied.", file=sys.stderr)
        return 2

    try:
        report, sources = run(topic, max_sources=args.max_sources,
                              dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"[cyber_bot] FATAL: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    if args.output_summary:
        try:
            with open(args.output_summary, "a", encoding="utf-8") as fh:
                fh.write(f"## Cyber Research: {topic}\n\n{report}\n\n")
                if sources:
                    fh.write("### Sources\n")
                    for i, it in enumerate(sources, 1):
                        fh.write(f"{i}. [{it.source_name}] [{it.title}]({it.url})\n")
        except OSError as exc:
            print(f"[cyber_bot] could not write summary: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
