"""Source configuration for the Cyber Research Bot.

Each entry has a stable id (used for dedup state), a human-readable name,
a kind (rss | nvd | arxiv), and source-specific fields. Add or remove
entries here without touching the rest of the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str  # "rss" | "nvd" | "arxiv"
    url: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)


SOURCES: list[Source] = [
    # News & analysis
    Source("krebs", "Krebs on Security", "rss",
           "https://krebsonsecurity.com/feed/", ("news", "analysis")),
    Source("hackernews", "The Hacker News", "rss",
           "https://feeds.feedburner.com/TheHackersNews", ("news",)),
    Source("bleeping", "BleepingComputer", "rss",
           "https://www.bleepingcomputer.com/feed/", ("news",)),
    Source("darkreading", "Dark Reading", "rss",
           "https://www.darkreading.com/rss.xml", ("news",)),
    Source("schneier", "Schneier on Security", "rss",
           "https://www.schneier.com/feed/atom/", ("analysis",)),
    Source("sans_isc", "SANS Internet Storm Center", "rss",
           "https://isc.sans.edu/rssfeed.xml", ("analysis", "advisory")),
    Source("googletag", "Google Threat Analysis Group", "rss",
           "https://blog.google/threat-analysis-group/rss/", ("research",)),
    Source("project_zero", "Project Zero", "rss",
           "https://googleprojectzero.blogspot.com/feeds/posts/default",
           ("research", "vulns")),

    # Government / coordinated advisories
    Source("cisa_advisories", "CISA Cybersecurity Advisories", "rss",
           "https://www.cisa.gov/cybersecurity-advisories/all.xml",
           ("advisory", "gov")),
    Source("cisa_kev", "CISA Known Exploited Vulnerabilities", "rss",
           "https://www.cisa.gov/known-exploited-vulnerabilities.xml",
           ("advisory", "gov", "exploited")),

    # Vendor research
    Source("talos", "Cisco Talos", "rss",
           "https://blog.talosintelligence.com/rss/", ("research", "vendor")),
    Source("unit42", "Palo Alto Unit 42", "rss",
           "https://unit42.paloaltonetworks.com/feed/", ("research", "vendor")),
    Source("mandiant", "Mandiant", "rss",
           "https://www.mandiant.com/resources/blog/rss.xml",
           ("research", "vendor")),
    Source("microsoft_msrc", "Microsoft Security Blog", "rss",
           "https://www.microsoft.com/en-us/security/blog/feed/",
           ("research", "vendor")),

    # CVE feed (NIST NVD JSON API — recent published)
    Source("nvd_recent", "NVD Recent CVEs (CVSS >= 7)", "nvd", None,
           ("cve", "vulns")),

    # Academic preprints
    Source("arxiv_crypto", "arXiv cs.CR (Crypto & Security)", "arxiv",
           "http://export.arxiv.org/api/query?search_query=cat:cs.CR"
           "&sortBy=submittedDate&sortOrder=descending&max_results=25",
           ("research", "academic")),
]


# Discord embed colour by tag bucket (decimal RGB)
TAG_COLORS = {
    "exploited": 0xE74C3C,   # red — actively exploited
    "advisory": 0xE67E22,    # orange
    "cve": 0xF1C40F,         # yellow
    "vulns": 0xF1C40F,
    "research": 0x3498DB,    # blue
    "academic": 0x9B59B6,    # purple
    "news": 0x2ECC71,        # green
    "analysis": 0x1ABC9C,    # teal
    "default": 0x95A5A6,     # grey
}


def color_for_tags(tags: tuple[str, ...]) -> int:
    for tag in ("exploited", "advisory", "cve", "vulns",
                "research", "academic", "analysis", "news"):
        if tag in tags:
            return TAG_COLORS[tag]
    return TAG_COLORS["default"]
