"""
main.py — SAGE Desktop Agent API server.

Runs locally on http://localhost:7700 on the user's machine.
Provides system tray control, background operation, and auto-start management.
"""

from __future__ import annotations

import logging
import sys
import os
import threading
import webbrowser
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageDraw
import pystray

from intent_detector import detect
from tool_router import route
import system_manager
import startup_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("sage-agent")

# Global state
voice_enabled = True

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SAGE Desktop Agent",
    description="Local desktop control API for the SAGE assistant.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # local-only binding — broad CORS is safe here
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ExecuteRequest(BaseModel):
    message: str
    confirmed: bool = False


class ExecuteResponse(BaseModel):
    handled: bool
    intent: str = ""
    response: str
    requires_confirm: bool = False
    confirm_description: str = ""


class SettingsUpdate(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "SAGE Desktop Agent v2.0"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(body: ExecuteRequest):
    """
    Parse the user message, detect intent, and execute (or request confirm).
    """
    logger.info(f"Execute request: '{body.message}' confirmed={body.confirmed}")

    intent = detect(body.message)

    if intent is None:
        # Not a desktop command — let SAGE handle it with Gemini
        return ExecuteResponse(
            handled=False,
            response="",
        )

    result = route(intent, confirmed=body.confirmed)
    logger.info(f"Intent={result['intent']} handled={result['handled']} confirm={result['requires_confirm']}")

    return ExecuteResponse(**result)


@app.get("/system/info")
async def system_info_endpoint():
    """Live CPU / memory / disk snapshot."""
    return system_manager.get_system_info()


@app.get("/processes")
async def processes_endpoint():
    """Running processes sorted by CPU usage."""
    return {"processes": system_manager.list_processes()}


@app.get("/settings")
async def get_settings():
    """Fetch current desktop agent settings."""
    return {
        "startup_enabled": startup_manager.is_startup_enabled(),
        "voice_enabled": voice_enabled,
    }


@app.post("/settings/startup")
async def update_startup(body: SettingsUpdate):
    """Toggle startup registry entry."""
    success = startup_manager.enable_startup() if body.enabled else startup_manager.disable_startup()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update startup setting")
    return {"status": "ok", "startup_enabled": startup_manager.is_startup_enabled()}


@app.post("/settings/voice")
async def update_voice(body: SettingsUpdate):
    """Toggle continuous voice listening loop."""
    global voice_enabled
    voice_enabled = body.enabled
    logger.info(f"Voice enabled updated via API: {voice_enabled}")
    return {"status": "ok", "voice_enabled": voice_enabled}


# ---------------------------------------------------------------------------
# System Tray Integration
# ---------------------------------------------------------------------------
def create_tray_image() -> Image.Image:
    """Generate a high-tech cyan 'S' icon dynamically with PIL."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)
    # Slate circle background with cyber-cyan border
    dc.ellipse([4, 4, 60, 60], fill=(15, 23, 42, 255), outline=(0, 255, 255, 255), width=4)
    # Draw digital 'S' in cyan
    dc.line([(22, 20), (42, 20)], fill=(0, 255, 255, 255), width=5)
    dc.line([(22, 20), (22, 32)], fill=(0, 255, 255, 255), width=5)
    dc.line([(22, 32), (42, 32)], fill=(0, 255, 255, 255), width=5)
    dc.line([(42, 32), (42, 44)], fill=(0, 255, 255, 255), width=5)
    dc.line([(22, 44), (42, 44)], fill=(0, 255, 255, 255), width=5)
    return img


def open_dashboard_action(icon, item):
    webbrowser.open("http://localhost:5173")


def toggle_voice_action(icon, item):
    global voice_enabled
    voice_enabled = not voice_enabled
    logger.info(f"Voice Assistant toggled: {voice_enabled}")


def toggle_startup_action(icon, item):
    enabled = startup_manager.is_startup_enabled()
    if enabled:
        startup_manager.disable_startup()
    else:
        startup_manager.enable_startup()


def exit_action(icon, item):
    logger.info("SAGE Desktop Agent shutting down...")
    icon.stop()
    os._exit(0)


def setup_system_tray():
    """Sets up and runs the system tray icon loop."""
    icon_image = create_tray_image()
    menu = pystray.Menu(
        pystray.MenuItem("Open SAGE Dashboard", open_dashboard_action),
        pystray.MenuItem("Voice Recognition", toggle_voice_action, checked=lambda item: voice_enabled),
        pystray.MenuItem("Auto-start on Boot", toggle_startup_action, checked=lambda item: startup_manager.is_startup_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", exit_action)
    )
    icon = pystray.Icon("sage-agent", icon_image, "SAGE Desktop Agent", menu)
    logger.info("Starting system tray icon thread.")
    icon.run()


def ensure_api_server():
    """Ensure the Express API server is running on port 5000."""
    import socket
    import subprocess
    
    # Check if port 5000 is open
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", 5000))
        s.close()
        logger.info("Express API server is already running on port 5000.")
        return
    except (socket.timeout, ConnectionRefusedError):
        logger.info("Express API server is not running on port 5000. Starting it...")

    try:
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.abspath(os.path.join(agent_dir, "..", "api-server"))
        root_dir = os.path.abspath(os.path.join(agent_dir, "..", ".."))
        
        # Ensure .env file exists in the root folder
        env_file = os.path.join(root_dir, ".env")
        if not os.path.exists(env_file):
            with open(env_file, "w") as f:
                f.write("GEMINI_API_KEY=YOUR_GEMINI_API_KEY\nPORT=5000\n")
            logger.info(f"Generated default .env file in root: {env_file}")

        # On Windows, suppress the command prompt popup window
        creationflags = 0
        if startup_manager.IS_WINDOWS:
            creationflags = subprocess.CREATE_NO_WINDOW

        # Start Node server
        log_file_path = os.path.join(api_dir, "api-server.log")
        log_file = open(log_file_path, "w", encoding="utf-8")
        node_cmd = ["node", "--env-file=../../.env", "--enable-source-maps", "./dist/index.mjs"]
        subprocess.Popen(
            node_cmd,
            cwd=api_dir,
            creationflags=creationflags,
            stdout=log_file,
            stderr=log_file,
            close_fds=True
        )
        logger.info(f"Launched Express API server in background. Logs: {log_file_path}")
    except Exception as e:
        logger.error(f"Failed to auto-launch Express API server: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Ensure SAGE is registered to run on Windows boot
    if startup_manager.IS_WINDOWS:
        try:
            startup_manager.enable_startup()
            logger.info("Auto-start registry checked/enabled successfully.")
        except Exception as e:
            logger.error(f"Could not enable startup registry: {e}")

    # Ensure Node Express backend is running
    ensure_api_server()

    # Start FastAPI server in a background daemon thread
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            app,
            host="127.0.0.1",
            port=7700,
            reload=False,
            log_level="info",
        ),
        daemon=True
    )
    server_thread.start()

    # Start the continuous voice assistant loop in a background thread
    import voice_assistant
    voice_assistant.start_voice_assistant()

    # Start the background briefings scheduler
    import scheduler
    scheduler.scheduler.start()

    # Start the system tray on the main thread (required on Windows)
    if os.environ.get("SAGE_PRODUCTION") == "1":
        logger.info("Running in SAGE production launcher mode. Bypassing Desktop Agent tray icon.")
        import time
        while True:
            time.sleep(1.0)
    else:
        setup_system_tray()
