#!/usr/bin/env python
"""
Clean database for fresh migration.
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
    conn.autocommit = True
    cur = conn.cursor()

    # Drop all tables in public schema
    print("Dropping all tables...")
    cur.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
            LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)

    # Drop all types
    print("Dropping all custom types...")
    cur.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace)
            LOOP
                BEGIN
                    EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                EXCEPTION
                    WHEN others THEN NULL;
                END;
            END LOOP;
        END $$;
    """)

    # Verify cleanup
    cur.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'")
    count = cur.fetchone()[0]
    print(f"Tables remaining: {count}")

    cur.close()
    conn.close()
    print("Database cleaned successfully!")

except Exception as e:
    print(f"Error: {e}")