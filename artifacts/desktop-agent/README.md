# SAGE Desktop Agent

A local Python service that gives the SAGE web assistant control over your desktop.

## What it can do

| Command (say it to SAGE) | Action |
|---|---|
| "Open VS Code" | Launches VS Code |
| "Open Chrome" | Launches Chrome |
| "Open Spotify" | Launches Spotify |
| "Create folder called DSA" | Creates `~/DSA/` |
| "Create file called notes.txt" | Creates `~/notes.txt` |
| "Rename projects to my-projects" | Renames folder |
| "Delete old_backup" | Deletes (with confirmation) |
| "Search for resume" | Finds files matching "resume" in home |
| "List my Documents folder" | Shows contents |
| "Show system info" | CPU / RAM / disk usage |
| "Kill Spotify" | Terminates process (with confirmation) |

## Setup

### Requirements
- Python 3.10 or newer
- Windows, macOS, or Linux

### Install and run

```bash
# 1. Clone or download this folder to your machine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the agent
python main.py
```

The agent runs at **http://localhost:7700** — only accessible from your machine.

## Architecture

```
main.py              FastAPI HTTP server (port 7700)
  └── intent_detector.py   Parses natural language → structured intent
  └── tool_router.py       Routes intent to tool, applies safety gates
        └── app_launcher.py    Opens apps and paths
        └── file_manager.py    Creates/renames/deletes files & folders
        └── system_manager.py  CPU/memory info, process control
```

## Safety

- The agent binds to `127.0.0.1` only — not accessible from the internet.
- Destructive actions (delete, rename, kill process) require a confirmation from the SAGE UI before executing.
- No shell=True subprocess calls; all commands use explicit argument lists.
- File operations stay within your home directory by default.

## Future roadmap

- [ ] Auto-start with Windows (Task Scheduler / startup folder)
- [ ] System tray icon (pystray)
- [ ] Wake word detection ("Hey SAGE") — offline with Vosk
- [ ] Plugin architecture (drop a `.py` file in `plugins/` to add new capabilities)
- [ ] Offline speech recognition (Vosk / Whisper)
