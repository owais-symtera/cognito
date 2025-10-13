#!/usr/bin/env python
"""
Run database migrations for CognitoAI Engine.

This script loads environment variables and runs Alembic migrations.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the root .env file
root_dir = Path(__file__).parent.parent.parent
env_file = root_dir / '.env'
load_dotenv(env_file)

# Print environment status for debugging
print(f"Loading environment from: {env_file}")
db_url = os.getenv('DATABASE_URL')
if db_url:
    # Hide password in output
    parts = db_url.split('@')
    if len(parts) > 1:
        print(f"DATABASE_URL found: ...@{parts[-1]}")
else:
    print("DATABASE_URL not found in environment")

# Set DATABASE_URL for Alembic if not already set
if not db_url:
    # Try to build from components
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "cognito_pharma")
    user = os.getenv("DATABASE_USER", "cognito")
    password = os.getenv("DATABASE_PASSWORD", "cognito")

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    os.environ['DATABASE_URL'] = db_url
    print(f"Built DATABASE_URL: ...@{host}:{port}/{name}")

# Run Alembic migrations
from alembic import command
from alembic.config import Config

# Get the alembic configuration
alembic_ini = Path(__file__).parent / "alembic.ini"
alembic_cfg = Config(str(alembic_ini))

# Run the migrations
print("\nRunning migrations...")
try:
    command.upgrade(alembic_cfg, "head")
    print("Migrations completed successfully!")
except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)