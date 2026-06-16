# How this was built (and how AI was used)

This project was built **with an AI coding agent (Claude Code) under my direction.**
Per the assessment's ground rules, I'm being explicit about that rather than hiding
it — the point is to show how I worked *with* the tool, what I decided, and where I
intervened.

> ⚠️ **To the person submitting this:** the section **"My reflection (in my own
> words)"** at the bottom is intentionally left for *you* to fill in by hand. The
> assessment says ghostwritten reflection is obvious and penalized — so write that
> part yourself, in your own voice. Everything above it is a factual build record.

## What the AI did vs. what I decided

**I owned the judgment calls:**
- The **thesis** (dev-tools/infra, technical founders, OSS wedge, organic traction)
  and that it had to be pinned before any code.
- The **two-source choice** (HN + GitHub) and going deep instead of wide.
- The key architecture call: **score deterministically in code, use the LLM only
  for the narrative** — so the score is defensible and the pipeline runs without a key.
- The calibration judgment in D9: *not* gaming the threshold to fake a nicer
  distribution.

**The agent did the mechanical building:** wrote the module code, the HTTP/parsing
plumbing, the markdown rendering, and the unit tests, from my instructions. I
reviewed each stage's output and redirected when something was wrong.

## The trail to look at

- **`DECISIONS.md`** — the running decision log, including two real bugs caught by
  running on live data (D7: a loose GitHub match that attached the `developer-roadmap`
  repo to an unrelated post; D9: a calibration flaw where 67% of candidates were
  flagged "Take a meeting").
- **`git log`** — commits are grouped by stage to tell the story: thesis → sourcing
  → scoring → analysis → memo → docs → example run. Not one big "add everything"
  dump. The two bugs I hit on live data are written up in `DECISIONS.md` (D7, D9).
- **`prompts/analysis_prompt.md`** — the actual LLM prompt, kept as a versioned file,
  including the "cite or say unknown" anti-hallucination rule.

## Things that went wrong (and what fixed them)

1. **Trusting unit tests over real data.** The scoring logic passed every unit test,
   but the *first live run* immediately surfaced a garbage #1 result (D7). Lesson
   reinforced: run the real thing on real inputs early; synthetic tests don't catch
   "this matched the wrong repo."
2. **Unearned points inflating the call.** Offline mode handing out a neutral market
   score made the triage stop triaging (D9). Fixed by being conservative about
   scores we didn't actually earn.
3. **Generic topic = noisy results.** "developer tools" surfaced roadmaps and
   listicles; "Postgres" surfaced real startups. Documented rather than hidden.

## Honesty about current limitations

- The committed `data/` was generated in **offline mode** (no `ANTHROPIC_API_KEY` was
  available in the build environment), so the **Market** section of each memo says
  "not assessed." The LLM path is fully implemented (`pipeline/analysis.py`) and runs
  when a key is present — see the README for how to regenerate with Claude.
- GitHub's unauthenticated rate limit (60/hr) bites on repeated runs; a `GITHUB_TOKEN`
  removes that. Some candidates show "no repo" purely because a call was rate-limited,
  not because no repo exists — the pipeline degrades honestly rather than guessing.

---

## My reflection (in my own words)

<!--
WRITE THIS YOURSELF. A few honest prompts to answer in your own voice:
- Where did you push back on the agent, or throw away what it produced?
- Which decision were you least sure about, and why?
- What would you do differently or build next with another day?
- What did working this way teach you about using AI well?
Keep it real and specific. Do not let a model write this part.
-->

_(your reflection goes here)_
