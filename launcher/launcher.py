"""
launcher.py — Main production entry point for SAGE Desktop Assistant.
"""

from __future__ import annotations
import os
import sys
import io

# Redirect stdout and stderr to devnull in windowless mode to prevent crashes from library prints and fileno() lookups
if getattr(sys, "frozen", False):
    try:
        base_dir = os.path.dirname(sys.executable)
        sys.stdout = open(os.path.join(base_dir, "launcher_output.log"), "a", encoding="utf-8", buffering=1)
        sys.stderr = sys.stdout
    except Exception as e:
        try:
            with open(os.path.expandvars(r"%TEMP%\sage_log_err.txt"), "w") as f:
                f.write(f"Failed to open launcher_output.log: {e}\n")
        except Exception:
            pass
import time
import logging
import threading
import requests
import webview
from PIL import Image, ImageDraw
import pystray

# Ensure launcher directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_manager
import service_manager
import watchdog
import startup_manager

# Configure logging
log_dir = os.path.join(service_manager.get_base_dir(), "logs")
os.makedirs(log_dir, exist_ok=True)

handlers = [logging.FileHandler(os.path.join(log_dir, "launcher.log"), encoding="utf-8")]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers
)
logger = logging.getLogger("sage-launcher")

# Global window reference
window: webview.Window | None = None
tray_icon: pystray.Icon | None = None


def create_tray_image(color_state: str) -> Image.Image:
    """Generate a high-tech digital 'S' icon dynamically with PIL."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)
    
    # Map status to cyber glow outline
    if color_state == "GREEN":
        outline_color = (0, 255, 128, 255)  # Cyber cyan-green
    elif color_state == "YELLOW":
        outline_color = (255, 204, 0, 255)  # Cyber yellow-gold
    else:
        outline_color = (255, 50, 50, 255)   # Cyber crimson-red
        
    # Slate background with status border
    dc.ellipse([4, 4, 60, 60], fill=(15, 23, 42, 255), outline=outline_color, width=4)
    # Cyberspace S logo lines
    dc.line([(22, 20), (42, 20)], fill=outline_color, width=5)
    dc.line([(22, 20), (22, 32)], fill=outline_color, width=5)
    dc.line([(22, 32), (42, 32)], fill=outline_color, width=5)
    dc.line([(42, 32), (42, 44)], fill=outline_color, width=5)
    dc.line([(22, 44), (42, 44)], fill=outline_color, width=5)
    return img


def on_closing() -> bool:
    """Intercept the close event of the webview to hide it to tray instead."""
    if window:
        window.hide()
    # Return False to cancel the window destruction
    return False


def open_dashboard_action(icon, item):
    """Restore and show the dashboard window."""
    if window:
        window.show()


def toggle_voice_action(icon, item):
    """Toggle voice assistant loop in a background thread."""
    def _run():
        try:
            r = requests.get("http://127.0.0.1:7700/settings", timeout=2.0)
            if r.status_code == 200:
                curr = r.json().get("voice_enabled", True)
                requests.post("http://127.0.0.1:7700/settings/voice", json={"enabled": not curr}, timeout=2.0)
        except Exception as e:
            logger.error(f"Failed to toggle voice state: {e}")
    threading.Thread(target=_run, daemon=True).start()


def restart_services_action(icon, item):
    """Trigger clean shutdown and boot of backend services."""
    def _run():
        logger.info("Force-restarting SAGE services...")
        service_manager.stop_all_services()
        time.sleep(1.0)
        service_manager.start_express_server()
        service_manager.start_desktop_agent()
    threading.Thread(target=_run, daemon=True).start()


def open_logs_action(icon, item):
    """Open logs directory."""
    log_path = os.path.abspath(os.path.join(service_manager.get_base_dir(), "logs"))
    os.makedirs(log_path, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(log_path)
    else:
        subprocess.Popen(["xdg-open", log_path])


def toggle_startup_action(icon, item):
    """Toggle windows boot startup setting."""
    enabled = startup_manager.is_startup_enabled()
    if enabled:
        startup_manager.disable_startup()
        logger.info("SAGE boot startup disabled.")
    else:
        exec_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
        startup_manager.enable_startup(exec_path)
        logger.info(f"SAGE boot startup enabled for path: {exec_path}")


def exit_action(icon, item):
    """Tear down all services, stop threads, and terminate launcher."""
    logger.info("Tearing down SAGE processes and threads.")
    watchdog.stop_watchdog()
    service_manager.stop_all_services()
    icon.stop()
    os._exit(0)


def state_changed_listener(service: str, status: str):
    """Update tray icon image dynamically when state changes."""
    global tray_icon
    if tray_icon:
        current_status = state_manager.get_overall_status()
        logger.info(f"Tray status update -> {current_status} (trigger: {service}={status})")
        tray_icon.icon = create_tray_image(current_status)


def run_tray():
    """Build and run the system tray icon loop."""
    global tray_icon
    
    # State-changed hook to update tray colors
    state_manager.register_listener(state_changed_listener)
    
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", open_dashboard_action, default=True),
        pystray.MenuItem("Toggle Voice", toggle_voice_action),
        pystray.MenuItem("Restart Services", restart_services_action),
        pystray.MenuItem("Open Logs", open_logs_action),
        pystray.MenuItem("Start on Boot", toggle_startup_action, checked=lambda item: startup_manager.is_startup_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit SAGE", exit_action)
    )
    
    initial_status = state_manager.get_overall_status()
    tray_icon = pystray.Icon("sage-launcher", create_tray_image(initial_status), "SAGE Assistant", menu)
    tray_icon.run_detached()


def main():
    global window
    
    # Hide the console window immediately on Windows if running as a frozen binary
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
            
    # 1. Prevent duplicate instances
    if not startup_manager.prevent_duplicate_instance():
        # Duplicate detected, show a messagebox and exit
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SAGE Error", "Another instance of SAGE is already running.")
        sys.exit(1)
        
    logger.info("Initializing SAGE Launcher...")
    
    # Create Windows desktop shortcut if on Windows
    if sys.platform == "win32":
        try:
            startup_manager.create_desktop_shortcut()
        except Exception as e:
            logger.error(f"Could not create desktop shortcut: {e}")
            
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_WRITE
            )
            try:
                winreg.DeleteValue(key, "SAGEAgent")
                logger.info("Legacy SAGEAgent registry entry cleaned up.")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to cleanup legacy registry: {e}")
    
    # 2. Boot Express and Python Agent services
    service_manager.start_express_server()
    service_manager.start_desktop_agent()
    
    # 3. Start Watchdog Thread
    watchdog.start_watchdog()
    
    # 4. Start Tray Icon in a detached background thread
    run_tray()
    
    # Check if launcher was started silently on system boot
    is_startup_mode = "--startup" in sys.argv
    
    # 5. Initialize native webview window (Edge HTML/JS/CSS shell)
    window = webview.create_window(
        title="SAGE — Personal Assistant",
        url="http://127.0.0.1:5000",
        width=1100,
        height=750,
        resizable=True,
        min_size=(800, 600),
        hidden=is_startup_mode
    )
    
    # Register window hide interceptor
    window.events.closing += on_closing
    
    # Start WebView loop (this blocks the main thread on Windows)
    webview.start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        try:
            # Try to write to launcher_crash.txt in the base directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            crash_file = os.path.join(base_dir, "launcher_crash.txt")
            with open(crash_file, "w") as f:
                f.write(f"Uncaught Exception: {e}\n")
                traceback.print_exc(file=f)
        except Exception:
            # Fallback to local folder if base_dir is read-only (e.g. temporary _MEIPASS)
            with open("launcher_crash.txt", "w") as f:
                f.write(f"Uncaught Exception: {e}\n")
                traceback.print_exc(file=f)
