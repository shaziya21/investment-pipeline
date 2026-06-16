"""Stage 2b — Analysis.

Turns a Candidate into a full Analysis (narrative + score + call + sources).

Two ways to produce the qualitative narrative (team / product / market / risks):

  * LLM path (preferred): Claude reads ONLY the gathered facts and returns a
    structured JSON analysis. It also returns a market_score (0–1) that feeds the
    market/why-now scoring component. Requires the `anthropic` package and an
    ANTHROPIC_API_KEY.

  * Offline path (fallback): a deterministic, signal-grounded summary built from
    the same facts. It uses real numbers (stars, points, language) so the memo is
    still specific and useful, and it honestly flags the market section as "not
    assessed" rather than faking judgement.

The SCORE is computed the same way in both paths (pipeline/scoring.py); only the
prose and the market_score differ. This keeps the recommendation defensible
regardless of whether an LLM was available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from . import config, scoring
from .models import Analysis, Candidate

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analysis_prompt.md"


# --- fact formatting (shared by both paths) -------------------------------------
def _hn_facts(c: Candidate) -> str:
    if not c.hn:
        return "no Hacker News data"
    return (f"{c.hn['points']} points, {c.hn['num_comments']} comments, "
            f"submitted by @{c.hn['author']} ({c.hn.get('created_at')})")


def _github_facts(c: Candidate) -> str:
    if not c.github:
        return "no public GitHub repo found"
    g = c.github
    prof = g.get("owner_profile") or {}
    owner = ""
    if prof:
        owner = (f"; owner {prof.get('login')} "
                 f"({prof.get('followers', '?')} followers, "
                 f"bio: {prof.get('bio') or 'none'})")
    return (f"{g['full_name']} — {g['stars']} stars, {g['forks']} forks, "
            f"language {g.get('language') or 'unknown'}, "
            f"last push {g.get('days_since_push', '?')} days ago "
            f"(matched by {g['matched_by']}){owner}")


def _build_sources(c: Candidate) -> list[dict[str, str]]:
    """Every claim in a memo should be traceable. These are the underlying sources."""
    sources = [{"claim": "Sourced from Hacker News Show HN", "source": c.hn["hn_url"]}] if c.hn else []
    if c.github:
        sources.append({"claim": f"GitHub repo {c.github['full_name']} "
                                 f"({c.github['stars']} stars, matched by {c.github['matched_by']})",
                        "source": c.github["html_url"]})
        prof = c.github.get("owner_profile") or {}
        if prof.get("html_url"):
            sources.append({"claim": f"Founder/owner profile @{prof.get('login')}",
                            "source": prof["html_url"]})
    sources.append({"claim": "Product website", "source": c.website})
    return sources


# --- LLM path -------------------------------------------------------------------
def _analyze_with_claude(c: Candidate) -> Optional[dict[str, Any]]:
    """Call Claude for the narrative + market_score. Returns None if unavailable."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # imported lazily so the pipeline runs without the package
    except ImportError:
        print("  [analysis] anthropic package not installed — using offline fallback")
        return None

    prompt = _PROMPT_PATH.read_text().format(
        name=c.name,
        one_liner=c.one_liner or "unknown",
        website=c.website,
        hn_facts=_hn_facts(c),
        github_facts=_github_facts(c),
        founders_signal=c.founders_signal or "unknown",
    )

    schema = {
        "type": "object",
        "properties": {
            "team": {"type": "string"},
            "product": {"type": "string"},
            "market": {"type": "string"},
            "risks": {"type": "string"},
            "market_score": {"type": "number"},
            "change_my_mind": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["team", "product", "market", "risks", "market_score", "change_my_mind"],
        "additionalProperties": False,
    }

    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)
    except Exception as e:  # noqa: BLE001
        print(f"  [analysis] Claude call failed ({type(e).__name__}: {e}) — offline fallback")
        return None


# --- offline path ---------------------------------------------------------------
def _analyze_offline(c: Candidate) -> dict[str, Any]:
    """Deterministic, signal-grounded narrative. Specific, not generic filler."""
    # Team
    if c.founders_signal:
        prof = (c.github or {}).get("owner_profile") or {}
        extra = ""
        if prof.get("followers") is not None:
            extra = (f" The GitHub owner has {prof['followers']} followers and "
                     f"{prof.get('public_repos', '?')} public repos"
                     + (f"; bio: {prof['bio']}." if prof.get("bio") else "."))
        team = f"{c.founders_signal}.{extra} Deeper background not findable from public data (treat as unknown)."
    else:
        team = "No founder signal findable from Hacker News or GitHub — unknown."

    # Product
    product = (c.one_liner or "No description provided.").strip()
    if product and product[-1] not in ".!?":
        product += "."
    if c.github and c.github.get("language"):
        product += f" Built primarily in {c.github['language']} (per its public repo)."

    # Market — honestly not assessed offline
    market = ("Market sizing and 'why now' require analyst/LLM judgement and were NOT assessed "
              "in offline mode. Run with an ANTHROPIC_API_KEY for this section.")

    # Risks — derived from what's missing/weak in the signals
    risks: list[str] = []
    if not c.github:
        risks.append("no public repo found, so technical depth and the open-source wedge are unverified")
    elif c.github.get("matched_by") == "name_search":
        risks.append("GitHub repo was matched by name search, not a direct link — verify it's the right repo")
    if c.github and c.github.get("days_since_push") is not None and c.github["days_since_push"] > 365:
        risks.append(f"repo's last commit was {c.github['days_since_push']} days ago — possibly abandoned")
    if (c.hn or {}).get("points", 0) < config.WEAK_TRACTION_POINTS:
        risks.append("weak Hacker News traction — limited evidence of organic pull")
    if not risks:
        risks.append("main open question is durability of traction and whether the OSS wedge converts to revenue")
    risk_text = "Key risks / open questions: " + "; ".join(risks) + "."

    change: list[str] = []
    if not c.github:
        change.append("Finding an active public repo with real commit history and a technical founder")
    change.append("Evidence of post-launch traction growth (stars/users) rather than a one-day HN spike")
    change.append("A clear wedge from open-source adoption to a monetizable product")

    return {
        "team": team, "product": product, "market": market, "risks": risk_text,
        # Conservative on purpose: we did NOT assess the market, so we don't hand
        # out generous "free" points. Otherwise every signal-strong candidate
        # floats over the "Take a meeting" line and the triage stops triaging.
        # The LLM path earns a higher market score when the case is real.
        "market_score": 0.25, "change_my_mind": change,
    }


# --- public entry point ---------------------------------------------------------
def analyze_candidate(c: Candidate, use_llm: bool = True) -> Analysis:
    """Produce a full Analysis for one candidate. This is stage 2."""
    llm_result = _analyze_with_claude(c) if use_llm else None
    if llm_result is not None:
        narrative = llm_result
        generated_by = f"claude:{config.CLAUDE_MODEL}"
        llm_used = True
    else:
        narrative = _analyze_offline(c)
        generated_by = "offline-heuristic"
        llm_used = False

    score = scoring.score_candidate(c, market_score=narrative["market_score"], llm_used=llm_used)
    call, reason = scoring.decide_call(c, score)

    return Analysis(
        candidate=c,
        score=score,
        call=call,
        call_reason=reason,
        team=narrative["team"],
        product=narrative["product"],
        market=narrative["market"],
        risks=narrative["risks"],
        change_my_mind=narrative["change_my_mind"],
        sources=_build_sources(c),
        generated_by=generated_by,
    )
