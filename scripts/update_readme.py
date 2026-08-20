#!/usr/bin/env python3
"""
update_readme.py
~~~~~~~~~~~~~~~~
Reads README.template.md, fetches live data from the GitHub API and the
ai-weekly-digest site, substitutes all placeholders, and writes README.md.

Placeholders in the template
-----------------------------
  GITHUB_USER        — replaced with the actual GitHub username
  {RECENT_ACTIVITY}  — last N push-event commits across all public repos
  {TOTAL_STARS}      — sum of stargazers_count across all owned repos
  {WEEKLY_DIGEST}    — headline + summary from the latest digest JSON
  {LAST_UPDATED}     — UTC timestamp of this run

Environment variables
---------------------
  GITHUB_TOKEN   — GitHub personal-access token (or Actions GITHUB_TOKEN)
  GITHUB_USER    — GitHub username; falls back to social.github in profile.yml
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "README.template.md"
README_PATH   = BASE_DIR / "README.md"
PROFILE_PATH  = BASE_DIR / "data" / "profile.yml"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_profile_cache: dict | None = None


def load_profile() -> dict:
    global _profile_cache
    if _profile_cache is None:
        with PROFILE_PATH.open(encoding="utf-8") as fh:
            _profile_cache = yaml.safe_load(fh)
    return _profile_cache


def get_github_user() -> str:
    """Resolve username: env var > profile.yml > abort."""
    username = os.environ.get("GITHUB_USER", "").strip()
    if not username:
        profile = load_profile()
        username = profile.get("social", {}).get("github", "").strip()
    if not username:
        sys.exit("ERROR: GITHUB_USER env var not set and profile.yml has no social.github.")
    return username


def _session() -> requests.Session:
    s = requests.Session()
    if GITHUB_TOKEN:
        s.headers["Authorization"] = f"token {GITHUB_TOKEN}"
    s.headers["Accept"] = "application/vnd.github.v3+json"
    s.headers["User-Agent"] = "readme-updater/1.0"
    return s


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def fetch_total_stars(username: str, session: requests.Session) -> int:
    """Sum stargazers_count over all owned public repos (handles pagination)."""
    total = 0
    page = 1
    while True:
        resp = session.get(
            f"https://api.github.com/users/{username}/repos",
            params={"type": "owner", "per_page": 100, "page": page},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: repos page {page} returned {resp.status_code}")
            break
        repos = resp.json()
        if not repos:
            break
        total += sum(r.get("stargazers_count", 0) for r in repos)
        if len(repos) < 100:
            break
        page += 1
    return total


def fetch_recent_activity(username: str, session: requests.Session, limit: int = 5) -> str:
    """Return a Markdown bullet list of the most recent push-event commits."""
    resp = session.get(
        f"https://api.github.com/users/{username}/events/public",
        params={"per_page": 100},
        timeout=15,
    )
    if resp.status_code != 200:
        return "- 🔨 Recent activity unavailable"

    lines: list[str] = []
    for event in resp.json():
        if event.get("type") != "PushEvent":
            continue
        repo_name = event.get("repo", {}).get("name", "?")
        for commit in event.get("payload", {}).get("commits", []):
            msg = commit.get("message", "").splitlines()[0][:80]
            lines.append(f"- 🔨 `{repo_name}` — {msg}")
            if len(lines) >= limit:
                break
        if len(lines) >= limit:
            break

    return "\n".join(lines) if lines else "- 🔨 No recent public push activity found"


# ---------------------------------------------------------------------------
# Digest helper
# ---------------------------------------------------------------------------

def fetch_weekly_digest(username: str) -> str:
    """Fetch the latest digest headline from the GitHub Pages JSON endpoint."""
    profile = load_profile()
    url = profile.get("digest_url") or (
        f"https://{username}.github.io/ai-weekly-digest/_data/latest.json"
    )
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "readme-updater/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            title   = data.get("title", "Untitled")
            date    = data.get("date", "")
            summary = data.get("summary", "").strip()
            base_url = url.rsplit("_data/", 1)[0]
            header = f"**[{title}]({base_url})** ({date})" if date else f"**[{title}]({base_url})**"
            return f"{header}\n\n> {summary}" if summary else header
    except Exception as exc:
        print(f"  Info: digest fetch failed — {exc}")
    return "_最新周刊即将发布，敬请期待..._"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    username = get_github_user()
    print(f"Updating README for GitHub user: {username}")

    # Read template
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    session = _session()

    # --- Total stars ---
    try:
        total_stars = str(fetch_total_stars(username, session))
        print(f"  Total stars: {total_stars}")
    except Exception as exc:
        print(f"  Warning: could not fetch stars — {exc}")
        total_stars = "N/A"

    # --- Recent activity ---
    try:
        recent_activity = fetch_recent_activity(username, session)
        print(f"  Recent activity: {recent_activity.count(chr(10)) + 1} lines")
    except Exception as exc:
        print(f"  Warning: could not fetch activity — {exc}")
        recent_activity = "- 🔨 Activity unavailable"

    # --- Weekly digest ---
    try:
        weekly_digest = fetch_weekly_digest(username)
        print(f"  Digest: {weekly_digest[:60]}...")
    except Exception as exc:
        print(f"  Warning: could not fetch digest — {exc}")
        weekly_digest = "_Digest unavailable_"

    # --- Timestamp ---
    last_updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # --- Substitutions ---
    content = template
    content = content.replace("GITHUB_USER",        username)
    content = content.replace("{RECENT_ACTIVITY}",  recent_activity)
    content = content.replace("{TOTAL_STARS}",      total_stars)
    content = content.replace("{WEEKLY_DIGEST}",    weekly_digest)
    content = content.replace("{LAST_UPDATED}",     last_updated)

    # --- Write ---
    README_PATH.write_text(content, encoding="utf-8")
    print(f"README.md written to {README_PATH}")


if __name__ == "__main__":
    main()
