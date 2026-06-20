"""
system_manager.py — Safe system-level operations for the SAGE Desktop Agent.

Only a curated allowlist of operations is permitted. Any command outside
the allowlist is rejected before execution — no subprocess shell=True,
no eval, no dynamic code execution.

Permitted operations:
  - System info (CPU, memory, disk, network, platform)
  - Process listing
  - Kill a named process by name (requires confirmation)
  - Volume control (platform-specific, best-effort)
"""

from __future__ import annotations

import os
import platform
import signal
import subprocess
import sys
from typing import Any

import psutil


OS = platform.system()


# ---------------------------------------------------------------------------
# Read-only system info
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, Any]:
    """Return a snapshot of system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "python": sys.version,
        "cpu": {
            "count": psutil.cpu_count(logical=True),
            "usage_percent": cpu_percent,
        },
        "memory": {
            "total_gb": round(mem.total / 1e9, 2),
            "used_gb": round(mem.used / 1e9, 2),
            "available_gb": round(mem.available / 1e9, 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1e9, 2),
            "used_gb": round(disk.used / 1e9, 2),
            "free_gb": round(disk.free / 1e9, 2),
            "percent": disk.percent,
        },
    }


def list_processes(limit: int = 20) -> list[dict]:
    """Return the top processes sorted by CPU usage."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = proc.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p.get("cpu_percent") or 0, reverse=True)
    return procs[:limit]


# ---------------------------------------------------------------------------
# Write/destructive operations (all flagged requires_confirm in tool_router)
# ---------------------------------------------------------------------------

def kill_process(name: str) -> str:
    """
    Kill all processes whose name matches (case-insensitive).
    DESTRUCTIVE — must be confirmed.
    """
    killed: list[int] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name.lower():
                proc.kill()
                killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not killed:
        raise ProcessLookupError(f"No process named '{name}' found.")
    return f"Killed process '{name}' (PID: {', '.join(map(str, killed))})."


# ---------------------------------------------------------------------------
# Volume control (best-effort, platform-specific)
# ---------------------------------------------------------------------------

def _set_volume_windows(level: int) -> None:
    script = (
        f"$wshShell = New-Object -ComObject WScript.Shell;"
        f"1..50 | ForEach-Object {{ $wshShell.SendKeys([char]174) }};"
        # Mute then set to level — simplified via nircmd if available
    )
    # Prefer nircmd if installed
    if subprocess.call(["where", "nircmd"], capture_output=True).returncode == 0:
        subprocess.run(["nircmd", "setsysvolume", str(int(level / 100 * 65535))], check=True)
    else:
        raise NotImplementedError("Install nircmd for Windows volume control.")


def _set_volume_macos(level: int) -> None:
    subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)


def _set_volume_linux(level: int) -> None:
    subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%"], check=True)


def set_volume(level: int) -> str:
    """Set system volume 0–100. Best-effort across platforms."""
    level = max(0, min(100, level))
    if OS == "Windows":
        _set_volume_windows(level)
    elif OS == "Darwin":
        _set_volume_macos(level)
    else:
        _set_volume_linux(level)
    return f"Volume set to {level}%."
