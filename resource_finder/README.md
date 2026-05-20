# Resource Finder

Companion module to [`bnreplah/cybersecuritylibrary`](https://github.com/bnreplah/cybersecuritylibrary).

It reads the live `RESOURCES_DB.js` (exported to JSON), asks Claude or
Gemini to propose **durable, evergreen** additions for a target
category, verifies each proposed URL is reachable, and writes a JSON
file the library's GitHub Actions workflow merges into
`RESOURCES_DB.js` and opens a PR for human review.

No Modal sandbox needed — this runs on a vanilla GitHub Actions runner
with just an Anthropic or Google API key.

## Pipeline

```
  RESOURCES_DB.js  ──extract_db.js──▶  existing.json
                                          │
                                          ▼
     (optional) recent RSS feed items ──▶ LLM (Claude / Gemini)
                                          │   propose entries
                                          ▼
                          schema validation + dedup
                                          │
                                          ▼
                                   URL verification
                                          │
                                          ▼
                                    proposed.json
                                          │
                  ──merge_curated.js──▶ updated RESOURCES_DB.js
                                          │
                                          ▼
                                  PR opened on library repo
```

## CLI

```bash
python -m resource_finder.discover \
  --existing-db existing.json \
  --category tools \
  --max 5 \
  --topic "AI security" \
  --out proposed.json
```

Flags:

| flag             | description                                                |
| ---------------- | ---------------------------------------------------------- |
| `--existing-db`  | Path to JSON export of `RESOURCES_DB.js` (required).       |
| `--category`     | Target category (`tools`, `research`, `events`, `training`, `threatIntel`, `rssNews`, `rssVendor`, `rssIndy`, `liveFeeds`). |
| `--max`          | Max proposed entries (default 5).                          |
| `--topic`        | Optional topic focus, e.g. `"cloud security"`.             |
| `--no-feeds`     | Skip RSS feed grounding (faster, less fresh).              |
| `--no-verify`    | Skip URL reachability check (faster, less safe).           |
| `--out`          | Path to write proposed-entries JSON (required).            |

## Environment

At least one LLM key:
- `ANTHROPIC_API_KEY` — for Claude (default backend)
- `GOOGLE_API_KEY` — for Gemini

Optional:
- `RESOURCE_FINDER_MODEL` — `claude` or `gemini` (default `claude`)
- `RESOURCE_FINDER_CLAUDE_MODEL` — overrides Claude model id
- `RESOURCE_FINDER_GEMINI_MODEL` — overrides Gemini model id

## Output schema

```jsonc
{
  "category": "tools",
  "topic": "AI security",
  "generated_at": "2026-05-20T12:00:00+00:00",
  "model_backend": "claude",
  "proposals": [
    {
      "category": "tools",
      "entry": {
        "title": "...",
        "url": "https://...",
        "badge": "AI Sec",
        "badgeClass": "badge-magenta",
        "cat": "defensive",
        "desc": "...",
        "tags": ["ai", "defensive", "..."]
      },
      "verification": {
        "missing_fields": [],
        "url_checked": "https://...",
        "status": 200,
        "reachable": true,
        "final_url": null,
        "page_title": "...",
        "error": null
      }
    }
  ]
}
```

Only proposals with `verification.reachable == true` and no
`missing_fields` are merged by the library workflow.
