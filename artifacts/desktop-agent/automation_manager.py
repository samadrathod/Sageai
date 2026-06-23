"""
automation_manager.py — Routine execution engine.
"""

from __future__ import annotations

import os
import json
import time
import threading
import logging
import platform

import app_launcher

logger = logging.getLogger("sage-agent")

ROUTINES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "routines.json")


def load_routines() -> dict:
    if not os.path.exists(ROUTINES_CONFIG_PATH):
        logger.warning("routines.json not found, returning empty configuration.")
        return {}
    try:
        with open(ROUTINES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading routines.json: {e}")
        return {}


def toggle_focus_assist(enabled: bool) -> bool:
    """Toggles Focus Assist / Do Not Disturb via Windows Registry."""
    if platform.system() != "Windows":
        logger.warning("Focus Assist toggle only supported on Windows.")
        return False

    import winreg
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"
    value_name = "NOC_GLOBAL_SETTING_TOASTS_ENABLED"
    # Toasts Enabled: 0 = Suppress / Do Not Disturb, 1 = Enable / Normal
    value = 0 if enabled else 1

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
        logger.info(f"Windows Focus Assist {'enabled (notifications muted)' if enabled else 'disabled'}.")
        return True
    except Exception as e:
        logger.error(f"Failed to toggle Windows Focus Assist: {e}")
        return False


def run_timer(duration_seconds: int, name: str):
    """Background timer thread that plays chimes and speaks on completion."""
    logger.info(f"Timer started: {name} for {duration_seconds}s.")
    time.sleep(duration_seconds)
    logger.info(f"Timer complete: {name}.")
    
    # Alert chimes
    import winsound
    try:
        for _ in range(3):
            winsound.Beep(1200, 150)
            time.sleep(0.1)
    except Exception:
        pass

    # Speak alert
    from voice_assistant import speak_text
    speak_text(f"Attention, your {name} timer of {duration_seconds // 60} minutes is complete. Time to take a break!")


def start_study_timer(duration_minutes: int):
    timer_thread = threading.Thread(
        target=run_timer,
        args=(duration_minutes * 60, "Study Mode"),
        daemon=True
    )
    timer_thread.start()


def execute_step(step: dict):
    """Executes a single routine step action."""
    action = step.get("action")
    logger.info(f"Executing automation step: {action}")

    if action == "speak":
        from voice_assistant import speak_text
        speak_text(step["text"])

    elif action == "launch_app":
        try:
            app_launcher.launch_app(step["target"])
        except Exception as e:
            logger.error(f"launch_app failed in step: {e}")

    elif action == "open_path":
        try:
            app_launcher.open_path(step["target"])
        except Exception as e:
            logger.error(f"open_path failed in step: {e}")

    elif action == "focus_assist":
        toggle_focus_assist(step.get("enabled", True))

    elif action == "start_timer":
        duration = step.get("duration_minutes", 25)
        start_study_timer(duration)


def execute_routine(routine_key: str) -> str:
    """Executes all steps in a routine sequentially in a separate thread."""
    routines = load_routines()
    routine = routines.get(routine_key)
    if not routine:
        return f"Routine '{routine_key}' not found."

    def _run():
        for step in routine.get("steps", []):
            execute_step(step)
            # Give a small pause between steps for natural transitions
            time.sleep(1.0)

    # Run in thread to prevent freezing the caller (voice or fastapi server)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return f"Triggered routine: {routine.get('name', routine_key)}."


def find_matched_routine(user_text: str) -> str | None:
    """Scans user text to see if it matches any routine trigger phrase."""
    text_clean = user_text.lower().strip().strip(",.!? ")
    routines = load_routines()
    for key, data in routines.items():
        for phrase in data.get("trigger_phrases", []):
            if phrase in text_clean:
                return key
    return None
