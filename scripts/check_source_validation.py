"""Check per-source validation results with JSON tables"""
import asyncio
import asyncpg
import json

async def check_source_validations():
    """Check per-source validation results for the latest request"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Get latest request
        latest_request = await conn.fetchrow("""
            SELECT id, drug_name, status, created_at
            FROM drug_requests
            ORDER BY created_at DESC
            LIMIT 1
        """)

        if not latest_request:
            print("[ERROR] No requests found")
            return

        print(f"\n{'='*100}")
        print(f"LATEST REQUEST")
        print(f"{'='*100}")
        print(f"Request ID: {latest_request['id']}")
        print(f"Drug: {latest_request['drug_name']}")
        print(f"Status: {latest_request['status']}")
        print(f"Created: {latest_request['created_at']}")

        # Get category results for this request
        category_results = await conn.fetch("""
            SELECT id, category_id, category_name
            FROM category_results
            WHERE request_id = $1
            ORDER BY id DESC
        """, latest_request['id'])

        for cat_result in category_results:
            print(f"\n{'='*100}")
            print(f"CATEGORY: {cat_result['category_name']}")
            print(f"{'='*100}")

            # Get per-source validation results
            source_validations = await conn.fetch("""
                SELECT
                    id, source_index, provider, model,
                    authority_score, tables_json,
                    total_tables, total_rows, validated_rows,
                    validation_score, validation_passed, pass_rate,
                    validated_at
                FROM source_validation_results
                WHERE category_result_id = $1
                ORDER BY source_index ASC
            """, cat_result['id'])

            if not source_validations:
                print("[INFO] No per-source validation results found for this category")
                continue

            print(f"\nFound {len(source_validations)} source validation results:\n")

            for sv in source_validations:
                print(f"\n{'-'*100}")
                print(f"SOURCE #{sv['source_index'] + 1}: {sv['provider']} ({sv['model']})")
                print(f"{'-'*100}")
                print(f"Authority Score: {sv['authority_score']}")
                print(f"Total Tables: {sv['total_tables']}")
                print(f"Total Rows: {sv['total_rows']}")
                print(f"Validated Rows: {sv['validated_rows']}")
                print(f"Pass Rate: {sv['pass_rate']}")
                print(f"Validation Passed: {sv['validation_passed']}")
                print(f"Validation Score: {sv['validation_score']}")

                # Parse tables JSON
                tables_json = sv['tables_json']
                if isinstance(tables_json, str):
                    tables_json = json.loads(tables_json)

                if not tables_json:
                    print("\n[INFO] No tables found in this source")
                    continue

                # Display each table with row validation
                for table in tables_json:
                    print(f"\n  TABLE {table['table_index']}:")
                    print(f"  Headers: {', '.join(table['headers'])}")
                    print(f"  Total Rows: {table['total_rows']}")
                    print(f"  Validated: {table['validated_rows']}")
                    print(f"  Failed: {table['failed_rows']}")
                    print(f"  Pass Rate: {table['pass_rate']}")

                    print(f"\n  ROW-BY-ROW VALIDATION:")
                    print(f"  {'-'*95}")

                    for row in table['rows'][:10]:  # Show first 10 rows
                        status = row['validation']['status']
                        status_icon = "✓" if status == "PASS" else "✗"

                        print(f"\n  Row {row['row_number']}: [{status_icon} {status}]")

                        # Show row data
                        for header, value in row['data'].items():
                            if len(str(value)) > 80:
                                value = str(value)[:77] + "..."
                            print(f"    {header}: {value}")

                        # Show validation details
                        val = row['validation']
                        if val['has_source']:
                            print(f"    ✓ Source: {val.get('source_name', 'Unknown')}")
                            print(f"      Priority: {val.get('source_priority')} | Type: {val.get('source_type')}")
                        else:
                            print(f"    ✗ FAIL: {val.get('reason', 'No source')}")

                    if len(table['rows']) > 10:
                        print(f"\n  ... and {len(table['rows']) - 10} more rows")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_source_validations())
