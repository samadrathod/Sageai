"""
file_commands.py — Safe file system operation handlers.
"""

from __future__ import annotations
import shutil
import file_manager
import app_launcher


def handle_create_folder(target: str, extra: dict) -> str:
    """Create a folder."""
    return file_manager.create_folder(target)


def handle_create_file(target: str, extra: dict) -> str:
    """Create a file."""
    return file_manager.create_file(target)


def handle_rename_file(target: str, extra: dict) -> str:
    """Rename a file or folder."""
    return file_manager.rename(target, extra.get("new_name", ""))


def handle_move_file(target: str, extra: dict) -> str:
    """Move a file or folder safely to a new path/directory."""
    src_path = file_manager._resolve(target)
    dest_path = file_manager._resolve(extra.get("destination", ""))
    
    if not src_path.exists():
        raise FileNotFoundError(f"Source not found: {src_path}")
        
    if dest_path.is_dir():
        dest_final = dest_path / src_path.name
    else:
        dest_final = dest_path
        
    dest_final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src_path, dest_final)
    return f"Moved '{src_path.name}' to '{dest_final}'"


def handle_delete_file(target: str, extra: dict) -> str:
    """Delete a file or folder."""
    return file_manager.delete(target)


def handle_search_files(target: str, extra: dict) -> str:
    """Search for files and return a formatted string list."""
    matches = file_manager.search_files(target)
    if not matches:
        return f"No files matching '{target}' were found."
    lines = [f"Found {len(matches)} result(s) for '{target}':"]
    for m in matches:
        lines.append(f"  • {m}")
    return "\n".join(lines)


def handle_open_folder(target: str, extra: dict) -> str:
    """Open a folder or directory in the system file manager."""
    return app_launcher.open_path(target or "~")
