"""
service_manager.py — Starts, monitors, and stops SAGE backend services.
"""

from __future__ import annotations
import os
import sys
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("sage-launcher")

api_process: Optional[subprocess.Popen] = None
agent_process: Optional[subprocess.Popen] = None


def get_base_dir() -> str:
    """Get the base path of the launcher, handling frozen binary vs script execution."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # dev mode: parent of launcher/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_paths() -> tuple[str, str]:
    """Retrieve absolute paths to api-server and desktop-agent directories."""
    base = get_base_dir()
    
    # Production layout check
    prod_api = os.path.join(base, "api-server")
    prod_agent = os.path.join(base, "desktop-agent")
    if os.path.exists(prod_api) and os.path.exists(prod_agent):
        return prod_api, prod_agent
        
    # Development layout fallback
    dev_api = os.path.join(base, "artifacts", "api-server")
    dev_agent = os.path.join(base, "artifacts", "desktop-agent")
    return dev_api, dev_agent


def start_express_server() -> Optional[subprocess.Popen]:
    """Spawn the Node.js Express server as a background subprocess."""
    global api_process
    api_dir, _ = get_paths()
    
    # Locate configuration dotenv
    env_file = os.path.abspath(os.path.join(api_dir, "..", "..", ".env"))
    if not os.path.exists(env_file):
        env_file = os.path.abspath(os.path.join(get_base_dir(), ".env"))
        
    if not os.path.exists(env_file):
        # Generate default env file if missing
        with open(env_file, "w") as f:
            f.write("GEMINI_API_KEY=YOUR_GEMINI_API_KEY\nPORT=5000\n")
            
    cmd = ["node", f"--env-file={env_file}", "--enable-source-maps", "./dist/index.mjs"]
    
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    log_dir = os.path.join(get_base_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "express-server.log")
    
    logger.info(f"Launching Node.js server in {api_dir}")
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
        api_process = subprocess.Popen(
            cmd,
            cwd=api_dir,
            creationflags=creationflags,
            stdout=log_file,
            stderr=log_file,
            text=True
        )
        return api_process
    except Exception as e:
        logger.error(f"Failed to start Express server: {e}")
        return None


def start_desktop_agent() -> Optional[subprocess.Popen]:
    """Spawn the Python Desktop Agent as a background subprocess."""
    global agent_process
    _, agent_dir = get_paths()
    
    cmd = [sys.executable, "main.py"]
    
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    log_dir = os.path.join(get_base_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "desktop-agent.log")
    
    # Configure production flags so main.py does not spawn a secondary tray icon
    env_vars = os.environ.copy()
    env_vars["SAGE_PRODUCTION"] = "1"
    
    logger.info(f"Launching Python Desktop Agent in {agent_dir}")
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
        agent_process = subprocess.Popen(
            cmd,
            cwd=agent_dir,
            creationflags=creationflags,
            stdout=log_file,
            stderr=log_file,
            env=env_vars,
            text=True
        )
        return agent_process
    except Exception as e:
        logger.error(f"Failed to start Desktop Agent: {e}")
        return None


def stop_all_services():
    """Terminate both backend processes cleanly."""
    global api_process, agent_process
    
    logger.info("Shutting down child processes...")
    
    if api_process:
        try:
            logger.info(f"Terminating Node server (PID {api_process.pid})")
            api_process.terminate()
            api_process.wait(timeout=2.0)
        except Exception:
            try:
                api_process.kill()
            except Exception:
                pass
        api_process = None
        
    if agent_process:
        try:
            logger.info(f"Terminating Python Agent (PID {agent_process.pid})")
            agent_process.terminate()
            agent_process.wait(timeout=2.0)
        except Exception:
            try:
                agent_process.kill()
            except Exception:
                pass
        agent_process = None
