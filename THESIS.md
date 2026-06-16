# Investment Thesis

> Everything in this pipeline — what we collect, how we score, what we recommend —
> flows from this thesis. It is deliberately **narrow** so the score means something.
> A thesis of "good companies" produces a meaningless score (see the assessment's
> anti-patterns). This one does not.

## The thesis (one sentence)

> **We back dev-tools and infrastructure startups led by a technical founding team,
> with an open-source wedge and early _organic_ traction (attention they earned, not
> attention they bought).**

## Why this thesis (and why now)

- **Sourceable from public, free signals.** A technical, open-source, organically-growing
  company leaves a public trail: a "Show HN" launch, a GitHub repo with stars and commit
  activity, a founder's GitHub profile. We can verify the thesis from data anyone can see —
  no paid databases, no scraping behind logins.
- **Defensible.** Each thesis word maps to a measurable signal (table below). That makes the
  score reproducible and auditable, not a vibe.
- **Held consistently.** A company that scores well on traction but has no public repo and no
  technical founder signal is *off-thesis* and should score low even if it's "interesting."

## What each thesis word means as a measurable signal

| Thesis word | What we look for | Where it comes from |
|---|---|---|
| **Dev-tools / infra** | Topic match; the product is software developers/operators use | The topic query + HN description |
| **Technical founding team** | Founder has a real GitHub presence (repos, followers, bio/company) | GitHub user API on the repo owner |
| **Open-source wedge** | A public repo exists and has traction (stars) | GitHub repo API |
| **Organic traction** | Earned attention: HN points/comments, GitHub stars | HN Algolia API + GitHub repo API |
| **Why now** | Qualitative — requires judgment | Claude (or flagged as "not assessed" offline) |

## The scoring rubric (0–100)

The score is **computed in code** from the signals above — see `pipeline/scoring.py`. It is
fully reproducible: same inputs always give the same score. The four components and their
maximum weights:

| Component | Max | What drives it |
|---|---:|---|
| **Technical depth** | 30 | Public repo found + primary language + founder GitHub profile |
| **Open-source wedge** | 25 | Public repo exists + star count |
| **Organic traction** | 25 | HN points + HN comments |
| **Market / why-now** | 20 | Qualitative judgement (Claude 0–1 → 0–20; offline = neutral, flagged) |

Three of the four components are 100% deterministic from public data. Only **Market / why-now**
needs judgement, and when we can't get it (no LLM key) we say so rather than faking a number.

## The recommendation thresholds

| Total score | Call |
|---|---|
| **≥ 68** | **Take a meeting** |
| **48–67** | **Watch** |
| **< 48** | **Pass** |

**Data-quality override:** if we could **not** find a public GitHub repo **and** HN traction is
weak (< 50 points), the company is off-thesis / unverifiable, so the call is capped at **Pass**
regardless of score, with the reason stated in the memo. This is how we stay "robust to bad or
missing data" — missing signal lowers conviction, it does not get hallucinated away.

## What this thesis deliberately ignores

- Consumer apps, vertical SaaS, hardware, and "AI wrapper" products with no technical moat —
  they will score low here *by design*, not by accident.
- Paid/ad-driven growth — we have no signal for it and don't want it; we reward organic attention.
