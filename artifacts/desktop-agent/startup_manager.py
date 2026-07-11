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
REG_VALUE_NAME = "SAGE"


def get_startup_command() -> str:
    """Constructs the command to run SAGE silently."""
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we are running in the compiled release structure where SAGE.exe exists
    # SAGE.exe is located at '../../SAGE.exe' relative to desktop-agent/startup_manager.py
    sage_exe_path = os.path.abspath(os.path.join(agent_dir, "..", "..", "SAGE.exe"))
    if os.path.exists(sage_exe_path):
        return f'"{sage_exe_path}" --startup'
    
    # Check if launcher.py exists (dev workspace layout)
    launcher_py_path = os.path.abspath(os.path.join(agent_dir, "..", "..", "launcher", "launcher.py"))
    if os.path.exists(launcher_py_path):
        executable = sys.executable
        if "python.exe" in executable.lower():
            pythonw = executable.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                executable = pythonw
        return f'"{executable}" "{launcher_py_path}" --startup'

    # Fallback to desktop agent script
    executable = sys.executable
    if "python.exe" in executable.lower():
        pythonw = executable.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            executable = pythonw

    script_path = os.path.abspath(os.path.join(agent_dir, "main.py"))
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
    """Registers SAGE to run on Windows boot."""
    if not IS_WINDOWS:
        logger.warning("Startup registry only supported on Windows.")
        return False

    import winreg
    try:
        cmd = get_startup_command()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, cmd)
            # Clean up the legacy SAGEAgent key if it exists
            try:
                winreg.DeleteValue(key, "SAGEAgent")
            except Exception:
                pass
        logger.info("Auto-start registered in Windows Registry.")
        return True
    except Exception as e:
        logger.error(f"Error enabling startup: {e}")
        return False


def disable_startup() -> bool:
    """Unregisters SAGE from Windows boot registry."""
    if not IS_WINDOWS:
        return False

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, REG_VALUE_NAME)
            except FileNotFoundError:
                pass
            try:
                winreg.DeleteValue(key, "SAGEAgent")
            except FileNotFoundError:
                pass
        logger.info("Auto-start unregistered from Windows Registry.")
        return True
    except Exception as e:
        logger.error(f"Error disabling startup: {e}")
        return False


def create_desktop_shortcut() -> bool:
    """Create a Windows Desktop shortcut pointing to the SAGE executable."""
    if not IS_WINDOWS:
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
            
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        sage_exe_path = os.path.abspath(os.path.join(agent_dir, "..", "..", "SAGE.exe"))
        
        if os.path.exists(sage_exe_path):
            target_path = sage_exe_path
            working_dir = os.path.dirname(sage_exe_path)
            arguments = ""
        else:
            launcher_py_path = os.path.abspath(os.path.join(agent_dir, "..", "..", "launcher", "launcher.py"))
            if os.path.exists(launcher_py_path):
                executable = sys.executable
                if "python.exe" in executable.lower():
                    pythonw = executable.lower().replace("python.exe", "pythonw.exe")
                    if os.path.exists(pythonw):
                        executable = pythonw
                target_path = executable
                working_dir = os.path.dirname(launcher_py_path)
                arguments = f'"{launcher_py_path}"'
            else:
                return False
                
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
