"""Posted-item dedup state, persisted as a single JSON file.

Storing in-repo keeps the bot stateless across GitHub Actions runs without
needing external storage. The workflow commits the updated file back at
the end of each successful run.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable


STATE_DIR = Path(__file__).parent / "state"
STATE_FILE = STATE_DIR / "posted.json"
# Cap the number of ids retained so the file doesn't grow forever.
MAX_TRACKED_IDS = 5000


def _load_raw() -> dict:
    if not STATE_FILE.exists():
        return {"posted": {}, "updated_at": 0}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"posted": {}, "updated_at": 0}


def already_posted(item_id: str) -> bool:
    data = _load_raw()
    return item_id in data.get("posted", {})


def filter_new(item_ids: Iterable[str]) -> set[str]:
    data = _load_raw()
    posted = data.get("posted", {})
    return {i for i in item_ids if i not in posted}


def mark_posted(item_ids: Iterable[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = _load_raw()
    posted: dict[str, int] = data.get("posted", {})
    now = int(time.time())
    for item_id in item_ids:
        posted[item_id] = now

    if len(posted) > MAX_TRACKED_IDS:
        # Keep most-recent N entries by timestamp.
        kept = sorted(posted.items(), key=lambda kv: kv[1], reverse=True)
        posted = dict(kept[:MAX_TRACKED_IDS])

    data["posted"] = posted
    data["updated_at"] = now
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    os.replace(tmp, STATE_FILE)
