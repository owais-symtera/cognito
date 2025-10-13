#!/usr/bin/env python
"""
Check database state for CognitoAI Engine.
"""

import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Load environment
root_dir = Path(__file__).parent.parent.parent
env_file = root_dir / '.env'
load_dotenv(env_file)

# Get database URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    # Build from components
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "cognito_pharma")
    user = os.getenv("DATABASE_USER", "cognito")
    password = os.getenv("DATABASE_PASSWORD", "cognito")
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

print(f"Connecting to database...")

try:
    # Connect to database
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check alembic version
    print("\nChecking alembic version table:")
    try:
        cur.execute("SELECT version_num FROM alembic_version")
        version = cur.fetchone()
        if version:
            print(f"Current version: {version[0]}")
        else:
            print("No version found in alembic_version table")
    except psycopg2.errors.UndefinedTable:
        print("alembic_version table does not exist")
        conn.rollback()

    # List all tables
    print("\nExisting tables:")
    cur.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    tables = cur.fetchall()
    for table in tables:
        print(f"  - {table[0]}")

    # List all indexes
    print("\nExisting indexes:")
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY indexname;
    """)
    indexes = cur.fetchall()
    for idx in indexes:
        print(f"  - {idx[0]}")

    cur.close()
    conn.close()
    print("\nDatabase check complete!")

except Exception as e:
    print(f"Error: {e}")