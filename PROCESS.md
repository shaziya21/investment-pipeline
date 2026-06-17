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

**Where did I push back on the agent / throw away what it produced?**
When I ran the "developer tools" topic, the number-one result was "developer-roadmap",
which isn't even a startup — and the result it generated was wrong. It got a score of 71
and a "Take a meeting" call, which was wrong because developer-roadmap is not a startup but
the agent was treating it as one. So I pointed that out and we fixed that part, and I changed
the topic from "developer tools" to "Postgres". I learned that I shouldn't trust the output
just because it ran successfully.

**Which decision was I least sure about, and why?**
I was least sure about the threshold part, where a score greater than 68 gave a "Take a
meeting" — that number felt randomly chosen to me. Also, when I wasn't using the LLM, the
agent gave 0.25 to the market component, which also looks random and not really calculated.

**What would I do differently or build next with another day?**
With another day, I'd use a real Claude key to fill in the market section, and I'd add a
founder's LinkedIn/Twitter signal. I'd also connect Product Hunt and YC data, and I would
calibrate the score more so that we get fewer "Take a meeting" calls.

**What did working this way teach me about using AI well?**
AI codes fast, but you need to validate it — you can't blindly trust AI agents, because they
hallucinate a lot. You need to make a proper plan with the AI first, so the implementation
takes fewer iterations and comes out clean and correct.
