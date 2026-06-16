"""AI-augmented investment triage pipeline.

Three replayable stages:
  sourcing  -> candidates.json
  analysis  -> analyses.json   (deterministic score + LLM/offline narrative)
  memo      -> data/memos/*.md
"""

__version__ = "0.1.0"
