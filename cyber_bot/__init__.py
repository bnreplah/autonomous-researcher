"""Cyber Research Bot — GitHub-driven cybersecurity news + research digest poster.

Pulls items from public security feeds (news, advisories, CVEs, academic
preprints), uses an LLM to score relevance and produce concise briefings,
and posts to a Discord channel via webhook. Designed to run from GitHub
Actions (scheduled cron + issue-triggered on-demand research).
"""

__all__ = ["sources", "researcher", "discord_client", "state", "config"]
