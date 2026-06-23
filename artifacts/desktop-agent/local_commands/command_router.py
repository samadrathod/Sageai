"""
command_router.py — Routes intents to registered command handlers and manages confirmations.
"""

from __future__ import annotations
import traceback
from typing import Any

from local_commands.intent_matcher import Intent
from local_commands.command_registry import get_handler
from local_commands.confirmation_manager import requires_confirmation, get_confirm_description


def route_command(intent: Intent, confirmed: bool = False) -> dict[str, Any]:
    """
    Route a local command intent to its handler.
    If the command is destructive and confirmed=False, returns a confirmation request.
    """
    base_response = {
        "handled": True,
        "intent": intent.intent,
        "response": "",
        "requires_confirm": False,
        "confirm_description": "",
    }

    # 1. Enforce confirmation gate for destructive intents
    if requires_confirmation(intent.intent) and not confirmed:
        confirm_desc = get_confirm_description(intent.intent, intent.target, intent.extra)
        base_response["requires_confirm"] = True
        base_response["confirm_description"] = confirm_desc
        base_response["response"] = confirm_desc
        return base_response

    # 2. Retrieve handler and execute
    handler = get_handler(intent.intent)
    if not handler:
        base_response["handled"] = False
        base_response["response"] = f"No handler registered for intent: {intent.intent}"
        return base_response

    try:
        response_str = handler(intent.target, intent.extra)
        base_response["response"] = response_str
    except (FileNotFoundError, NotADirectoryError, FileExistsError, ProcessLookupError) as e:
        base_response["response"] = f"⚠ {e}"
    except RuntimeError as e:
        base_response["response"] = f"⚠ {e}"
    except Exception:
        base_response["response"] = f"Unexpected execution error:\n{traceback.format_exc()}"

    return base_response
