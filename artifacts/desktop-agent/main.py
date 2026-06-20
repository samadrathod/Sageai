"""
main.py — SAGE Desktop Agent API server.

Runs locally on http://localhost:7700 on the user's machine.
The SAGE web app (running in the browser) connects to this server to
execute desktop commands (open apps, manage files, etc.).

Endpoints:
  GET  /health          → liveness check
  POST /execute         → parse intent and execute or return confirm prompt
  GET  /system/info     → current CPU / memory / disk snapshot
  GET  /processes       → running processes (top 20 by CPU)

CORS is configured to accept requests from any origin because the web app
may be served from a .replit.app domain or localhost during development.
For security, this server binds to 127.0.0.1 only — it is NOT accessible
from the network, only from the local machine.

Run with:
  pip install -r requirements.txt
  python main.py
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from intent_detector import detect
from tool_router import route
import system_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("sage-agent")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SAGE Desktop Agent",
    description="Local desktop control API for the SAGE assistant.",
    version="1.0.0",
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "SAGE Desktop Agent v1.0"}


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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("SAGE Desktop Agent starting on http://127.0.0.1:7700")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=7700,
        reload=False,
        log_level="info",
    )
