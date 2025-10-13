"""Check all tables in database"""
import asyncio
import asyncpg

async def check_tables():
    """Check all tables in database"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print("[INFO] All tables in database:")
        for table in tables:
            print(f"  - {table['table_name']}")

        # Check specific tables for merged data
        print("\n[INFO] Checking for category/response data tables:")

        response_tables = ['pipeline_responses', 'category_results', 'responses', 'results']
        for tbl in response_tables:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{tbl}'
                )
            """)
            if exists:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {tbl}")
                print(f"  ✓ {tbl}: {count} rows")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables())
