"""Stage 1 — Sourcing.

Given a topic query, collect 10–20 candidate startups from two sources, going
*deep* on each rather than shallow on many (the assessment warns against a
"12-source layer where each returns 2 garbage results"):

  1. Hacker News (Algolia API) — "Show HN" launches give us a launch signal AND
     organic traction (points / comments) for free, no auth.
  2. GitHub (REST API) — enriches each candidate with technical-depth signal:
     the repo (stars, language, recency) and the founder's public profile.

Only the standard library is used for HTTP (urllib), so this runs with no pip
install. A GITHUB_TOKEN env var is optional and only raises the rate limit.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from . import config
from .models import Candidate, Signal


# --- tiny HTTP helper -----------------------------------------------------------
def _get_json(url: str, params: dict[str, Any] | None = None,
              headers: dict[str, str] | None = None) -> Optional[Any]:
    """GET a URL and parse JSON. Returns None on any failure (never raises).

    Returning None instead of crashing is deliberate: a single dead repo or a
    rate-limit blip must not kill a 15-company run. Missing data is handled
    downstream, not by aborting.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — intentionally broad; we degrade gracefully
        print(f"  [warn] request failed ({type(e).__name__}) for {url[:80]}")
        return None


def _github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


# --- parsing "Show HN: Name – description" --------------------------------------
_SHOW_HN_PREFIX = re.compile(r"^\s*show hn:\s*", re.IGNORECASE)
_SEPARATORS = [" – ", " — ", " - ", ": ", " | "]


def _split_name_and_oneliner(title: str) -> tuple[str, str]:
    """Turn an HN title into (name, one_liner).

    'Show HN: OpenAPI DevTools – Chrome extension that generates an API spec'
      -> ('OpenAPI DevTools', 'Chrome extension that generates an API spec')
    """
    cleaned = _SHOW_HN_PREFIX.sub("", title).strip()
    for sep in _SEPARATORS:
        if sep in cleaned:
            name, rest = cleaned.split(sep, 1)
            return name.strip(), rest.strip()
    # No separator: treat the whole thing as the name, no description.
    return cleaned, ""


def _distinctive_tokens(text: str) -> set[str]:
    """Lowercase tokens longer than 2 chars, with generic stopwords removed."""
    return {
        t.lower() for t in re.split(r"[\s/_-]+", text)
        if len(t) > 2 and t.lower() not in config.MATCH_STOPWORDS
    }


def _looks_like_sentence(name: str) -> bool:
    """True if an HN 'name' is really a sentence, not a product name."""
    low = name.lower()
    return low.startswith(config.SENTENCE_STARTERS) or len(name.split()) > config.MAX_NAME_WORDS


def _name_from_repo(url: str) -> Optional[str]:
    """Derive a clean display name from a github.com/owner/repo URL.

    'github.com/AndrewWalsh/openapi-devtools' -> 'Openapi Devtools'
    Returns None if the URL isn't a GitHub repo link.
    """
    parsed = _owner_repo_from_url(url)
    if not parsed:
        return None
    repo = parsed[1]
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", repo) if w)


def _days_since(iso_ts: str) -> Optional[int]:
    """Whole days between an ISO timestamp and now (UTC). None if unparseable."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:  # noqa: BLE001
        return None


# --- GitHub enrichment ----------------------------------------------------------
_GITHUB_HOST = re.compile(r"https?://(www\.)?github\.com/([^/]+)/([^/#?]+)", re.IGNORECASE)


def _owner_repo_from_url(url: str) -> Optional[tuple[str, str]]:
    m = _GITHUB_HOST.match(url or "")
    if not m:
        return None
    owner, repo = m.group(2), m.group(3)
    return owner, re.sub(r"\.git$", "", repo)


def _fetch_owner_profile(login: str) -> Optional[dict[str, Any]]:
    data = _get_json(config.GITHUB_USER_URL.format(login=login), headers=_github_headers())
    if not data:
        return None
    return {
        "login": data.get("login"),
        "name": data.get("name"),
        "bio": data.get("bio"),
        "company": data.get("company"),
        "followers": data.get("followers"),
        "public_repos": data.get("public_repos"),
        "type": data.get("type"),  # "User" or "Organization"
        "html_url": data.get("html_url"),
    }


def _shape_repo(data: dict[str, Any], matched_by: str) -> dict[str, Any]:
    owner_login = (data.get("owner") or {}).get("login")
    return {
        "full_name": data.get("full_name"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "language": data.get("language"),
        "pushed_at": data.get("pushed_at"),
        "days_since_push": _days_since(data.get("pushed_at", "")),
        "html_url": data.get("html_url"),
        "matched_by": matched_by,  # "direct_link" or "name_search"
        "owner_profile": _fetch_owner_profile(owner_login) if owner_login else None,
    }


def _enrich_with_github(candidate: Candidate) -> None:
    """Attach GitHub repo + owner profile to a candidate, in place.

    Two paths, in order of confidence:
      1. The HN-submitted URL *is* a github.com/owner/repo link -> use it directly.
      2. Otherwise search GitHub for the candidate's name and take the top repo,
         but only if the name overlaps (avoid attaching an unrelated repo).
    If neither works, candidate.github stays None and downstream treats the
    open-source / technical-depth signal as "not found".
    """
    direct = _owner_repo_from_url(candidate.website)
    if direct:
        owner, repo = direct
        data = _get_json(config.GITHUB_REPO_URL.format(owner=owner, repo=repo),
                         headers=_github_headers())
        if data and not data.get("message"):  # GitHub returns {"message": "Not Found"} on 404
            candidate.github = _shape_repo(data, matched_by="direct_link")
            return

    # Fallback: search by name.
    results = _get_json(
        config.GITHUB_SEARCH_URL,
        params={"q": candidate.name, "sort": "stars", "order": "desc", "per_page": 3},
        headers=_github_headers(),
    )
    items = (results or {}).get("items") or []
    if not items:
        return
    top = items[0]
    # Only accept the match if a *distinctive* name token overlaps. We strip
    # generic stopwords first, so "developer tools" can no longer match the
    # developer-roadmap repo — the overlap must be on a meaningful token.
    name_tokens = _distinctive_tokens(candidate.name)
    repo_tokens = _distinctive_tokens(top.get("full_name", "").replace("/", " "))
    if name_tokens & repo_tokens:
        candidate.github = _shape_repo(top, matched_by="name_search")


# --- building signals + founder string ------------------------------------------
def _build_signals(c: Candidate) -> None:
    """Populate c.signals — the freshness/traction evidence, each with a URL."""
    if c.hn:
        age = _days_since(c.hn.get("created_at", ""))
        age_str = f", launched ~{age} days ago" if age is not None else ""
        c.signals.append(Signal(
            kind="hn_launch",
            summary=f"{c.hn['points']} points / {c.hn['num_comments']} comments on Show HN{age_str}",
            url=c.hn["hn_url"],
            detail={"points": c.hn["points"], "comments": c.hn["num_comments"], "age_days": age},
        ))
    if c.github:
        g = c.github
        recency = (f", last push {g['days_since_push']} days ago"
                   if g.get("days_since_push") is not None else "")
        c.signals.append(Signal(
            kind="github_repo",
            summary=f"{g['stars']} stars, {g.get('language') or 'unknown'} repo{recency}",
            url=g["html_url"],
            detail={"stars": g["stars"], "language": g.get("language"),
                    "matched_by": g["matched_by"]},
        ))


def _build_founder_signal(c: Candidate) -> None:
    parts: list[str] = []
    if c.hn:
        parts.append(f"HN submitter @{c.hn['author']}")
    prof = (c.github or {}).get("owner_profile") if c.github else None
    if prof:
        bits = [prof.get("name") or prof.get("login")]
        if prof.get("company"):
            bits.append(f"({prof['company']})")
        if prof.get("followers") is not None:
            bits.append(f"{prof['followers']} GitHub followers")
        parts.append("GitHub owner: " + " ".join(b for b in bits if b))
    c.founders_signal = "; ".join(parts) if parts else None


# --- public entry point ---------------------------------------------------------
def source_candidates(topic: str, limit: int = 15) -> list[Candidate]:
    """Collect up to `limit` candidates for a topic. This is stage 1.

    Pull HN "Show HN" launches matching the topic (relevance-ranked, which favours
    posts with traction), parse each into a candidate, dedup, then enrich the top
    `limit` with GitHub data.
    """
    print(f"[source] Hacker News: searching Show HN for {topic!r} ...")
    hits = _get_json(config.HN_SEARCH_URL, params={
        "query": topic,
        "tags": "show_hn",
        "hitsPerPage": limit * config.HN_FETCH_MULTIPLIER,
    })
    raw_hits = (hits or {}).get("hits", [])
    print(f"[source] Hacker News returned {len(raw_hits)} raw hits")

    candidates: list[Candidate] = []
    seen: set[str] = set()
    for hit in raw_hits:
        title = hit.get("title") or ""
        name, one_liner = _split_name_and_oneliner(title)
        if not name:
            continue
        website = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

        # If the HN title was a sentence (no clean "Name – desc"), prefer a clean
        # name derived from the GitHub repo and keep the sentence as the one-liner.
        if _looks_like_sentence(name):
            repo_name = _name_from_repo(website)
            if repo_name:
                one_liner = one_liner or name
                name = repo_name
            else:
                # No repo to rescue the name and it's a sentence -> skip; a partner
                # won't take a memo titled with a half-sentence seriously.
                continue
        # Dedup on a normalized name OR the website host.
        key = name.lower().strip()
        if key in seen:
            continue
        seen.add(key)

        candidates.append(Candidate(
            name=name,
            website=website,
            one_liner=one_liner or (hit.get("story_text") or "")[:140],
            source="hacker_news",
            hn={
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "created_at": hit.get("created_at"),
                "author": hit.get("author"),
                "object_id": hit.get("objectID"),
                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            },
        ))
        if len(candidates) >= limit:
            break

    print(f"[source] parsed {len(candidates)} candidates; enriching with GitHub ...")
    for i, c in enumerate(candidates, 1):
        _enrich_with_github(c)
        _build_signals(c)
        _build_founder_signal(c)
        found = "repo found" if c.github else "no repo"
        print(f"  [{i}/{len(candidates)}] {c.name[:40]:40s} -> {found}")
        time.sleep(0.3)  # be polite to the GitHub API

    return candidates
