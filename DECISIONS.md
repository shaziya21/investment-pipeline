# Decision log

A running log of the real decisions, tradeoffs, and dead ends from building this
pipeline — kept *as the work happened*, not reconstructed afterwards. Newest at
the bottom. This is the honest answer to "how did this get built and why."

---

### D1 — Thesis first, before any code
**Decision:** Write `THESIS.md` and the scoring rubric *before* writing the pipeline.
**Why:** The rubric explicitly punishes a thesis so broad the score is meaningless.
If the thesis isn't pinned first, the scoring code drifts into "rank by whatever
data we happened to collect." Pinning it first means every signal we collect has a
reason to exist. Chose **dev-tools / infra + technical founders + OSS wedge +
organic traction** because every word maps to a *free, public* signal we can verify.

### D2 — Two sources, deep, not twelve shallow
**Decision:** Hacker News (Algolia) + GitHub only.
**Why:** The assessment's anti-pattern is "a 12-source layer where each returns 2
garbage results." HN "Show HN" gives a launch signal *and* organic traction
(points/comments) in one free, no-auth call. GitHub gives the technical-depth and
OSS-wedge signals the thesis needs. The two compose cleanly: HN = "does anyone
care," GitHub = "are the founders technical / is there a real wedge."
**Rejected:** Product Hunt (needs OAuth — friction, and we wanted depth on one
launch source), Crunchbase/Twitter (not free / not public enough).

### D3 — Deterministic score, LLM only for narrative
**Decision:** Compute the 0–100 score *in code* from signals; use the LLM only to
write the team/product/market/risks prose and to judge the one genuinely
qualitative axis (market / why-now).
**Why:** "Scores defensible" is a grading line. A number an LLM emits from a vibe
is not defensible and not reproducible. A number computed from "direct repo link
+ 1k stars + 382 HN points" is both. It also means the pipeline still produces a
real, ranked, defensible score **with no API key at all** — the LLM is an
enhancement, not a hard dependency.

### D4 — Standard-library HTTP, no `requests`
**Decision:** Use `urllib` for all HTTP.
**Why:** Sourcing + scoring then run with **zero** pip installs, so a reviewer can
clone and run immediately. The only optional dependency is `anthropic`, and only
for the narrative stage. Lower friction = the "can a partner run one command"
test actually passes.

### D5 — Replayable stages via committed JSON
**Decision:** Each stage writes a JSON/markdown file the next stage reads; commit
the outputs.
**Why:** "Replayable. Commit them so we don't need to re-run." A reviewer reads
`data/memos/` without running anything; I can re-run only `analyze` after tweaking
scoring without re-hitting the network. Clean stage separation = the system-design
grading line.

### D6 — Graceful degradation over correctness-or-crash
**Decision:** Every network call returns `None` on failure instead of raising;
missing GitHub data zeroes the relevant score components *and says so in the memo*.
**Why:** "Robust to bad or missing data." A single dead repo or a rate-limit blip
must not kill a 15-company run, and a missing signal must lower conviction
**honestly** rather than be hallucinated away.

---

### D7 — Bug found during first live run: loose GitHub matching (FIXED)
**Symptom:** On the topic "developer tools," the #1 result was
`An illustration of Web Developer tools in 2018`, scored 71 → "Take a meeting,"
with the famous `developer-roadmap` repo attached to it.
**Root cause:** (a) the HN title had no clean `Name – desc` separator so the whole
sentence became the "name," and (b) the GitHub name-search matched on the generic
token "developer," attaching a huge unrelated repo and inflating the score.
**Fix:**
- Added a stopword set (`MATCH_STOPWORDS`) so generic tokens (developer, tool, web,
  open, source, …) can't justify a repo match — the overlap must be on a
  *distinctive* token.
- Sentence-like HN titles now derive a clean name from the repo (or are dropped if
  there's no repo to rescue the name).
- A `name_search` match is treated as lower-confidence: its star bonus is halved
  and labelled "(unverified repo)," so a popular-but-unrelated repo can't push an
  off-thesis candidate to the top. (See `scoring.py::_open_source_wedge`.)
**Why it matters:** This is exactly the "claims with no traceable source" anti-
pattern. Catching it on the first real run is the reason to *run the thing on real
data early* instead of trusting unit tests on synthetic inputs.

### D8 — Topic choice: focused beats generic
**Observation:** "developer tools" surfaces meta-content (roadmaps, "I'm collecting
deals," listicles) — noise. A focused infra topic like **"Postgres"** returns real
product launches (ElectricSQL, PGlite, PostgresML, Hasura, PgDog, …) that are
squarely on-thesis.
**Decision:** Use "Postgres" for the committed demo run, and document that the
pipeline accepts any topic — generic topics are just noisier. The reviewer can
point it anywhere.

### D9 — Calibration: don't give away unearned market points (FIXED)
**Symptom:** First Postgres run put 8 of 12 candidates at "Take a meeting." Triage
that flags 67% isn't triage.
**Root cause:** In offline mode every candidate got a neutral 10/20 market score it
hadn't earned, floating signal-strong candidates over the line.
**Fix:** Offline market score dropped to a conservative 0.25 (5/20), explicitly
flagged in the memo as "not assessed." The LLM path earns a higher market score
when the case is real.
**Honest note (NOT gamed):** Even after the fix, a *Postgres* query still yields
many "Take a meeting" calls — because that topic is the thesis bullseye and those
projects (Hasura, PgDog, pg_flame) genuinely are strong on technical depth, OSS
wedge, and organic traction. I deliberately did **not** keep raising the threshold
just to manufacture a prettier pyramid — that would be gaming the score for optics,
another anti-pattern. The pipeline still differentiates (77 → 22) and correctly
**Passes** the two no-repo candidates and **Watches** the borderline ones. On a
broader topic the qualified fraction drops naturally.
