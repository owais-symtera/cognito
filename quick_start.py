#!/usr/bin/env python3
"""
CognitoAI Engine Quick Start Script
Starts the application immediately with minimal checks
"""

import os
import sys
import subprocess
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# Ensure we're using the virtual environment
project_root = Path(__file__).parent
venv_python = project_root / "venv" / "Scripts" / "python.exe"

# Check if running in venv
if not sys.prefix.endswith('venv'):
    print("[WARNING] Not running in virtual environment!")
    print("Starting with venv...")
    if venv_python.exists():
        subprocess.run([str(venv_python), __file__])
        sys.exit(0)
    else:
        print("[ERROR] Virtual environment not found.")
        sys.exit(1)

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend" / "src"))

print("="*60)
print("CognitoAI Pharmaceutical Intelligence Engine")
print("="*60)
print("\n[QUICK START] Starting application with existing packages...")

os.chdir(Path(__file__).parent / "apps" / "backend")

try:
    import uvicorn

    print("\n[SERVER] Starting on http://localhost:8000")
    print("[DOCS] Interactive API docs at http://localhost:8000/api/docs")
    print("\nPress CTRL+C to stop the server\n")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for quick start
        log_level="info"
    )
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("[INFO] Please wait for full installation to complete")
except KeyboardInterrupt:
    print("\n[SHUTDOWN] Application stopped")