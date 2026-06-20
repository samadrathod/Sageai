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


def route(intent: Intent, confirmed: bool = False) -> dict[str, Any]:
    """
    Route an intent to the appropriate tool and return a response dict.
    If the intent is destructive and confirmed=False, return requires_confirm.
    """
    base_response = {
        "handled": True,
        "intent": intent.intent,
        "response": "",
        "requires_confirm": False,
        "confirm_description": "",
    }

    # -------------------------------------------------------------------
    # Destructive gate — ask for confirmation before anything irreversible
    # -------------------------------------------------------------------
    if intent.intent in DESTRUCTIVE_INTENTS and not confirmed:
        descriptions = {
            "delete": f"Delete '{intent.target}'? This cannot be undone.",
            "rename": f"Rename '{intent.target}' to '{intent.extra.get('new_name', '?')}'?",
            "kill_process": f"Kill all processes named '{intent.target}'?",
            "run_command": f"Execute command: {intent.target}?",
        }
        base_response["requires_confirm"] = True
        base_response["confirm_description"] = descriptions.get(intent.intent, f"Execute {intent.intent}?")
        base_response["response"] = base_response["confirm_description"]
        return base_response

    # -------------------------------------------------------------------
    # Safe execution with structured error handling
    # -------------------------------------------------------------------
    try:
        match intent.intent:

            case "open_application":
                display = intent.extra.get("display_name", intent.target or "")
                result = app_launcher.launch_app(intent.target or "", display)
                base_response["response"] = result

            case "open_path":
                result = app_launcher.open_path(intent.target or "~")
                base_response["response"] = result

            case "create_folder":
                result = file_manager.create_folder(intent.target or "")
                base_response["response"] = result

            case "create_file":
                result = file_manager.create_file(intent.target or "")
                base_response["response"] = result

            case "rename":
                result = file_manager.rename(
                    intent.target or "",
                    intent.extra.get("new_name", ""),
                )
                base_response["response"] = result

            case "delete":
                result = file_manager.delete(intent.target or "")
                base_response["response"] = result

            case "search_files":
                matches = file_manager.search_files(intent.target or "*")
                base_response["response"] = _fmt_search(matches, intent.target or "*")

            case "list_directory":
                info = file_manager.list_directory(intent.target or "~")
                base_response["response"] = _fmt_list_dir(info)

            case "system_info":
                info = system_manager.get_system_info()
                base_response["response"] = _fmt_sysinfo(info)

            case "kill_process":
                result = system_manager.kill_process(intent.target or "")
                base_response["response"] = result

            case _:
                base_response["handled"] = False
                base_response["response"] = f"Unknown intent: {intent.intent}"

    except (FileNotFoundError, NotADirectoryError, FileExistsError, ProcessLookupError) as e:
        base_response["response"] = f"⚠ {e}"

    except RuntimeError as e:
        base_response["response"] = f"⚠ {e}"

    except Exception:
        base_response["response"] = f"Unexpected error:\n{traceback.format_exc()}"

    return base_response
