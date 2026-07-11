"""
startup_manager.py — Manages Windows boot startup registry keys and instance singletons.
"""

from __future__ import annotations
import os
import sys
import socket
from typing import Optional

_mutex_handle = None


def prevent_duplicate_instance() -> bool:
    """
    Use a Windows named mutex for single-instance detection.
    
    Unlike the previous socket-based approach (binding to port 7705), a named
    mutex is automatically released by the OS when the owning process exits —
    even if it crashes hard. This eliminates false-positive "already running"
    errors that occurred when the previous instance died without cleanly
    releasing the socket.
    
    Falls back to a socket-based approach on non-Windows platforms.
    """
    global _mutex_handle
    
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        
        # Create a named mutex — if it already exists, another instance owns it
        _mutex_handle = kernel32.CreateMutexW(None, False, "Global\\SAGE_LAUNCHER_MUTEX")
        last_error = kernel32.GetLastError()
        
        if last_error == ERROR_ALREADY_EXISTS:
            return False
        return True
    else:
        # Non-Windows fallback: use socket binding
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 7705))
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
        # Wrap path in quotes to handle spaces correctly, and append --startup
        cmd = f'"{executable_path}" --startup'
        winreg.SetValueEx(key, "SAGE", 0, winreg.REG_SZ, cmd)
        
        # Clean up the legacy SAGEAgent key if it exists
        try:
            winreg.DeleteValue(key, "SAGEAgent")
        except Exception:
            pass
            
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
        try:
            winreg.DeleteValue(key, "SAGE")
        except FileNotFoundError:
            pass
            
        try:
            winreg.DeleteValue(key, "SAGEAgent")
        except FileNotFoundError:
            pass
            
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def create_desktop_shortcut() -> bool:
    """Create a Windows Desktop shortcut pointing to the SAGE executable."""
    if not is_windows():
        return False
        
    import subprocess
    import winreg
    try:
        # Query active Desktop path from Registry
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            val, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            desktop_path = os.path.abspath(os.path.expandvars(str(val)))
        except Exception:
            # Fallback
            user_profile = os.environ.get("USERPROFILE", "")
            desktop_paths = [
                os.path.join(user_profile, "OneDrive", "Desktop"),
                os.path.join(user_profile, "Desktop")
            ]
            desktop_path = None
            for p in desktop_paths:
                if os.path.exists(p):
                    desktop_path = p
                    break
            if not desktop_path:
                desktop_path = os.path.expanduser("~/Desktop")
            
        # Determine the target path and working directory
        if getattr(sys, "frozen", False):
            target_path = sys.executable
            working_dir = os.path.dirname(target_path)
            arguments = ""
        else:
            # Point to launcher.py via pythonw.exe in dev
            launcher_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "launcher.py"))
            executable = sys.executable
            if "python.exe" in executable.lower():
                pythonw = executable.lower().replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw):
                    executable = pythonw
            target_path = executable
            working_dir = os.path.dirname(launcher_py_path)
            arguments = f'"{launcher_py_path}"'
            
        shortcut_path = os.path.join(desktop_path, "SAGE.lnk")
        
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target_path}"; '
            f'$s.WorkingDirectory = "{working_dir}"; '
            f'$s.Arguments = "{arguments}"; '
            f'$s.IconLocation = "{target_path},0"; '
            f'$s.Save()'
        )
        
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True,
            text=True
        )
        return True
    except Exception:
        return False
