"""Data shapes passed between the three stages.

We use plain dataclasses (no database, no ORM). Each stage serializes to JSON so
the pipeline is *replayable*: a reviewer can read data/candidates.json without
re-running sourcing, re-run only analysis, etc.

Design note for beginners: a dataclass is just a typed struct. `to_dict()` /
`from_dict()` convert to and from the JSON we commit to the repo.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Signal:
    """One freshness or traction signal, always carrying its source URL.

    Every claim in a memo must be traceable (assessment requirement), so a
    Signal never exists without the URL it came from.
    """

    kind: str          # e.g. "hn_launch", "github_repo"
    summary: str       # human-readable, e.g. "811 points / 102 comments on HN"
    url: str           # where a reviewer can verify it
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Candidate:
    """A sourced startup. Produced by stage 1 (sourcing)."""

    name: str
    website: str
    one_liner: str
    source: str                       # "hacker_news"
    hn: Optional[dict[str, Any]] = None       # points, num_comments, created_at, author, hn_url, object_id
    github: Optional[dict[str, Any]] = None   # full_name, stars, forks, pushed_at, language, html_url, matched_by, owner_profile
    founders_signal: Optional[str] = None     # short human string about the team
    signals: list[Signal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Candidate":
        d = dict(d)
        d["signals"] = [Signal(**s) for s in d.get("signals", [])]
        return cls(**d)


@dataclass
class ScoreBreakdown:
    """The 0–100 score, component by component, with a note explaining each.

    The notes are what make the score *defensible*: you can read why each number
    came out the way it did.
    """

    technical_depth: int
    open_source_wedge: int
    organic_traction: int
    market_timing: int
    total: int
    notes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Analysis:
    """Full analysis of one candidate. Produced by stage 2."""

    candidate: Candidate
    score: ScoreBreakdown
    call: str                          # Pass / Watch / Take a meeting
    team: str
    product: str
    market: str
    risks: str
    change_my_mind: list[str]
    sources: list[dict[str, str]]      # [{"claim": ..., "source": <url>}]
    generated_by: str                  # "claude:<model>" or "offline-heuristic"
    call_reason: str = ""              # why this call (incl. any data-quality override)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Analysis":
        d = dict(d)
        d["candidate"] = Candidate.from_dict(d["candidate"])
        d["score"] = ScoreBreakdown(**d["score"])
        return cls(**d)
