"""Stage 2a — Deterministic scoring.

This is the backbone of the whole pipeline. The 0–100 score is computed *in code*
from observable public signals, so it is fully reproducible: the same candidate
always produces the same score, and every number can be traced to a signal.

Three of the four components (technical depth, open-source wedge, organic
traction) are 100% deterministic. The fourth (market / why-now) needs human/LLM
judgement, so it takes a `market_score` in [0, 1] from the analysis stage; when no
LLM is available we pass a neutral 0.5 and say so in the note.
"""

from __future__ import annotations

from . import config
from .models import Candidate, ScoreBreakdown


def _technical_depth(c: Candidate) -> tuple[int, str]:
    """Max 30. Public repo + language tier + founder GitHub profile."""
    if not c.github:
        return 0, "No public GitHub repo found — technical depth could not be verified."

    g = c.github
    score = 18 if g["matched_by"] == "direct_link" else 10
    why = ["repo via direct HN link" if g["matched_by"] == "direct_link"
           else "repo via name search (lower confidence)"]

    lang = g.get("language")
    if lang in config.SYSTEMS_LANGS:
        score += 12
        why.append(f"systems language ({lang})")
    elif lang in config.COMMON_DEV_LANGS:
        score += 8
        why.append(f"developer language ({lang})")
    elif lang:
        score += 4
        why.append(f"language: {lang}")

    prof = g.get("owner_profile") or {}
    if (prof.get("followers") or 0) >= 500:
        why.append(f"founder has {prof['followers']} GitHub followers")

    score = min(score, config.W_TECHNICAL_DEPTH)
    return score, "; ".join(why) + "."


def _open_source_wedge(c: Candidate) -> tuple[int, str]:
    """Max 25. Public repo exists + star count."""
    if not c.github:
        return 0, "No public repo — no open-source wedge."
    g = c.github
    direct = g["matched_by"] == "direct_link"
    score = 12 if direct else 6
    stars = g.get("stars", 0)
    if stars >= 1000:
        bonus, label = 13, "1k+ stars"
    elif stars >= 200:
        bonus, label = 9, "200+ stars"
    elif stars >= 50:
        bonus, label = 5, "50+ stars"
    elif stars >= 10:
        bonus, label = 2, "10+ stars"
    else:
        bonus, label = 0, "<10 stars"

    # A name-search match might not actually be *their* repo, so we don't give
    # full credit for its stars — halve the bonus and flag the uncertainty. This
    # stops a popular-but-unrelated repo (e.g. a roadmap repo matched by name)
    # from inflating an off-thesis candidate to the top of the funnel.
    if not direct:
        bonus = bonus // 2
        label += ", name-matched (unverified repo)"

    score = min(score + bonus, config.W_OPEN_SOURCE_WEDGE)
    return score, f"public repo, {label} ({stars})."


def _organic_traction(c: Candidate) -> tuple[int, str]:
    """Max 25. HN points + HN comments (attention they *earned*)."""
    if not c.hn:
        return 0, "No HN traction signal."
    pts = c.hn.get("points", 0)
    com = c.hn.get("num_comments", 0)

    if pts >= 500:
        p_score = 15
    elif pts >= 200:
        p_score = 11
    elif pts >= 80:
        p_score = 7
    elif pts >= 30:
        p_score = 3
    else:
        p_score = 1 if pts else 0

    if com >= 100:
        c_score = 10
    elif com >= 40:
        c_score = 6
    elif com >= 10:
        c_score = 3
    else:
        c_score = 1 if com else 0

    score = min(p_score + c_score, config.W_ORGANIC_TRACTION)
    return score, f"{pts} HN points, {com} comments."


def _market_timing(market_score: float, llm_used: bool) -> tuple[int, str]:
    """Max 20. Qualitative — comes from the analysis stage's judgement."""
    market_score = max(0.0, min(1.0, market_score))
    score = round(market_score * config.W_MARKET_TIMING)
    if llm_used:
        return score, f"Claude market judgement {market_score:.2f} -> {score}/20."
    return score, ("Not assessed (no LLM) — conservative placeholder so unscored market "
                   f"doesn't inflate the call; confirm manually -> {score}/20.")


def score_candidate(c: Candidate, market_score: float = 0.5,
                    llm_used: bool = False) -> ScoreBreakdown:
    """Combine the four components into a 0–100 ScoreBreakdown with notes."""
    td, td_note = _technical_depth(c)
    wedge, wedge_note = _open_source_wedge(c)
    traction, traction_note = _organic_traction(c)
    market, market_note = _market_timing(market_score, llm_used)

    total = max(0, min(100, td + wedge + traction + market))
    return ScoreBreakdown(
        technical_depth=td,
        open_source_wedge=wedge,
        organic_traction=traction,
        market_timing=market,
        total=total,
        notes={
            "technical_depth": td_note,
            "open_source_wedge": wedge_note,
            "organic_traction": traction_note,
            "market_timing": market_note,
        },
    )


def decide_call(c: Candidate, score: ScoreBreakdown) -> tuple[str, str]:
    """Map a score to Pass / Watch / Take a meeting, applying the data-quality override.

    Returns (call, reason). The override is how we stay robust to missing data:
    a company we couldn't verify (no repo) and that has weak traction is capped at
    Pass no matter what the raw number says.
    """
    weak_traction = (c.hn or {}).get("points", 0) < config.WEAK_TRACTION_POINTS
    if not c.github and weak_traction:
        return (config.CALL_PASS,
                f"Data-quality override: no public repo found and only "
                f"{(c.hn or {}).get('points', 0)} HN points — insufficient signal to act on, "
                f"so capped at Pass (raw score {score.total}).")

    if score.total >= config.SCORE_TAKE_MEETING:
        return config.CALL_TAKE_MEETING, f"Score {score.total} ≥ {config.SCORE_TAKE_MEETING}."
    if score.total >= config.SCORE_WATCH:
        return config.CALL_WATCH, f"Score {score.total} in [{config.SCORE_WATCH}, {config.SCORE_TAKE_MEETING})."
    return config.CALL_PASS, f"Score {score.total} < {config.SCORE_WATCH}."
