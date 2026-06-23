"""
intent_matcher.py — Offline pattern-based intent extractor for local commands.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Intent:
    intent: str
    target: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    confidence: float = 1.0


# App name aliases for opening applications
APP_ALIASES: dict[str, str] = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "spotify": "spotify",
    "notepad": "notepad",
    "cmd": "cmd",
    "command prompt": "cmd",
    "explorer": "explorer",
    "file explorer": "explorer",
    "calculator": "calc",
    "calc": "calc",
    "settings": "ms-settings:",
}

# Processes to close/kill corresponding to common app terms
PROCESS_ALIASES: dict[str, str] = {
    "code": "Code.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "spotify": "Spotify.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "notepad": "notepad.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
}

# System control patterns
_SYSTEM_PATTERNS = [
    (re.compile(r"(?:increase|raise|up)\s+volume", re.I), "volume_control", "up", {}),
    (re.compile(r"(?:decrease|lower|down)\s+volume", re.I), "volume_control", "down", {}),
    (re.compile(r"mute\s*(?:volume|audio)?", re.I), "volume_control", "mute", {}),
    (re.compile(r"unmute\s*(?:volume|audio)?", re.I), "volume_control", "unmute", {}),
    (re.compile(r"(?:increase|raise|up)\s+brightness", re.I), "brightness_control", "up", {}),
    (re.compile(r"(?:decrease|lower|down)\s+brightness", re.I), "brightness_control", "down", {}),
    (re.compile(r"set\s+brightness\s+(?:to\s+)?(\d+)\s*%?", re.I), "brightness_control", "set", {}),
    (re.compile(r"(?:turn\s+on|enable|activate)\s+(?:wi-fi|wifi)", re.I), "wifi_toggle", "on", {}),
    (re.compile(r"(?:turn\s+off|disable|deactivate)\s+(?:wi-fi|wifi)", re.I), "wifi_toggle", "off", {}),
    (re.compile(r"toggle\s+(?:wi-fi|wifi)", re.I), "wifi_toggle", "toggle", {}),
    (re.compile(r"(?:turn\s+on|enable|activate)\s+bluetooth", re.I), "bluetooth_toggle", "on", {}),
    (re.compile(r"(?:turn\s+off|disable|deactivate)\s+bluetooth", re.I), "bluetooth_toggle", "off", {}),
    (re.compile(r"toggle\s+bluetooth", re.I), "bluetooth_toggle", "toggle", {}),
    (re.compile(r"(?:shutdown|power\s+off|turn\s+off)\s+(?:computer|pc|system)", re.I), "shutdown", None, {}),
    (re.compile(r"shutdown", re.I), "shutdown", None, {}),
    (re.compile(r"(?:restart|reboot)\s+(?:computer|pc|system)", re.I), "restart", None, {}),
    (re.compile(r"restart", re.I), "restart", None, {}),
    (re.compile(r"(?:sleep|suspend)\s+(?:computer|pc|system)", re.I), "sleep", None, {}),
    (re.compile(r"sleep", re.I), "sleep", None, {}),
]

# Memory command patterns
_MEMORY_PATTERNS = [
    (re.compile(r"remember\s+(?:that\s+)?(?:my\s+)?(.+?)\s+(?:is|was|to be)\s+(.+)", re.I), "remember"),
    (re.compile(r"remember\s+(.+)", re.I), "remember_fact"),
    (re.compile(r"(?:what|where|when|who)\s+(?:is|was|are|were)\s+my\s+(.+)", re.I), "recall"),
    (re.compile(r"forget\s+(?:all\s+memories|everything)", re.I), "forget_all"),
    (re.compile(r"forget\s+(?:that\s+)?(?:my\s+)?(.+)", re.I), "forget"),
]

# Automation routines
_ROUTINE_PATTERNS = [
    (re.compile(r"(?:open\s+my\s+)?coding\s+setup", re.I), "coding_setup"),
    (re.compile(r"coding\s+mode", re.I), "coding_setup"),
    (re.compile(r"start\s+coding", re.I), "coding_setup"),
    (re.compile(r"study\s+mode", re.I), "study_mode"),
    (re.compile(r"start\s+studying", re.I), "study_mode"),
    (re.compile(r"enable\s+study\s+mode", re.I), "study_mode"),
    (re.compile(r"gaming\s+mode", re.I), "gaming_mode"),
    (re.compile(r"start\s+gaming", re.I), "gaming_mode"),
    (re.compile(r"enable\s+gaming\s+mode", re.I), "gaming_mode"),
    (re.compile(r"(?:what's|what is)\s+(?:happening|the\s+news|new)\s+(?:around\s+the\s+world|globally|today)", re.I), "global_news_briefing"),
    (re.compile(r"global\s+news\s+briefing", re.I), "global_news_briefing"),
    (re.compile(r"news\s+briefing", re.I), "global_news_briefing"),
]

# File management patterns
_FILE_PATTERNS = [
    (re.compile(r"(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:(?:called|named)\s+)?(.+)", re.I), "create_folder"),
    (re.compile(r"(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(?:(?:called|named)\s+)?(.+)", re.I), "create_file"),
    (re.compile(r"rename\s+(.+?)\s+to\s+(.+)", re.I), "rename_file"),
    (re.compile(r"move\s+(.+?)\s+to\s+(.+)", re.I), "move_file"),
    (re.compile(r"(?:delete|remove)\s+(.+)", re.I), "delete_file"),
    (re.compile(r"(?:search|find)\s+(?:files?|folders?)?\s*(?:for|named|called)?\s+(.+)", re.I), "search_files"),
    (re.compile(r"(?:open|show)\s+(?:downloads|the\s+downloads\s+folder)", re.I), "open_folder_downloads"),
    (re.compile(r"(?:open|go\s+to|navigate\s+to)\s+(?:the\s+)?(?:folder|directory|path)\s+(.+)", re.I), "open_folder"),
    (re.compile(r"(?:open|show)\s+(.+?)\s+(?:folder|directory)", re.I), "open_folder"),
]

# Application launch/close patterns
_APP_PATTERNS = [
    (re.compile(r"(?:open|launch|start|run)\s+(.+)", re.I), "open_application"),
    (re.compile(r"(?:close|exit|quit)\s+(.+)", re.I), "close_application"),
    (re.compile(r"(?:kill|stop|terminate)\s+(?:process\s+|app\s+)?(.+)", re.I), "kill_process"),
]


def match_intent(message: str) -> Intent | None:
    """
    Parse message and return matched Intent, or None if no local commands match.
    """
    msg = message.strip().strip("?.! ")

    # 1. System commands
    for pattern, intent, target, extra in _SYSTEM_PATTERNS:
        m = pattern.match(msg)
        if m:
            t = target
            ex = extra.copy()
            if intent == "brightness_control" and target == "set":
                ex["level"] = int(m.group(1))
            return Intent(intent=intent, target=t, extra=ex, raw=message)

    # 2. Memory commands
    for pattern, intent in _MEMORY_PATTERNS:
        m = pattern.match(msg)
        if m:
            if intent == "remember":
                key = m.group(1).strip().strip("'\"").strip("?.! ")
                val = m.group(2).strip().strip("'\"").strip("?.! ")
                return Intent(intent="remember", target=key, extra={"value": val}, raw=message)
            elif intent == "remember_fact":
                fact = m.group(1).strip().strip("'\"").strip("?.! ")
                return Intent(intent="remember", target=fact, extra={"value": fact}, raw=message)
            elif intent == "recall":
                key = m.group(1).strip().strip("'\"").strip("?.! ")
                return Intent(intent="recall", target=key, raw=message)
            elif intent == "forget":
                key = m.group(1).strip().strip("'\"").strip("?.! ")
                return Intent(intent="forget", target=key, raw=message)
            elif intent == "forget_all":
                return Intent(intent="forget_all", raw=message)

    # 3. Automation routines
    for pattern, routine_key in _ROUTINE_PATTERNS:
        if pattern.match(msg):
            return Intent(intent=routine_key, raw=message)

    # 4. File commands
    for pattern, intent in _FILE_PATTERNS:
        m = pattern.match(msg)
        if m:
            if intent == "open_folder_downloads":
                return Intent(intent="open_folder", target="~/Downloads", raw=message)
            elif intent == "rename_file":
                src = m.group(1).strip().strip("'\"")
                dest = m.group(2).strip().strip("'\"")
                return Intent(intent="rename_file", target=src, extra={"new_name": dest}, raw=message)
            elif intent == "move_file":
                src = m.group(1).strip().strip("'\"")
                dest = m.group(2).strip().strip("'\"")
                return Intent(intent="move_file", target=src, extra={"destination": dest}, raw=message)
            else:
                target = m.group(1).strip().strip("'\"")
                return Intent(intent=intent, target=target, raw=message)

    # 5. System Info
    sys_info_pat = re.compile(r"(?:show|get|what(?:'s| is))\s+(?:system|cpu|memory|ram|disk)\s+(?:info|usage|status)?", re.I)
    if sys_info_pat.match(msg):
        return Intent(intent="system_info", raw=message)

    # 6. App commands
    for pattern, intent in _APP_PATTERNS:
        m = pattern.match(msg)
        if m:
            target = m.group(1).strip().strip("'\"")
            target_lower = target.lower()
            resolved = None

            if intent == "open_application":
                # Resolve app name to executable name using aliases
                if target_lower in APP_ALIASES:
                    resolved = APP_ALIASES[target_lower]
                else:
                    for alias, exe in APP_ALIASES.items():
                        if alias in target_lower:
                            resolved = exe
                            break
                extra = {"display_name": target}
                return Intent(intent=intent, target=resolved or target_lower, extra=extra, raw=message)
            
            elif intent in ("close_application", "kill_process"):
                # Resolve app name to process name using aliases
                if target_lower in PROCESS_ALIASES:
                    resolved = PROCESS_ALIASES[target_lower]
                else:
                    for alias, proc in PROCESS_ALIASES.items():
                        if alias in target_lower:
                            resolved = proc
                            break
                # If we couldn't resolve, default to target_lower.exe or target_lower
                proc_name = resolved or (target if target.endswith(".exe") else f"{target}.exe")
                return Intent(intent=intent, target=proc_name, extra={"display_name": target}, raw=message)

    return None
