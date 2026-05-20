"""Schema for RESOURCES_DB.js categories.

Keeps the LLM and the merge step on the same page about which fields
are required for each category, and which badge classes are valid.
The category list mirrors what is actually present in the live
RESOURCES_DB.js (32 categories at time of writing).
"""

from __future__ import annotations

# Most non-feed categories share the same shape. Keep it as a constant
# so we don't have to repeat it 25 times.
_STD_FIELDS = ["title", "url", "badge", "badgeClass", "cat", "desc", "tags"]
_STD_FIELDS_NO_CAT = ["title", "url", "badge", "badgeClass", "desc", "tags"]

# Required fields per category, in canonical display order.
CATEGORY_FIELDS: dict[str, list[str]] = {
    # Feeds / RSS lists.
    "liveFeeds":     ["id", "name", "url", "site", "color"],
    "rssNews":       ["name", "site", "rss"],
    "rssVendor":     ["name", "site", "rss"],
    "rssIndy":       ["name", "site", "rss"],

    # Specialised shapes.
    "events":        ["title", "url", "badge", "badgeClass", "cat",
                      "desc", "location", "date", "cost", "tags"],
    "research":      _STD_FIELDS_NO_CAT,
    "tools":         _STD_FIELDS,
    "training":      _STD_FIELDS_NO_CAT,
    "threatIntel":   _STD_FIELDS_NO_CAT,

    # Domain-specific shelves (all share the standard cat-included shape).
    "enterprise":     _STD_FIELDS,
    "pentesting":     _STD_FIELDS_NO_CAT,
    "vulnmanagement": _STD_FIELDS,
    "communities":    _STD_FIELDS_NO_CAT,
    "appsec":         _STD_FIELDS,
    "datasec":        _STD_FIELDS,
    "networksec":     _STD_FIELDS,
    "physicalsec":    _STD_FIELDS,
    "cloudsec":       _STD_FIELDS,
    "blueteam":       _STD_FIELDS,
    "devsecops":      _STD_FIELDS,
    "iam":            _STD_FIELDS,
    "asm":            _STD_FIELDS,
    "mobile":         _STD_FIELDS,
    "compliance":     _STD_FIELDS,
    "programming":    _STD_FIELDS,
    "maker":          _STD_FIELDS,
    "blogs":          _STD_FIELDS,
    "youtube":        _STD_FIELDS,
    "podcasts":       _STD_FIELDS,
    "newsletters":    _STD_FIELDS,
    "conferences":    _STD_FIELDS,
    "culture":        _STD_FIELDS,
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
    "enterprise":     ("Enterprise security platforms and suites "
                       "(SIEM, XDR, EDR, SOAR, ZTNA, CASB)."),
    "pentesting":     ("Penetration-testing distributions, suites, and "
                       "training labs."),
    "vulnmanagement": ("Vulnerability management platforms, scanners, "
                       "and prioritisation tools."),
    "communities":    ("Cybersecurity communities, Discord/Slack servers, "
                       "subreddits, and mailing lists."),
    "appsec":         ("Application security tools, libraries, and "
                       "resources (SAST, DAST, IAST, fuzzing, secure "
                       "coding)."),
    "datasec":        ("Data security and privacy tools (DLP, encryption, "
                       "tokenisation, differential privacy)."),
    "networksec":     ("Network security tools and platforms (firewalls, "
                       "IDS/IPS, NDR, packet analysis)."),
    "physicalsec":    ("Physical security and lock-picking / RFID / "
                       "tamper-evidence resources."),
    "cloudsec":       ("Cloud security tools and frameworks (CSPM, CWPP, "
                       "CIEM, Kubernetes security)."),
    "blueteam":       ("Blue-team / defender tooling: detection, IR, "
                       "threat hunting, deception."),
    "devsecops":      ("DevSecOps tooling: secrets scanning, SBOM, "
                       "supply-chain security, CI/CD security."),
    "iam":            ("Identity and access management tooling and "
                       "standards."),
    "asm":            ("Attack-surface management platforms and "
                       "external-recon services."),
    "mobile":         ("Mobile security tools (Android / iOS reversing, "
                       "MASVS, MobSF)."),
    "compliance":     ("Compliance, audit, and GRC platforms and "
                       "frameworks."),
    "programming":    ("Programming references, security-relevant "
                       "languages, libraries, and learning paths."),
    "maker":          ("Hardware / maker resources: HW hacking, "
                       "embedded, IoT, soldering kits."),
    "blogs":          ("Notable cybersecurity blogs (personal or "
                       "company) worth bookmarking."),
    "youtube":        ("Notable cybersecurity YouTube channels."),
    "podcasts":       ("Notable cybersecurity podcasts."),
    "newsletters":    ("Notable cybersecurity newsletters."),
    "conferences":    ("Recurring conferences beyond the headline events "
                       "list (regional / specialised)."),
    "culture":        ("Cybersecurity culture: books, movies, games, "
                       "documentaries, history."),
}

# Sensible badge defaults per category (the LLM may override).
DEFAULT_BADGE: dict[str, tuple[str, str]] = {
    # category -> (badge_text, badge_class)
    "tools":          ("Tool",      "badge-cyan"),
    "research":       ("Research",  "badge-amber"),
    "events":         ("Event",     "badge-green"),
    "training":       ("Training",  "badge-purple"),
    "threatIntel":    ("Intel",     "badge-red"),
    "enterprise":     ("Enterprise","badge-purple"),
    "pentesting":     ("Pentest",   "badge-red"),
    "vulnmanagement": ("VulnMgmt",  "badge-amber"),
    "communities":    ("Community", "badge-green"),
    "appsec":         ("AppSec",    "badge-amber"),
    "datasec":        ("DataSec",   "badge-cyan"),
    "networksec":     ("NetSec",    "badge-cyan"),
    "physicalsec":    ("Physical",  "badge-magenta"),
    "cloudsec":       ("Cloud",     "badge-cyan"),
    "blueteam":       ("Blue Team", "badge-cyan"),
    "devsecops":      ("DevSecOps", "badge-green"),
    "iam":            ("IAM",       "badge-purple"),
    "asm":            ("ASM",       "badge-amber"),
    "mobile":         ("Mobile",    "badge-magenta"),
    "compliance":     ("Compliance","badge-purple"),
    "programming":    ("Code",      "badge-green"),
    "maker":          ("Maker",     "badge-magenta"),
    "blogs":          ("Blog",      "badge-cyan"),
    "youtube":        ("Video",     "badge-red"),
    "podcasts":       ("Podcast",   "badge-magenta"),
    "newsletters":    ("Newsletter","badge-amber"),
    "conferences":    ("Conference","badge-green"),
    "culture":        ("Culture",   "badge-magenta"),
}

CATEGORIES = list(CATEGORY_FIELDS)
