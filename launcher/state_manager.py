"""
state_manager.py — Tracks and coordinates status states for SAGE core services.
"""

from __future__ import annotations
import threading
from typing import Callable

_lock = threading.Lock()

# States: ONLINE, OFFLINE, RESTARTING, FAILED
_state = {
    "API_SERVER": "OFFLINE",
    "DESKTOP_AGENT": "OFFLINE",
    "VOICE_ENGINE": "OFFLINE"
}

_listeners: list[Callable[[str, str], None]] = []


def register_listener(callback: Callable[[str, str], None]):
    """Register a callback that fires when any service state changes."""
    with _lock:
        _listeners.append(callback)


def set_state(service: str, status: str):
    """Set the state of a service and notify listeners if it changed."""
    trigger_notify = False
    with _lock:
        if service in _state:
            old = _state[service]
            _state[service] = status
            if old != status:
                trigger_notify = True
                
    if trigger_notify:
        for cb in _listeners:
            try:
                cb(service, status)
            except Exception:
                pass


def get_state(service: str) -> str:
    """Retrieve the current state of a service."""
    with _lock:
        return _state.get(service, "OFFLINE")


def get_all_states() -> dict[str, str]:
    """Retrieve a copy of all service states."""
    with _lock:
        return _state.copy()


def get_overall_status() -> str:
    """
    Get the overall health of the assistant:
    - GREEN: All systems online.
    - RED: Critical failure (Express API and Desktop Agent are offline/failed).
    - YELLOW: Partial warning (some systems restarting or only one online).
    """
    with _lock:
        states = _state.copy()
        
    api = states["API_SERVER"]
    agent = states["DESKTOP_AGENT"]
    voice = states["VOICE_ENGINE"]
    
    if api == "ONLINE" and agent == "ONLINE" and voice == "ONLINE":
        return "GREEN"
    if api in ("FAILED", "OFFLINE") and agent in ("FAILED", "OFFLINE"):
        return "RED"
    return "YELLOW"
