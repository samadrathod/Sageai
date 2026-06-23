"""
watchdog.py — Monitors SAGE backend processes and executes auto-restarts.
"""

from __future__ import annotations
import time
import logging
import threading
import requests
import service_manager
import state_manager

logger = logging.getLogger("sage-launcher")

_watchdog_thread: threading.Thread | None = None
_should_run = True

# Max restart attempts before marking as FAILED
MAX_RETRIES = 5
_api_retries = 0
_agent_retries = 0


def _check_http_health(url: str) -> bool:
    """Helper to perform HTTP GET health checks with short timeout."""
    try:
        r = requests.get(url, timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _check_voice_engine_status() -> str:
    """Check the Desktop Agent settings to verify the Voice Engine status."""
    try:
        r = requests.get("http://127.0.0.1:7700/settings", timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            return "ONLINE" if data.get("voice_enabled") else "OFFLINE"
    except Exception:
        pass
    return "OFFLINE"


def _monitor_loop():
    """Main monitor loop checking service health every 5 seconds."""
    global _api_retries, _agent_retries
    
    logger.info("Watchdog monitor loop started.")
    
    # Give services a few seconds to boot up initially
    time.sleep(5.0)
    
    while _should_run:
        # 1. Monitor Express API Server
        api_proc = service_manager.api_process
        api_alive = api_proc is not None and api_proc.poll() is None
        api_healthy = api_alive and _check_http_health("http://127.0.0.1:5000/health")
        
        if api_healthy:
            state_manager.set_state("API_SERVER", "ONLINE")
            _api_retries = 0
        else:
            if _api_retries < MAX_RETRIES:
                logger.warning("Express API Server is unresponsive or crashed. Restarting...")
                state_manager.set_state("API_SERVER", "RESTARTING")
                
                # Cleanup and restart
                if api_proc:
                    try:
                        api_proc.kill()
                    except Exception:
                        pass
                
                service_manager.start_express_server()
                _api_retries += 1
                time.sleep(2.0)
            else:
                logger.critical("Express API Server has failed repeatedly. Giving up.")
                state_manager.set_state("API_SERVER", "FAILED")
        
        # 2. Monitor Desktop Agent
        agent_proc = service_manager.agent_process
        agent_alive = agent_proc is not None and agent_proc.poll() is None
        agent_healthy = agent_alive and _check_http_health("http://127.0.0.1:7700/health")
        
        if agent_healthy:
            state_manager.set_state("DESKTOP_AGENT", "ONLINE")
            _agent_retries = 0
            
            # 3. Monitor Voice Engine state (derived from Agent settings)
            voice_status = _check_voice_engine_status()
            state_manager.set_state("VOICE_ENGINE", voice_status)
        else:
            state_manager.set_state("VOICE_ENGINE", "OFFLINE")
            if _agent_retries < MAX_RETRIES:
                logger.warning("Python Desktop Agent is unresponsive or crashed. Restarting...")
                state_manager.set_state("DESKTOP_AGENT", "RESTARTING")
                
                # Cleanup and restart
                if agent_proc:
                    try:
                        agent_proc.kill()
                    except Exception:
                        pass
                
                service_manager.start_desktop_agent()
                _agent_retries += 1
                time.sleep(2.0)
            else:
                logger.critical("Python Desktop Agent has failed repeatedly. Giving up.")
                state_manager.set_state("DESKTOP_AGENT", "FAILED")
                
        time.sleep(5.0)


def start_watchdog():
    """Start the watchdog monitor thread."""
    global _watchdog_thread, _should_run
    _should_run = True
    _watchdog_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _watchdog_thread.start()
    logger.info("Watchdog background thread spawned.")


def stop_watchdog():
    """Stop the watchdog monitor thread."""
    global _should_run
    _should_run = False
    logger.info("Watchdog stop signal sent.")
