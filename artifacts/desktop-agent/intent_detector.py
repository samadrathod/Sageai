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

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Intent:
    intent: str
    target: Optional[str] = None
    extra: dict = field(default_factory=dict)
    raw: str = ""
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Application aliases: map common spoken names to executable targets.
# Extend this dict for new apps — it is the only place app names are defined.
# ---------------------------------------------------------------------------
APP_ALIASES: dict[str, str] = {
    # Editors / IDEs
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "code": "code",
    "sublime": "subl",
    "sublime text": "subl",
    "atom": "atom",
    "notepad": "notepad",
    "notepad++": "notepad++",
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "safari": "safari",
    "brave": "brave-browser",
    # Media
    "spotify": "spotify",
    "vlc": "vlc",
    # Terminals
    "terminal": "x-terminal-emulator",
    "cmd": "cmd",
    "powershell": "powershell",
    "bash": "bash",
    # System
    "file explorer": "explorer",
    "explorer": "explorer",
    "finder": "open -a Finder",
    "calculator": "calculator",
    "calendar": "gnome-calendar",
    "settings": "gnome-control-center",
    "task manager": "taskmgr",
}

# ---------------------------------------------------------------------------
# Patterns — ordered from most-specific to least-specific.
# Each entry: (compiled_regex, intent_name, target_group)
# target_group is the regex group index (1-based) that holds the target string.
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[re.Pattern, str, int | None]] = [
    # open_application
    (re.compile(r"(?:open|launch|start|run)\s+(.+)", re.I), "open_application", 1),
    # search_files
    (re.compile(r"(?:search|find|locate)\s+(?:file|files|folder)?\s*(?:named|called|for)?\s+(.+)", re.I), "search_files", 1),
    (re.compile(r"(?:search|find)\s+(.+)\s+(?:in|inside|on)\s+(.+)", re.I), "search_files", 1),
    # create_folder
    (re.compile(r"(?:create|make|mkdir)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called|named)?\s+(.+)", re.I), "create_folder", 1),
    (re.compile(r"(?:create|make)\s+(?:a\s+)?(?:new\s+)?directory\s+(?:called|named)?\s+(.+)", re.I), "create_folder", 1),
    # create_file
    (re.compile(r"(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called|named)?\s+(.+)", re.I), "create_file", 1),
    # rename
    (re.compile(r"rename\s+(.+?)\s+to\s+(.+)", re.I), "rename", 1),
    # delete
    (re.compile(r"(?:delete|remove|trash)\s+(.+)", re.I), "delete", 1),
    # open_path / open_folder
    (re.compile(r"(?:open|go to|navigate to)\s+(?:the\s+)?(?:folder|directory|path)\s+(.+)", re.I), "open_path", 1),
    (re.compile(r"(?:open|show)\s+(.+?)\s+(?:folder|directory)", re.I), "open_path", 1),
    # run_command (explicit)
    (re.compile(r"(?:run|execute|cmd)\s+command\s+(.+)", re.I), "run_command", 1),
    # list_directory
    (re.compile(r"(?:list|show|ls)\s+(?:files?\s+in|contents? of|directory)?\s*(.+)", re.I), "list_directory", 1),
    # system_info
    (re.compile(r"(?:show|get|what(?:'s| is))\s+(?:system|cpu|memory|ram|disk)\s+(?:info|usage|status)?", re.I), "system_info", None),
    # kill_process
    (re.compile(r"(?:kill|stop|terminate)\s+(?:process\s+|app\s+)?(.+)", re.I), "kill_process", 1),
]


def detect(message: str) -> Intent | None:
    """
    Parse a user message and return a structured Intent, or None if
    the message does not look like a desktop command.
    """
    msg = message.strip()

    for pattern, intent_name, group_idx in _PATTERNS:
        m = pattern.match(msg)
        if not m:
            continue

        target: str | None = None
        extra: dict = {}

        if group_idx is not None:
            target = m.group(group_idx).strip().strip("'\"")

        # For open_application, resolve to the canonical executable
        if intent_name == "open_application" and target:
            target_lower = target.lower()
            resolved = None
            # Exact alias match first
            if target_lower in APP_ALIASES:
                resolved = APP_ALIASES[target_lower]
            else:
                # Partial match (e.g. "vs code 1.80" → "vs code")
                for alias, exe in APP_ALIASES.items():
                    if alias in target_lower:
                        resolved = exe
                        break
            extra["display_name"] = target
            target = resolved or target_lower

        # rename has a second group (new name)
        if intent_name == "rename" and len(m.groups()) >= 2:
            extra["new_name"] = m.group(2).strip().strip("'\"")

        return Intent(
            intent=intent_name,
            target=target,
            extra=extra,
            raw=msg,
            confidence=0.9,
        )

    return None
