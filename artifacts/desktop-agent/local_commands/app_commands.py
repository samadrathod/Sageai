"""
app_commands.py — App execution and termination handlers.
"""

from __future__ import annotations
import psutil
import app_launcher
import system_manager


def handle_open_app(target: str, extra: dict) -> str:
    """Launch an application."""
    display = extra.get("display_name", target)
    return app_launcher.launch_app(target, display)


def handle_close_app(target: str, extra: dict) -> str:
    """Soft-close an application by terminating its processes cleanly."""
    killed = []
    display = extra.get("display_name", target)
    
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == target.lower():
                proc.terminate()
                killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not killed:
        return f"No running application processes named '{display}' were found."
    return f"Closed '{display}' (terminated PIDs: {', '.join(map(str, killed))})."


def handle_kill_process(target: str, extra: dict) -> str:
    """Forcefully kill a process."""
    return system_manager.kill_process(target)
