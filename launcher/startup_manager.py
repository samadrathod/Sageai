"""
startup_manager.py — Manages Windows boot startup registry keys and instance singletons.
"""

from __future__ import annotations
import os
import sys
import socket
from typing import Optional

_lock_socket: Optional[socket.socket] = None


def prevent_duplicate_instance(port: int = 7705) -> bool:
    """
    Bind to a specific local port. If it fails, another instance is already
    running, preventing duplicates.
    """
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", port))
        # Keep the socket open for the lifetime of the application
        return True
    except socket.error:
        return False


def is_windows() -> bool:
    """Check if the operating system is Windows."""
    return sys.platform == "win32"


def is_startup_enabled() -> bool:
    """Check if SAGE is registered to start on Windows boot."""
    if not is_windows():
        return False
        
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "SAGE")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_startup(executable_path: str) -> bool:
    """Add a registry entry to run SAGE on Windows boot."""
    if not is_windows():
        return False
        
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE
        )
        # Wrap path in quotes to handle spaces correctly
        winreg.SetValueEx(key, "SAGE", 0, winreg.REG_SZ, f'"{executable_path}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable_startup() -> bool:
    """Remove the registry entry for SAGE startup."""
    if not is_windows():
        return False
        
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE
        )
        winreg.DeleteValue(key, "SAGE")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False
