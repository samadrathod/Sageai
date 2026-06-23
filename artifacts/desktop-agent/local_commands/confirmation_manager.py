"""
confirmation_manager.py — Enforces approval safety gate for destructive desktop actions.
"""

from __future__ import annotations
from typing import Any

# Intent names that must be explicitly confirmed by the user before running
DESTRUCTIVE_INTENTS = {
    "delete_file",
    "rename_file",
    "kill_process",
    "shutdown",
    "restart",
    "sleep"
}


def requires_confirmation(intent_name: str) -> bool:
    """Check if an intent requires user confirmation."""
    return intent_name in DESTRUCTIVE_INTENTS


def get_confirm_description(intent_name: str, target: str | None, extra: dict[str, Any] | None = None) -> str:
    """Get safety descriptions for the user confirmation prompt."""
    extra = extra or {}
    target_display = target or "unknown"
    
    descriptions = {
        "delete_file": f"Delete '{target_display}'? This cannot be undone.",
        "rename_file": f"Rename '{target_display}' to '{extra.get('new_name', '?')}'?",
        "kill_process": f"Kill all processes named '{target_display}'?",
        "shutdown": "Shut down the computer?",
        "restart": "Restart the computer?",
        "sleep": "Put the computer to sleep?",
    }
    return descriptions.get(intent_name, f"Execute '{intent_name}' command?")
