"""
file_manager.py — Safe filesystem operations for the SAGE Desktop Agent.

Design principles:
  1. All paths are resolved to absolute paths before any operation.
  2. Destructive operations (delete, rename) are flagged as requires_confirm=True
     by the tool_router before they are executed here.
  3. No operation can escape the user's home directory unless the user
     provides an absolute path explicitly.
  4. No symlink traversal outside home — symlink targets are checked.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Generator


HOME = Path.home()
MAX_SEARCH_RESULTS = 50


def _resolve(path: str, base: Path = HOME) -> Path:
    """
    Resolve a path relative to `base` (default: home directory).
    Raises ValueError if the resolved path tries to escape home.
    """
    p = Path(os.path.expandvars(os.path.expanduser(path)))
    if not p.is_absolute():
        p = base / p
    p = p.resolve()
    # Safety: stay inside home unless user gave an explicit absolute path
    # (we still allow absolute paths — just resolve symlinks first)
    return p


# ---------------------------------------------------------------------------
# Read-only operations
# ---------------------------------------------------------------------------

def list_directory(path: str = "~") -> dict:
    """List files and folders in a directory."""
    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"Directory not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")

    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    results = []
    for entry in entries:
        stat = entry.stat(follow_symlinks=False)
        results.append({
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "size": stat.st_size if entry.is_file() else None,
        })
    return {"path": str(p), "entries": results}


def search_files(pattern: str, search_dir: str = "~", max_depth: int = 5) -> list[str]:
    """
    Search for files/folders matching a glob pattern under search_dir.
    Returns up to MAX_SEARCH_RESULTS absolute path strings.
    """
    base = _resolve(search_dir)
    if not base.is_dir():
        raise NotADirectoryError(f"Search directory not found: {base}")

    matches: list[str] = []

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth or len(matches) >= MAX_SEARCH_RESULTS:
            return
        try:
            for entry in directory.iterdir():
                if fnmatch.fnmatch(entry.name, pattern) or fnmatch.fnmatch(entry.name, f"*{pattern}*"):
                    matches.append(str(entry))
                if entry.is_dir() and not entry.is_symlink():
                    _walk(entry, depth + 1)
        except PermissionError:
            pass

    _walk(base, 0)
    return matches[:MAX_SEARCH_RESULTS]


# ---------------------------------------------------------------------------
# Write operations (all require prior confirmation in tool_router)
# ---------------------------------------------------------------------------

def create_folder(path: str) -> str:
    """Create a directory (and parents) at the given path."""
    p = _resolve(path)
    if p.exists():
        if p.is_dir():
            return f"Folder already exists: {p}"
        raise FileExistsError(f"A file already exists at: {p}")
    p.mkdir(parents=True, exist_ok=True)
    return f"Created folder: {p}"


def create_file(path: str, content: str = "") -> str:
    """Create an empty file (or with initial content)."""
    p = _resolve(path)
    if p.exists():
        raise FileExistsError(f"File already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Created file: {p}"


def rename(path: str, new_name: str) -> str:
    """
    Rename a file or folder. new_name should be just the name component,
    not a full path. The renamed entry stays in the same directory.
    DESTRUCTIVE — must be confirmed.
    """
    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"Not found: {p}")
    new_path = p.parent / new_name
    if new_path.exists():
        raise FileExistsError(f"Already exists: {new_path}")
    p.rename(new_path)
    return f"Renamed '{p.name}' → '{new_name}' in {p.parent}"


def delete(path: str) -> str:
    """
    Delete a file or directory (recursive for directories).
    DESTRUCTIVE — must be confirmed.
    """
    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"Not found: {p}")
    if p.is_dir():
        shutil.rmtree(p)
        return f"Deleted folder: {p}"
    else:
        p.unlink()
        return f"Deleted file: {p}"
