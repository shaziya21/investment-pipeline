"""Command-line entry point — wires the three stages together.

One command runs the whole thing:

    python -m pipeline.cli run --topic "developer tools"

Or run stages individually (they're replayable because each reads the previous
stage's committed JSON file):

    python -m pipeline.cli source  --topic "developer tools"
    python -m pipeline.cli analyze            # reads candidates.json
    python -m pipeline.cli memo               # reads analyses.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import analysis as analysis_stage
from . import memo as memo_stage
from . import sourcing
from .models import Analysis, Candidate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_FILE = DATA_DIR / "candidates.json"
ANALYSES_FILE = DATA_DIR / "analyses.json"
MEMOS_DIR = DATA_DIR / "memos"


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    print(f"  -> wrote {path.relative_to(DATA_DIR.parent)}")


# --- stage runners --------------------------------------------------------------
def run_source(topic: str, limit: int) -> list[Candidate]:
    candidates = sourcing.source_candidates(topic, limit=limit)
    _write_json(CANDIDATES_FILE, {
        "topic": topic,
        "count": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
    })
    return candidates


def run_analyze(use_llm: bool) -> list[Analysis]:
    if not CANDIDATES_FILE.exists():
        sys.exit("No candidates.json — run `source` first.")
    payload = json.loads(CANDIDATES_FILE.read_text())
    candidates = [Candidate.from_dict(d) for d in payload["candidates"]]
    print(f"[analyze] analysing {len(candidates)} candidates "
          f"({'LLM enabled' if use_llm else 'offline mode'}) ...")

    analyses: list[Analysis] = []
    for i, c in enumerate(candidates, 1):
        a = analysis_stage.analyze_candidate(c, use_llm=use_llm)
        analyses.append(a)
        print(f"  [{i}/{len(candidates)}] {c.name[:38]:38s} score {a.score.total:3d} -> {a.call}")

    # Sort best-first so the top of the file is the top of the funnel.
    analyses.sort(key=lambda a: a.score.total, reverse=True)
    _write_json(ANALYSES_FILE, {
        "count": len(analyses),
        "analyses": [a.to_dict() for a in analyses],
    })
    return analyses


def run_memo() -> None:
    if not ANALYSES_FILE.exists():
        sys.exit("No analyses.json — run `analyze` first.")
    payload = json.loads(ANALYSES_FILE.read_text())
    analyses = [Analysis.from_dict(d) for d in payload["analyses"]]
    MEMOS_DIR.mkdir(parents=True, exist_ok=True)

    index_lines = ["# Memo index\n", "Sorted best-first by score.\n"]
    for a in analyses:
        fname = memo_stage.memo_filename(a)
        (MEMOS_DIR / fname).write_text(memo_stage.render_memo(a))
        index_lines.append(f"- [{a.candidate.name}](./{fname}) — **{a.call}** ({a.score.total}/100)")
    (MEMOS_DIR / "INDEX.md").write_text("\n".join(index_lines) + "\n")
    print(f"[memo] wrote {len(analyses)} memos + INDEX.md to {MEMOS_DIR.relative_to(DATA_DIR.parent)}/")


# --- argument parsing -----------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="AI-augmented investment triage pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_src = sub.add_parser("source", help="Stage 1: collect candidates for a topic")
    p_src.add_argument("--topic", required=True, help='e.g. "developer tools"')
    p_src.add_argument("--limit", type=int, default=15, help="max candidates (default 15)")

    p_an = sub.add_parser("analyze", help="Stage 2: score + analyse candidates.json")
    p_an.add_argument("--offline", action="store_true",
                      help="skip the LLM and use the deterministic fallback")

    sub.add_parser("memo", help="Stage 3: render one memo per analysis")

    p_run = sub.add_parser("run", help="Run all three stages end-to-end")
    p_run.add_argument("--topic", required=True)
    p_run.add_argument("--limit", type=int, default=15)
    p_run.add_argument("--offline", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "source":
        run_source(args.topic, args.limit)
    elif args.command == "analyze":
        run_analyze(use_llm=not args.offline)
    elif args.command == "memo":
        run_memo()
    elif args.command == "run":
        run_source(args.topic, args.limit)
        run_analyze(use_llm=not args.offline)
        run_memo()


if __name__ == "__main__":
    main()
