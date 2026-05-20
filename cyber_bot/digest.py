"""Scheduled digest entry point.

Pulls all feeds, drops already-posted items via dedup state, asks the
LLM to score+brief the remainder, posts the top-K to Discord, and marks
those items as posted.

Run directly:
    python -m cyber_bot.digest
or via GitHub Actions on cron.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv

from . import state
from .discord_client import post_digest
from .researcher import score_and_brief
from .sources import Item, fetch_all


def collect_new_items(max_candidates: int = 80) -> list[Item]:
    items = fetch_all()
    new_items = [it for it in items if not state.already_posted(it.item_id)]
    # Newest first when timestamps are present, then trim.
    new_items.sort(key=lambda it: it.published or "", reverse=True)
    if len(new_items) > max_candidates:
        new_items = new_items[:max_candidates]
    return new_items


def run(top_k: int = 8, min_score: int = 6,
        max_candidates: int = 80, dry_run: bool = False) -> int:
    new_items = collect_new_items(max_candidates=max_candidates)
    print(f"[cyber_bot] {len(new_items)} new candidate(s) after dedup")

    if not new_items:
        if not dry_run:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            header = f"**🛡️ Cyber Research Digest — {now}**"
            post_digest([], header=header)
        return 0

    briefs = score_and_brief(new_items, top_k=top_k, min_score=min_score)
    print(f"[cyber_bot] {len(briefs)} brief(s) passed scoring threshold {min_score}")

    if dry_run:
        for b in briefs:
            print(f"  [{b.score}] {b.headline} — {b.item.url}")
        return len(briefs)

    posted = post_digest(briefs)
    state.mark_posted(b.item.item_id for b in briefs)
    return posted


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Cyber Research Bot — digest")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--min-score", type=int, default=6)
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--dry-run", action="store_true",
                        help="Score and print but do not post to Discord")
    args = parser.parse_args()

    try:
        run(top_k=args.top_k, min_score=args.min_score,
            max_candidates=args.max_candidates, dry_run=args.dry_run)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[cyber_bot] FATAL: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
