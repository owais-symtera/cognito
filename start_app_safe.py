#!/usr/bin/env python3
"""
CognitoAI Engine Startup Script

Checks dependencies and starts the application with all services.
Uses virtual environment for all operations.
"""

import os
import sys
import subprocess
import time
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
    # Re-run this script with venv python
    if venv_python.exists():
        subprocess.run([str(venv_python), __file__])
        sys.exit(0)
    else:
        print("[ERROR] Virtual environment not found. Please run: python -m venv venv")
        sys.exit(1)

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend" / "src"))

def check_dependencies():
    """Check if all required services are available."""
    print("[CHECK] Checking dependencies...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8+ required")
        return False
    print("[OK] Python version OK")

    # Check for .env file
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("[WARNING] .env file not found. Creating from example...")
        example_env = Path(__file__).parent / ".env.example"
        if example_env.exists():
            import shutil
            shutil.copy(example_env, env_file)
            print("[INFO] Created .env file. Please add your API keys!")
            return False
    print("[OK] Environment configuration found")

    # Check Redis (optional - will work without it)
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("[OK] Redis is running")
    except:
        print("[WARNING] Redis not available (optional - caching disabled)")

    # Check PostgreSQL (optional for now)
    try:
        import psycopg2
        print("[OK] PostgreSQL driver available")
    except ImportError:
        print("[WARNING] PostgreSQL driver not installed (optional)")

    return True

def install_requirements():
    """Install Python requirements."""
    print("\n[PACKAGES] Installing requirements...")
    backend_dir = Path(__file__).parent / "apps" / "backend"
    requirements_file = backend_dir / "requirements.txt"

    if requirements_file.exists():
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("[OK] Requirements installed")
    else:
        print("[WARNING] requirements.txt not found")

def display_api_info():
    """Display API information and endpoints."""
    print("\n" + "="*60)
    print("CognitoAI Pharmaceutical Intelligence Engine")
    print("="*60)
    print("\n[CAPABILITIES]:")
    print("  - Multi-API Integration (6 AI Providers)")
    print("  - Pharmaceutical Intelligence Gathering")
    print("  - Source Priority & Hierarchical Processing")
    print("  - Temperature Variation Search Strategies")
    print("  - Real-time Collection Monitoring")
    print("  - 4-Stage Pipeline Orchestration")
    print("  - 7-Year Data Retention Compliance")
    print("  - Comprehensive Audit Trails")

    print("\n[AI PROVIDERS]:")
    print("  1. OpenAI ChatGPT")
    print("  2. Anthropic Claude")
    print("  3. Google Gemini")
    print("  4. X.AI Grok")
    print("  5. Perplexity")
    print("  6. Tavily Search")

    print("\n[SECURITY]:")
    print("  - API Key Encryption (AES-256-GCM)")
    print("  - Role-Based Access Control")
    print("  - Connection Pooling with Circuit Breakers")
    print("  - Comprehensive Audit Logging")

    print("\n[MONITORING]:")
    print("  - Real-time Collection Metrics")
    print("  - Historical Accuracy Tracking")
    print("  - Provider Performance Comparison")
    print("  - Cost Optimization Tracking")

    print("\n[API ENDPOINTS]:")
    print("  - API Documentation: http://localhost:8000/api/docs")
    print("  - Alternative Docs: http://localhost:8000/api/redoc")
    print("  - Health Check: http://localhost:8000/health")
    print("  - Root Info: http://localhost:8000/")

    print("\n[KEY ROUTES]:")
    print("  - /api/v1/categories - Pharmaceutical categories")
    print("  - /api/v1/analysis - Intelligence analysis")
    print("  - /api/v1/collection - Collection monitoring")
    print("  - /api/v1/pipeline - Pipeline orchestration")
    print("  - /api/v1/providers - API provider management")

    print("\n" + "="*60)

def start_application():
    """Start the FastAPI application."""
    print("\n[STARTUP] Starting CognitoAI Engine...")
    print("="*60)

    os.chdir(Path(__file__).parent / "apps" / "backend")

    # Start uvicorn
    try:
        import uvicorn

        # Display startup information
        display_api_info()

        print("\n[SERVER] Starting on http://localhost:8000")
        print("[DOCS] Interactive API docs at http://localhost:8000/api/docs")
        print("\nPress CTRL+C to stop the server\n")

        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError:
        print("[ERROR] Uvicorn not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn[standard]"])
        print("[OK] Uvicorn installed. Please run the script again.")
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Shutting down CognitoAI Engine...")
        print("[OK] Application stopped successfully")

def main():
    """Main entry point."""
    print("="*60)
    print("CognitoAI Pharmaceutical Intelligence Engine")
    print("="*60)

    # Check dependencies
    if not check_dependencies():
        print("\n[WARNING] Please resolve dependencies and try again.")
        print("[INFO] Add your API keys to the .env file:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - PERPLEXITY_API_KEY")
        print("   - GEMINI_API_KEY")
        print("   - GROK_API_KEY")
        print("   - TAVILY_API_KEY")
        return

    # Check if requirements need to be installed
    try:
        import fastapi
        import httpx
        import sqlalchemy
        print("[OK] Core packages installed")
    except ImportError:
        print("[PACKAGES] Installing required packages...")
        install_requirements()

    # Start the application
    start_application()

if __name__ == "__main__":
    main()