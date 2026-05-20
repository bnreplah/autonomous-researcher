"""Schema for RESOURCES_DB.js categories.

Keeps the LLM and the merge step on the same page about which fields
are required for each category, and which badge classes are valid.
"""

from __future__ import annotations

# Required fields per category, in canonical display order.
CATEGORY_FIELDS: dict[str, list[str]] = {
    "liveFeeds":   ["id", "name", "url", "site", "color"],
    "rssNews":     ["name", "site", "rss"],
    "rssVendor":   ["name", "site", "rss"],
    "rssIndy":     ["name", "site", "rss"],
    "events":      ["title", "url", "badge", "badgeClass", "cat",
                    "desc", "location", "date", "cost", "tags"],
    "research":    ["title", "url", "badge", "badgeClass", "desc", "tags"],
    "tools":       ["title", "url", "badge", "badgeClass", "cat",
                    "desc", "tags"],
    "training":    ["title", "url", "badge", "badgeClass", "desc", "tags"],
    "threatIntel": ["title", "url", "badge", "badgeClass", "desc", "tags"],
}

# CSS classes used by index.html for entry badges.
BADGE_CLASSES: list[str] = [
    "badge-red", "badge-amber", "badge-green",
    "badge-cyan", "badge-purple", "badge-magenta",
]

# What kind of resource belongs in each category. Used in the LLM prompt.
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "tools":       ("Production security tools and frameworks: offensive, "
                    "defensive, OSINT, forensics, reversing. Must have a "
                    "project home page. NOT a blog post or news article."),
    "research":    ("Authoritative research databases, knowledge bases, "
                    "and standards (e.g. MITRE ATT&CK, NIST NVD, OWASP, "
                    "Exploit-DB, arXiv categories). NOT individual papers."),
    "events":      ("Recurring annual cybersecurity conferences and "
                    "competitions (e.g. DEF CON, Black Hat, RSAC, Pwn2Own, "
                    "BSides). Must include location, date, cost."),
    "training":    ("Reputable training platforms, certification bodies, "
                    "and curricula (e.g. Offensive Security, SANS, "
                    "TryHackMe, HackTheBox, NICCS)."),
    "threatIntel": ("Threat-intelligence platforms, feeds, ISACs, and "
                    "sharing communities."),
    "rssNews":     ("Independent security news outlets with RSS/Atom "
                    "feeds. Skip vendor blogs (those go in rssVendor)."),
    "rssVendor":   ("Vendor research blogs with RSS/Atom feeds "
                    "(e.g. Talos, Unit 42, Sophos News, Microsoft "
                    "Security)."),
    "rssIndy":     ("Independent security researchers and individual "
                    "experts with personal blogs/RSS feeds."),
    "liveFeeds":   ("Highest-signal RSS feeds suitable for a homepage "
                    "live ticker. Each needs a hex color for its chip."),
}

# Sensible badge defaults per category (the LLM may override).
DEFAULT_BADGE: dict[str, tuple[str, str]] = {
    # category -> (badge_text, badge_class)
    "tools":       ("Tool",      "badge-cyan"),
    "research":    ("Research",  "badge-amber"),
    "events":      ("Event",     "badge-green"),
    "training":    ("Training",  "badge-purple"),
    "threatIntel": ("Intel",     "badge-red"),
}

CATEGORIES = list(CATEGORY_FIELDS)
