"""
intent_detector.py — Lightweight rule-based intent parser.

Converts natural language user messages into structured intents without
requiring an external AI call. Pattern matching is fast, offline, and
deterministic — important for a local desktop agent.

Intent schema:
  {
    "intent": str,          # e.g. "open_application", "create_folder"
    "target": str | None,   # primary target (app name, path, filename)
    "extra": dict,          # any additional parsed fields
    "raw": str,             # original user message
    "confidence": float     # 0.0–1.0 match confidence
  }

Returns None if the message is not a desktop command.
"""

from __future__ import annotations

from local_commands.intent_matcher import Intent, match_intent


def detect(message: str) -> Intent | None:
    """
    Parse a user message and return a structured Intent, or None if
    the message does not look like a desktop command.
    """
    return match_intent(message)

