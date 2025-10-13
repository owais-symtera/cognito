"""Run migration 006 - Add Merged Data Table"""
import asyncio
import asyncpg

async def run_migration():
    """Execute migration 006"""
    # Read migration file
    with open('apps/backend/migrations/006_add_merged_data_table.sql', 'r') as f:
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
        print("[SUCCESS] Migration 006 completed successfully!")
        print("[SUCCESS] Created table: merged_data_results")
        print("[SUCCESS] Added indexes for performance")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
