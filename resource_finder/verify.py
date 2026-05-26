"""Lightweight URL verification for proposed library entries.

Goal: catch the obvious — typos, dead domains, parking pages — without
paying for a real crawler. Treats rate-limited / auth-required responses
as reachable, since many real resources serve those to bots.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional

import requests

USER_AGENT = (
    "cybersecuritylibrary-curator/1.0 "
    "(+https://github.com/bnreplah/autonomous-researcher)"
)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Status codes we treat as "reachable but blocking bots" — still real.
_SOFT_OK = {401, 403, 405, 429}


@dataclass
class UrlCheck:
    url: str
    status: int
    reachable: bool
    final_url: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def check_url(url: str, timeout: float = 15.0,
              fetch_body: bool = True) -> UrlCheck:
    """GET a URL, follow redirects, classify reachability."""
    if not url or not re.match(r"https?://", url):
        return UrlCheck(url=url, status=0, reachable=False,
                        error="invalid url")

    try:
        resp = requests.get(
            url, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            stream=not fetch_body,
        )
    except requests.RequestException as exc:
        return UrlCheck(url=url, status=0, reachable=False, error=str(exc))

    code = resp.status_code
    reachable = (200 <= code < 400) or code in _SOFT_OK

    title = None
    if fetch_body and 200 <= code < 400 and \
       "html" in resp.headers.get("Content-Type", "").lower():
        try:
            body = resp.text[:50_000]
            m = _TITLE_RE.search(body)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
        except Exception:
            pass

    final = str(resp.url) if str(resp.url) != url else None
    return UrlCheck(url=url, status=code, reachable=reachable,
                    final_url=final, title=title)
