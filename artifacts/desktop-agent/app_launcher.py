"""
app_launcher.py — Cross-platform application launcher.

Detects the current OS and calls the appropriate launch strategy.
Windows: uses `start` via cmd /c, with common app path fallbacks.
macOS:   uses `open -a` for GUI apps.
Linux:   uses $PATH lookup via subprocess.

The launcher is intentionally read-only with respect to the filesystem —
it cannot create, delete, or modify files. That is file_manager.py's job.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _windows_launch(target: str, display_name: str) -> str:
    """Attempt to launch an app on Windows using several strategies."""
    # Strategy 1: target is already a known command in PATH
    if shutil.which(target):
        subprocess.Popen([target], shell=False, close_fds=True)
        return f"Launched {display_name}."

    # Strategy 2: use `start` which handles registered Windows apps
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", target],
            shell=False,
            close_fds=True,
        )
        return f"Launched {display_name}."
    except FileNotFoundError:
        pass

    # Strategy 3: common Program Files locations
    candidates = [
        rf"C:\Program Files\{display_name}\{target}.exe",
        rf"C:\Program Files (x86)\{display_name}\{target}.exe",
        os.path.expandvars(rf"%LOCALAPPDATA%\Programs\{display_name}\{target}.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            subprocess.Popen([path], shell=False, close_fds=True)
            return f"Launched {display_name} from {path}."

    raise RuntimeError(
        f"Could not find '{display_name}' on this system. "
        "Make sure it is installed and in your PATH."
    )


def _macos_launch(target: str, display_name: str) -> str:
    if shutil.which(target):
        subprocess.Popen([target], close_fds=True)
        return f"Launched {display_name}."
    # Try `open -a <App Name>`
    try:
        subprocess.Popen(["open", "-a", display_name], close_fds=True)
        return f"Launched {display_name}."
    except Exception:
        pass
    raise RuntimeError(f"Could not launch '{display_name}' on macOS.")


def _linux_launch(target: str, display_name: str) -> str:
    if shutil.which(target):
        subprocess.Popen([target], close_fds=True)
        return f"Launched {display_name}."
    # Try xdg-open for generic mime handling
    try:
        subprocess.Popen(["xdg-open", target], close_fds=True)
        return f"Launched {display_name}."
    except Exception:
        pass
    raise RuntimeError(
        f"'{display_name}' not found. Install it or add it to PATH."
    )


def launch_app(target: str, display_name: str | None = None) -> str:
    """
    Launch an application by its executable name or alias.
    Returns a human-readable status string.
    Raises RuntimeError on failure (caller should catch and surface to user).
    """
    display = display_name or target
    if OS == "Windows":
        return _windows_launch(target, display)
    elif OS == "Darwin":
        return _macos_launch(target, display)
    else:
        return _linux_launch(target, display)


def open_path(path: str) -> str:
    """Open a file or directory in the system file manager / default app."""
    expanded = os.path.expanduser(os.path.expandvars(path))
    if not os.path.exists(expanded):
        raise FileNotFoundError(f"Path not found: {expanded}")

    if OS == "Windows":
        os.startfile(expanded)  # type: ignore[attr-defined]
    elif OS == "Darwin":
        subprocess.Popen(["open", expanded], close_fds=True)
    else:
        subprocess.Popen(["xdg-open", expanded], close_fds=True)

    kind = "folder" if os.path.isdir(expanded) else "file"
    return f"Opened {kind}: {expanded}"
