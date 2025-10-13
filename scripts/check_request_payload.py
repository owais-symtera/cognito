"""
Quick script to check request_payload values in api_usage_logs table
"""
import asyncio
import asyncpg
import json

async def check_request_payloads():
    """Query the database to check request_payload values"""
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='cognito-engine'
        )

        try:
            rows = await conn.fetch("""
                SELECT
                    id,
                    api_provider,
                    request_payload,
                    timestamp,
                    category_name
                FROM api_usage_logs
                ORDER BY timestamp DESC
                LIMIT 10
            """)

            print("\n" + "="*80)
            print("CHECKING REQUEST_PAYLOAD VALUES IN API_USAGE_LOGS")
            print("="*80 + "\n")

            for i, row in enumerate(rows, 1):
                print(f"Record {i}:")
                print(f"  ID: {row['id']}")
                print(f"  Provider: {row['api_provider']}")
                print(f"  Category: {row['category_name']}")
                print(f"  Timestamp: {row['timestamp']}")
                print(f"  Request Payload Type: {type(row['request_payload'])}")
                print(f"  Request Payload Value: {row['request_payload']}")

                if row['request_payload']:
                    if isinstance(row['request_payload'], str):
                        try:
                            parsed = json.loads(row['request_payload'])
                            print(f"  Parsed Keys: {list(parsed.keys())}")
                        except:
                            pass
                else:
                    print("  ⚠️  REQUEST PAYLOAD IS NULL/EMPTY!")

                print()

        finally:
            await conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_request_payloads())
