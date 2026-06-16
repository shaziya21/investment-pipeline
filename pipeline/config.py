"""Central configuration: thesis weights, scoring thresholds, and constants.

Everything tunable lives here so the thesis (THESIS.md) and the code agree in one
place. If a reviewer wants to challenge a weight, this is the single file to read.
"""

from __future__ import annotations

# --- Model used for the LLM narrative stage -------------------------------------
# We default to Claude Opus 4.8. The pipeline still runs fully without a key
# (see pipeline/analysis.py -> offline fallback); the LLM only writes the prose.
CLAUDE_MODEL = "claude-opus-4-8"

# --- Sourcing -------------------------------------------------------------------
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
GITHUB_REPO_URL = "https://api.github.com/repos/{owner}/{repo}"
GITHUB_USER_URL = "https://api.github.com/users/{login}"
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

HTTP_TIMEOUT = 15  # seconds, per request
USER_AGENT = "investment-pipeline/0.1 (take-home; contact via repo)"

# How many HN hits to pull before filtering/dedup down to the target count.
HN_FETCH_MULTIPLIER = 3

# Generic words that must NOT, on their own, justify matching a startup name to a
# GitHub repo. Without this, "developer tools" matches the famous
# developer-roadmap repo and inflates the score with an unrelated project.
MATCH_STOPWORDS = {
    "developer", "developers", "dev", "tool", "tools", "app", "apps", "web",
    "open", "source", "opensource", "api", "data", "the", "for", "with", "and",
    "your", "new", "free", "online", "platform", "framework", "library", "cli",
    "made", "built", "create", "created", "build", "project", "simple", "easy",
}

# HN titles starting with these (or longer than this many words) are treated as
# sentences, not product names — we then prefer a clean name from the repo.
SENTENCE_STARTERS = ("i ", "i'", "my ", "an ", "a ", "we ", "how ", "this ", "the ")
MAX_NAME_WORDS = 6

# Languages we treat as signals of technical depth, by tier.
SYSTEMS_LANGS = {"Rust", "Go", "C", "C++", "Zig", "Elixir", "Erlang", "Haskell", "OCaml"}
COMMON_DEV_LANGS = {
    "TypeScript", "Python", "JavaScript", "Java", "Ruby", "Kotlin",
    "Swift", "Scala", "C#", "PHP", "Clojure",
}

# --- Scoring weights (must sum to 100; asserted at import) ----------------------
W_TECHNICAL_DEPTH = 30
W_OPEN_SOURCE_WEDGE = 25
W_ORGANIC_TRACTION = 25
W_MARKET_TIMING = 20

assert (
    W_TECHNICAL_DEPTH + W_OPEN_SOURCE_WEDGE + W_ORGANIC_TRACTION + W_MARKET_TIMING == 100
), "Scoring weights must sum to 100"

# --- Recommendation thresholds --------------------------------------------------
SCORE_TAKE_MEETING = 68  # >= this -> "Take a meeting"
SCORE_WATCH = 48         # >= this (and below take-meeting) -> "Watch"; below -> "Pass"

# Data-quality override: no repo found AND HN points below this -> cap call at Pass.
WEAK_TRACTION_POINTS = 50

CALL_TAKE_MEETING = "Take a meeting"
CALL_WATCH = "Watch"
CALL_PASS = "Pass"
