"""Run migration 008 - Add Source Validation Results Table"""
import asyncio
import asyncpg

async def run_migration():
    """Execute migration 008"""
    # Read migration file
    with open('apps/backend/migrations/008_add_source_validation_results.sql', 'r') as f:
        migration_sql = f.read()

    # Connect to database
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Execute migration
        await conn.execute(migration_sql)
        print("[SUCCESS] Migration 008 completed successfully!")
        print("[SUCCESS] Created table: source_validation_results")
        print("[SUCCESS] Added indexes for performance")
        print("[INFO] This table stores per-source validation with table-to-JSON conversion")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
