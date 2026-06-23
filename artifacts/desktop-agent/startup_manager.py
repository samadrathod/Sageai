"""
startup_manager.py — Manages auto-start on Windows boot via the Registry.
"""

from __future__ import annotations

import os
import sys
import platform
import logging

logger = logging.getLogger("sage-agent")

IS_WINDOWS = platform.system() == "Windows"
REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "SAGEAgent"


def get_startup_command() -> str:
    """Constructs the command to run SAGE Desktop Agent silently."""
    executable = sys.executable
    # Use pythonw.exe if available so it runs without popping up a cmd window
    if "python.exe" in executable.lower():
        pythonw = executable.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            executable = pythonw

    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
    return f'"{executable}" "{script_path}"'


def is_startup_enabled() -> bool:
    """Checks if SAGE is registered in Windows startup registry."""
    if not IS_WINDOWS:
        return False

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
            # Match current command to verify it's valid
            expected = get_startup_command()
            return value == expected
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking startup registry: {e}")
        return False


def enable_startup() -> bool:
    """Registers SAGE Desktop Agent to run on Windows boot."""
    if not IS_WINDOWS:
        logger.warning("Startup registry only supported on Windows.")
        return False

    import winreg
    try:
        cmd = get_startup_command()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, cmd)
        logger.info("Auto-start registered in Windows Registry.")
        return True
    except Exception as e:
        logger.error(f"Error enabling startup: {e}")
        return False


def disable_startup() -> bool:
    """Unregisters SAGE Desktop Agent from Windows boot registry."""
    if not IS_WINDOWS:
        return False

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, REG_VALUE_NAME)
        logger.info("Auto-start unregistered from Windows Registry.")
        return True
    except FileNotFoundError:
        # Already disabled
        return True
    except Exception as e:
        logger.error(f"Error disabling startup: {e}")
        return False
