"""
memory_commands.py — Local SQLite-backed memory/database operations.
"""

from __future__ import annotations
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.db")


def init_db():
    """Initialize the memories database table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Ensure database and table exist
init_db()


def handle_remember(target: str, extra: dict) -> str:
    """Save or update a key-value memory."""
    val = extra.get("value", target)
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO memories (key, value) VALUES (?, ?)",
            (target.lower(), val)
        )
        conn.commit()
    finally:
        conn.close()
    return f"I've remembered that your {target} is {val}."


def handle_recall(target: str, extra: dict) -> str:
    """Recall a memory matching the target key (exact or partial)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        # Look for exact match first, then partial match
        cursor.execute("SELECT key, value FROM memories WHERE key = ?", (target.lower(),))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT key, value FROM memories WHERE key LIKE ?", (f"%{target.lower()}%",))
            row = cursor.fetchone()
    finally:
        conn.close()
        
    if row:
        # Capitalize target name nicely if matched
        return f"Your {row[0]} is {row[1]}."
    return f"I don't have any record of your '{target}'."


def handle_forget(target: str, extra: dict) -> str:
    """Delete a memory matching the target key."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM memories WHERE key = ?", (target.lower(),))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT key FROM memories WHERE key LIKE ?", (f"%{target.lower()}%",))
            row = cursor.fetchone()
            
        if row:
            key_found = row[0]
            cursor.execute("DELETE FROM memories WHERE key = ?", (key_found,))
            conn.commit()
            return f"I have forgotten your {key_found}."
    finally:
        conn.close()
        
    return f"I couldn't find any memory matching '{target}' to forget."


def handle_forget_all(target: str | None, extra: dict) -> str:
    """Clear all memories from the database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
    finally:
        conn.close()
    return "I have forgotten all of your memories."
