# AI-Augmented Investment Pipeline

A triage layer for a seed-stage VC: point it at a topic, get one-page memos out the
other end, each ending in a clear call — **Pass / Watch / Take a meeting**.

It sources candidate startups from **Hacker News** + **GitHub**, scores them
**deterministically** against a stated thesis, and writes a memo per company with
**every claim traced to a source**.

> **Start here:** [`THESIS.md`](./THESIS.md) (what we back & how we score) ·
> [`DECISIONS.md`](./DECISIONS.md) (how it was built, with the bugs I hit) ·
> [`PROCESS.md`](./PROCESS.md) (how AI was used) ·
> [`data/memos/INDEX.md`](./data/memos/INDEX.md) (the committed example output).

## Run it (one command)

No dependencies needed for sourcing + scoring — only the Python standard library.

```bash
python3 -m pipeline.cli run --topic "Postgres" --limit 12
```

That runs all three stages and writes:
- `data/candidates.json` — sourced startups
- `data/analyses.json` — scores + narratives + calls
- `data/memos/*.md` — one memo per company, plus `INDEX.md` (ranked best-first)

The committed `data/` is an example run on **"Postgres"** — open
[`data/memos/INDEX.md`](./data/memos/INDEX.md) to read it without running anything.

### With Claude (optional — adds the market analysis)

The score works without an LLM. Add a key to get the **Market / why-now** section
and a real market judgement in the score:

```bash
pip install "anthropic>=0.40"
export ANTHROPIC_API_KEY=sk-ant-...        # see .env.example
python3 -m pipeline.cli run --topic "Postgres" --limit 12
```

Without a key it automatically falls back to a deterministic, signal-grounded
narrative and flags the market section as "not assessed" (it never fakes it).

### Run stages individually (they're replayable)

```bash
python3 -m pipeline.cli source  --topic "Postgres" --limit 12   # -> candidates.json
python3 -m pipeline.cli analyze --offline                       # -> analyses.json
python3 -m pipeline.cli memo                                    # -> data/memos/
```

### Tests

```bash
python3 -m unittest discover -s tests
```

## How it works

```
topic ──▶ [1 source] ─▶ candidates.json ──▶ [2 analyze] ─▶ analyses.json ──▶ [3 memo] ─▶ memos/*.md
          HN + GitHub                       score + narrative                 one page each
```

| Stage | File | What it does |
|---|---|---|
| 1. Source | `pipeline/sourcing.py` | HN "Show HN" launches (traction signal) enriched with GitHub repo + founder profile (technical-depth signal) |
| 2a. Score | `pipeline/scoring.py` | Deterministic 0–100 from public signals — reproducible & defensible |
| 2b. Analyze | `pipeline/analysis.py` | Narrative (team/product/market/risks) via Claude, or offline fallback |
| 3. Memo | `pipeline/memo.py` | One skimmable markdown page; call at top; every claim sourced |

The scoring rubric and thresholds live in `pipeline/config.py` and are explained in
[`THESIS.md`](./THESIS.md).

## What's deliberately *not* here

No database, no job queue, no vector store, no web frontend — the assessment says to
stop if you're building those. State is just committed JSON + markdown files.
