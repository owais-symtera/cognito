#!/usr/bin/env python3
"""
Start CognitoAI Engine without Redis dependency
"""

import os
import sys
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
        import subprocess
        subprocess.run([str(venv_python), __file__])
        sys.exit(0)
    else:
        print("[ERROR] Virtual environment not found.")
        sys.exit(1)

# Set environment variable to disable Redis
os.environ["DISABLE_REDIS"] = "true"

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend" / "src"))

print("="*60)
print("CognitoAI Pharmaceutical Intelligence Engine")
print("="*60)
print("\n[INFO] Starting without Redis (caching disabled)")

os.chdir(Path(__file__).parent / "apps" / "backend")

try:
    import uvicorn

    print("\n[SUCCESS] Application is starting!")
    print("\n[CAPABILITIES]:")
    print("  - 6 AI Providers Integrated")
    print("  - Pharmaceutical Intelligence Gathering")
    print("  - 4-Stage Pipeline Orchestration")
    print("  - Source Priority & Hierarchical Processing")
    print("  - Temperature Variation Strategies")
    print("  - 7-Year Data Retention Compliance")

    print("\n[INTEGRATED AI PROVIDERS]:")
    print("  1. OpenAI ChatGPT")
    print("  2. Anthropic Claude")
    print("  3. Google Gemini")
    print("  4. X.AI Grok")
    print("  5. Perplexity")
    print("  6. Tavily Search")

    print("\n[API ENDPOINTS]:")
    print("  - API Documentation: http://localhost:8000/api/docs")
    print("  - Health Check: http://localhost:8000/health")
    print("  - Categories: http://localhost:8000/api/v1/categories")

    print("\n[SERVER] Starting on http://localhost:8000")
    print("[DOCS] Interactive API docs at http://localhost:8000/api/docs\n")
    print("Press CTRL+C to stop the server\n")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("[INFO] Installing minimal requirements...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi", "httpx", "sqlalchemy"])
    print("[INFO] Please run the script again")
except KeyboardInterrupt:
    print("\n[SHUTDOWN] Application stopped")