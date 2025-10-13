"""Find verification details for a specific pipeline stage execution"""
import asyncio
import asyncpg
import json

async def find_verification_details(stage_execution_id: str):
    """Find all verification details for a pipeline stage execution"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Get the pipeline stage execution
        stage_exec = await conn.fetchrow("""
            SELECT
                id, request_id, category_result_id, stage_name,
                executed, skipped, input_data, output_data,
                stage_metadata, execution_time_ms,
                started_at, completed_at
            FROM pipeline_stage_executions
            WHERE id = $1
        """, stage_execution_id)

        if not stage_exec:
            print(f"[ERROR] No pipeline stage execution found with ID: {stage_execution_id}")
            return

        print(f"\n{'='*100}")
        print(f"PIPELINE STAGE EXECUTION")
        print(f"{'='*100}")
        print(f"ID: {stage_exec['id']}")
        print(f"Request ID: {stage_exec['request_id']}")
        print(f"Category Result ID: {stage_exec['category_result_id']}")
        print(f"Stage Name: {stage_exec['stage_name']}")
        print(f"Executed: {stage_exec['executed']}")
        print(f"Skipped: {stage_exec['skipped']}")
        print(f"Execution Time: {stage_exec['execution_time_ms']} ms")
        print(f"Started At: {stage_exec['started_at']}")
        print(f"Completed At: {stage_exec['completed_at']}")

        # Parse and display output_data (verification result)
        output_data = stage_exec['output_data']
        if isinstance(output_data, str):
            output_data = json.loads(output_data)

        print(f"\n{'='*100}")
        print(f"VERIFICATION OUTPUT DATA (Summary)")
        print(f"{'='*100}")
        print(json.dumps(output_data, indent=2))

        # Check if per-source validation data exists
        if 'source_validations' in output_data:
            print(f"\n{'='*100}")
            print(f"PER-SOURCE VALIDATION SUMMARY (from output_data)")
            print(f"{'='*100}")
            print(json.dumps(output_data['source_validations'], indent=2))
        else:
            print(f"\n[INFO] This execution was before per-source validation was implemented")
            print(f"[INFO] Run a new request to see per-source validation details")

        # Get the specific category result for this stage
        category_result_id = stage_exec['category_result_id']

        if not category_result_id:
            print(f"\n[INFO] No category_result_id linked to this stage execution")
            return

        cat_result = await conn.fetchrow("""
            SELECT id, category_id, category_name
            FROM category_results
            WHERE id = $1
        """, category_result_id)

        if not cat_result:
            print(f"\n[INFO] No category result found for ID: {category_result_id}")
            return

        print(f"\n{'='*100}")
        print(f"CATEGORY RESULT FOR THIS VERIFICATION")
        print(f"{'='*100}")
        print(f"Category: {cat_result['category_name']}")
        print(f"Category Result ID: {cat_result['id']}")

        # Get per-source validation results
        source_validations = await conn.fetch("""
            SELECT
                id, source_index, provider, model,
                authority_score, total_tables, total_rows,
                validated_rows, validation_score, validation_passed,
                pass_rate, validated_at
            FROM source_validation_results
            WHERE category_result_id = $1
            ORDER BY source_index ASC
        """, cat_result['id'])

        if source_validations:
            print(f"\n{'='*100}")
            print(f"PER-SOURCE VALIDATION RESULTS ({len(source_validations)} sources)")
            print(f"{'='*100}")

            for sv in source_validations:
                print(f"\nSource #{sv['source_index'] + 1}: {sv['provider']} ({sv['model']})")
                print(f"  - Authority Score: {sv['authority_score']}")
                print(f"  - Tables: {sv['total_tables']} | Rows: {sv['total_rows']}")
                print(f"  - Validated Rows: {sv['validated_rows']}")
                print(f"  - Pass Rate: {sv['pass_rate']}")
                print(f"  - Validation Passed: {sv['validation_passed']}")
                print(f"  - Validation Score: {sv['validation_score']}")
                print(f"  - Validated At: {sv['validated_at']}")

                # Get detailed tables JSON
                tables_detail = await conn.fetchval("""
                    SELECT tables_json
                    FROM source_validation_results
                    WHERE id = $1
                """, sv['id'])

                if tables_detail:
                    if isinstance(tables_detail, str):
                        tables_detail = json.loads(tables_detail)

                    print(f"\n  DETAILED TABLE VALIDATION:")
                    for table in tables_detail:
                        print(f"\n    Table {table['table_index']}:")
                        print(f"      - Headers: {', '.join(table['headers'])}")
                        print(f"      - Total Rows: {table['total_rows']}")
                        print(f"      - Validated: {table['validated_rows']}")
                        print(f"      - Failed: {table['failed_rows']}")
                        print(f"      - Pass Rate: {table['pass_rate']}")

                    print(f"\n  [INFO] Use 'python check_source_validation.py' to see row-by-row details")
        else:
            print(f"\n[INFO] No per-source validation results found")

        # Get aggregated validation results
        validation_results = await conn.fetch("""
            SELECT
                id, validation_passed, validation_score,
                confidence_penalty, failed_steps,
                recommendations, validated_at
            FROM validation_results
            WHERE category_result_id = $1
            ORDER BY validated_at DESC
        """, cat_result['id'])

        if validation_results:
            print(f"\n{'='*100}")
            print(f"AGGREGATED VALIDATION RESULTS")
            print(f"{'='*100}")

            for vr in validation_results:
                print(f"\nValidation ID: {vr['id']}")
                print(f"  - Passed: {vr['validation_passed']}")
                print(f"  - Score: {vr['validation_score']}")
                print(f"  - Confidence Penalty: {vr['confidence_penalty']}")
                print(f"  - Failed Steps: {vr['failed_steps']}")
                print(f"  - Recommendations: {vr['recommendations']}")
                print(f"  - Validated At: {vr['validated_at']}")

        print(f"\n{'='*100}")
        print(f"SUMMARY - WHERE TO FIND VERIFICATION DETAILS")
        print(f"{'='*100}")
        print(f"\n1. Pipeline Stage Metadata:")
        print(f"   - Table: pipeline_stage_executions")
        print(f"   - Columns: output_data (JSONB), stage_metadata (JSONB)")
        print(f"   - Query: SELECT output_data FROM pipeline_stage_executions WHERE id = '{stage_execution_id}'")
        print(f"\n2. Per-Source Validation (NEW!):")
        print(f"   - Table: source_validation_results")
        print(f"   - Query: SELECT * FROM source_validation_results WHERE category_result_id = '{category_result_id}'")
        print(f"   - Contains: provider, model, total_rows, validated_rows, pass_rate, tables_json")
        print(f"\n3. Aggregated Validation:")
        print(f"   - Table: validation_results")
        print(f"   - Query: SELECT * FROM validation_results WHERE category_result_id = '{category_result_id}'")
        print(f"\n4. Row-by-Row Details:")
        print(f"   - Column: source_validation_results.tables_json (JSONB)")
        print(f"   - Contains: JSON array with each row's validation status, source priority, source type, etc.")
        print(f"\n5. Quick Scripts:")
        print(f"   - python find_verification_details.py  # This script")
        print(f"   - python check_source_validation.py    # See latest row-by-row details")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    stage_id = "517a7cf8-2eda-4b9e-9284-27a41b4c935a"
    asyncio.run(find_verification_details(stage_id))
