"""
tool_router.py — Routes detected intents to the correct tool module.

This is the central safety layer. Every intent passes through here before
any OS-level call is made. The router:

  1. Validates the intent fields.
  2. Decides whether confirmation is required (destructive actions).
  3. Delegates to the correct tool function.
  4. Formats a human-readable response string.

Response schema:
  {
    "handled": bool,             # True if this was a desktop command
    "intent": str,               # detected intent name
    "response": str,             # human-readable result or error
    "requires_confirm": bool,    # True if the frontend must confirm first
    "confirm_description": str,  # What the user will be confirming
  }
"""

from __future__ import annotations

import traceback
from typing import Any

from intent_detector import Intent
import app_launcher
import file_manager
import system_manager


# Intents that must be confirmed by the user before execution.
DESTRUCTIVE_INTENTS = {"delete", "rename", "kill_process", "run_command"}


def _fmt_list_dir(result: dict) -> str:
    entries = result["entries"]
    if not entries:
        return f"Directory is empty: {result['path']}"
    lines = [f"Contents of {result['path']}:"]
    for e in entries:
        icon = "📁" if e["type"] == "dir" else "📄"
        size = f"  ({e['size']:,} bytes)" if e["size"] is not None else ""
        lines.append(f"  {icon} {e['name']}{size}")
    return "\n".join(lines)


def _fmt_search(matches: list[str], pattern: str) -> str:
    if not matches:
        return f"No files matching '{pattern}' were found."
    lines = [f"Found {len(matches)} result(s) for '{pattern}':"]
    for m in matches:
        lines.append(f"  • {m}")
    return "\n".join(lines)


def _fmt_sysinfo(info: dict) -> str:
    m = info["memory"]
    d = info["disk"]
    c = info["cpu"]
    return (
        f"System: {info['platform']} {info['platform_version'][:40]}\n"
        f"CPU: {c['count']} cores @ {c['usage_percent']}% usage\n"
        f"RAM: {m['used_gb']} GB / {m['total_gb']} GB ({m['percent']}% used)\n"
        f"Disk: {d['used_gb']} GB / {d['total_gb']} GB ({d['percent']}% used)"
    )


from local_commands.command_router import route_command


def route(intent: Intent, confirmed: bool = False) -> dict[str, Any]:
    """
    Route an intent to the appropriate tool and return a response dict.
    If the intent is destructive and confirmed=False, return requires_confirm.
    """
    return route_command(intent, confirmed)

