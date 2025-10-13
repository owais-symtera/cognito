"""Run migration 005 - Add Validation Schemas"""
import asyncio
import asyncpg

async def run_migration():
    """Execute migration 005"""
    # Read migration file
    with open('apps/backend/migrations/005_add_validation_schemas.sql', 'r') as f:
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
        print("[SUCCESS] Migration 005 completed successfully!")
        print("[SUCCESS] Created tables:")
        print("   - category_validation_schemas")
        print("   - validation_results")
        print("[SUCCESS] Added default validation schema for 'Market Overview' category")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
