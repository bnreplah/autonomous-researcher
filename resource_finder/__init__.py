"""Resource Finder — discover, parse, verify cybersecurity library entries.

Companion module for bnreplah/cybersecuritylibrary. Given the live
RESOURCES_DB.js (exported to JSON), it asks an LLM to propose new
durable resources for a target category, verifies their URLs, and
emits a JSON file the cybersecuritylibrary workflow merges and opens
a PR for. Standalone — no Modal sandbox required, suitable for
GitHub Actions runners.

Entrypoint:
    python -m resource_finder.discover --help
"""

__all__ = ["discover", "schema", "llm", "verify", "feeds"]
