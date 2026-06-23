"""
command_registry.py — Command Registry pattern implementation mapping intents to handlers.
"""

from __future__ import annotations
from typing import Callable, Any

from local_commands.app_commands import handle_open_app, handle_close_app, handle_kill_process
from local_commands.file_commands import (
    handle_create_folder,
    handle_create_file,
    handle_rename_file,
    handle_move_file,
    handle_delete_file,
    handle_search_files,
    handle_open_folder
)
from local_commands.system_commands import (
    handle_system_info,
    handle_volume_control,
    handle_brightness_control,
    handle_wifi_toggle,
    handle_bluetooth_toggle,
    handle_shutdown,
    handle_restart,
    handle_sleep
)
from local_commands.memory_commands import (
    handle_remember,
    handle_recall,
    handle_forget,
    handle_forget_all
)
from local_commands.automation_commands import (
    handle_coding_setup,
    handle_study_mode,
    handle_gaming_mode,
    handle_global_news_briefing
)

# Registry dictionary mapping intent string names to their handler function
COMMAND_REGISTRY: dict[str, Callable[[Any, dict], str]] = {
    # Application Control
    "open_application": handle_open_app,
    "close_application": handle_close_app,
    "kill_process": handle_kill_process,

    # File Management
    "create_folder": handle_create_folder,
    "create_file": handle_create_file,
    "rename_file": handle_rename_file,
    "move_file": handle_move_file,
    "delete_file": handle_delete_file,
    "search_files": handle_search_files,
    "open_folder": handle_open_folder,

    # System Control
    "system_info": handle_system_info,
    "volume_control": handle_volume_control,
    "brightness_control": handle_brightness_control,
    "wifi_toggle": handle_wifi_toggle,
    "bluetooth_toggle": handle_bluetooth_toggle,
    "shutdown": handle_shutdown,
    "restart": handle_restart,
    "sleep": handle_sleep,

    # Automation Routines
    "coding_setup": handle_coding_setup,
    "study_mode": handle_study_mode,
    "gaming_mode": handle_gaming_mode,
    "global_news_briefing": handle_global_news_briefing,

    # Memory Commands
    "remember": handle_remember,
    "recall": handle_recall,
    "forget": handle_forget,
    "forget_all": handle_forget_all,
}


def get_handler(intent_name: str) -> Callable[[Any, dict], str] | None:
    """Retrieve the handler for a specific intent from the registry."""
    return COMMAND_REGISTRY.get(intent_name)
