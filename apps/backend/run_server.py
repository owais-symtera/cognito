#!/usr/bin/env python
"""Run the FastAPI server with environment variables loaded."""

import os
import sys
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables from root .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Print which database we're connecting to for verification
print(f"Connecting to database: {os.getenv('DATABASE_NAME', 'NOT SET')}")
print(f"Database host: {os.getenv('DATABASE_HOST', 'NOT SET')}")
print(f"Database user: {os.getenv('DATABASE_USER', 'NOT SET')}")

# Run uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )