"""Check validation tables in database"""
import asyncio
import asyncpg

async def check_tables():
    """Check if validation tables exist and their structure"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('category_validation_schemas', 'validation_results')
        """)

        print("[INFO] Existing validation tables:")
        for table in tables:
            print(f"  - {table['table_name']}")

        # Check if default schema exists
        schemas = await conn.fetch("""
            SELECT category_id, category_name, version, enabled
            FROM category_validation_schemas
        """)

        print(f"\n[INFO] Found {len(schemas)} validation schemas:")
        for schema in schemas:
            print(f"  - Category {schema['category_id']}: {schema['category_name']} (v{schema['version']}, enabled={schema['enabled']})")

        # Check validation results
        results_count = await conn.fetchval("SELECT COUNT(*) FROM validation_results")
        print(f"\n[INFO] Total validation results: {results_count}")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables())
