---
name: SAGE Desktop Agent Architecture
description: How the Python local desktop agent integrates with the SAGE web app
---

# SAGE Desktop Agent Architecture

**Why:** The desktop agent is a separate local Python process on the user's machine. The web app cannot directly execute OS commands — it must delegate to a local HTTP server.

**How it works:**
- Python FastAPI server runs at `http://127.0.0.1:7700` on the user's machine
- SAGE web app (`use-desktop-agent.ts`) pings `/health` every 10 seconds
- When the agent is online, user messages are first sent to `/execute` before Gemini
- Agent returns `{ handled: false }` for non-desktop commands → falls through to Gemini
- Destructive actions return `requires_confirm: true` → frontend shows amber banner

**File locations:**
- `artifacts/desktop-agent/` — all Python agent files (standalone, runs on user machine)
- `artifacts/sage/src/hooks/use-desktop-agent.ts` — frontend connector hook
- `artifacts/sage/src/hooks/use-voice.ts` — Web Speech API STT + TTS hook

**Safety rules:**
- Agent binds to 127.0.0.1 only (not network-accessible)
- DESTRUCTIVE_INTENTS = {delete, rename, kill_process, run_command} require confirm
- No shell=True subprocess calls anywhere in the agent

**How to apply:** When adding new intents, add them to `intent_detector.py` patterns, route them in `tool_router.py`, and flag them in DESTRUCTIVE_INTENTS if they modify/delete data.
