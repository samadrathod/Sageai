"""
build_release.py — Production packaging pipeline for SAGE.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys


def clean_dir(path: str):
    """Safely delete and recreate a directory."""
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)


def build_sage_app():
    logger = lambda msg: print(f"\n>>> [BUILD] {msg}\n")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    release_dir = os.path.join(root_dir, "SAGE")
    
    # 1. Build React dashboard
    logger("Compiling React frontend dashboard...")
    subprocess.run(
        ["pnpm", "run", "build"],
        cwd=os.path.join(root_dir, "artifacts", "sage"),
        shell=True,
        check=True
    )
    
    # 2. Build Node Express server
    logger("Compiling Express API server...")
    subprocess.run(
        ["pnpm", "run", "build"],
        cwd=os.path.join(root_dir, "artifacts", "api-server"),
        shell=True,
        check=True
    )
    
    # 3. Build launcher binary using PyInstaller
    logger("Compiling SAGE.exe launcher via PyInstaller...")
    # --onefile creates SAGE.exe
    # --noconsole suppresses cmd console window popup
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "SAGE",
        "--workpath", os.path.join(root_dir, "build_pyi"),
        "--distpath", os.path.join(root_dir, "release_temp"),
        "launcher/launcher.py"
    ]
    subprocess.run(cmd, check=True)
    
    # 4. Construct SAGE production directory layout
    logger("Assembling SAGE release directory structure...")
    clean_dir(release_dir)
    
    # Copy SAGE.exe to root
    shutil.copy(
        os.path.join(root_dir, "release_temp", "SAGE.exe"),
        os.path.join(release_dir, "SAGE.exe")
    )
    
    # Copy API server distribution and node_modules
    api_dest = os.path.join(release_dir, "api-server")
    clean_dir(api_dest)
    shutil.copytree(
        os.path.join(root_dir, "artifacts", "api-server", "dist"),
        os.path.join(api_dest, "dist"),
        symlinks=True
    )
    shutil.copytree(
        os.path.join(root_dir, "artifacts", "api-server", "node_modules"),
        os.path.join(api_dest, "node_modules"),
        symlinks=True
    )
    
    # Copy Dashboard static files
    sage_dest = os.path.join(release_dir, "sage")
    clean_dir(sage_dest)
    shutil.copytree(
        os.path.join(root_dir, "artifacts", "sage", "dist"),
        os.path.join(sage_dest, "dist"),
        symlinks=True
    )
    
    # Copy Desktop Agent Python code
    agent_dest = os.path.join(release_dir, "desktop-agent")
    clean_dir(agent_dest)
    
    # Copy agent root folder items (excluding log and db files)
    src_agent = os.path.join(root_dir, "artifacts", "desktop-agent")
    for item in os.listdir(src_agent):
        s = os.path.join(src_agent, item)
        d = os.path.join(agent_dest, item)
        
        if os.path.isdir(s):
            if item not in ("__pycache__", "local_commands", "dist", "build"):
                shutil.copytree(s, d, symlinks=True)
        else:
            if not item.endswith((".pyc", ".db", ".log")):
                shutil.copy(s, d)
                
    # Copy local_commands folder
    shutil.copytree(
        os.path.join(src_agent, "local_commands"),
        os.path.join(agent_dest, "local_commands"),
        symlinks=True
    )
    
    # Create empty folders for production use
    os.makedirs(os.path.join(release_dir, "resources"), exist_ok=True)
    os.makedirs(os.path.join(release_dir, "database"), exist_ok=True)
    os.makedirs(os.path.join(release_dir, "logs"), exist_ok=True)
    
    # Copy .env file to release base folder
    shutil.copy(os.path.join(root_dir, ".env"), os.path.join(release_dir, ".env"))
    
    # Clean up compilation artifacts
    logger("Cleaning up temporary build folders...")
    shutil.rmtree(os.path.join(root_dir, "release_temp"), ignore_errors=True)
    shutil.rmtree(os.path.join(root_dir, "build_pyi"), ignore_errors=True)
    
    spec_file = os.path.join(root_dir, "SAGE.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)
        
    logger("SUCCESS! SAGE Release directory is built inside: './SAGE'")


if __name__ == "__main__":
    build_sage_app()
