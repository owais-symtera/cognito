"""Check detailed validation results"""
import asyncio
import asyncpg
import json

async def check_validation_details():
    """Check detailed validation results for the latest request"""
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

        print(f"\n{'='*80}")
        print(f"LATEST REQUEST")
        print(f"{'='*80}")
        print(f"Request ID: {latest_request['id']}")
        print(f"Drug: {latest_request['drug_name']}")
        print(f"Status: {latest_request['status']}")
        print(f"Created: {latest_request['created_at']}")

        # Get category results for this request
        category_results = await conn.fetch("""
            SELECT id, category_id, category_name, summary,
                   confidence_score, data_quality_score, status
            FROM category_results
            WHERE request_id = $1
            ORDER BY id DESC
        """, latest_request['id'])

        print(f"\n{'='*80}")
        print(f"CATEGORY RESULTS ({len(category_results)} categories)")
        print(f"{'='*80}")

        for i, cat_result in enumerate(category_results, 1):
            print(f"\n[{i}] Category: {cat_result['category_name']}")
            print(f"    Category Result ID: {cat_result['id']}")
            print(f"    Status: {cat_result['status']}")
            print(f"    Confidence: {cat_result['confidence_score']}")
            print(f"    Quality: {cat_result['data_quality_score']}")
            print(f"    Summary Length: {len(cat_result['summary'])} chars")

            # Get validation results for this category
            validation_results = await conn.fetch("""
                SELECT
                    id, validation_passed, validation_score,
                    confidence_penalty, step_results,
                    failed_steps, data_quality_issues,
                    recommendations, validated_at
                FROM validation_results
                WHERE category_result_id = $1
                ORDER BY validated_at DESC
            """, cat_result['id'])

            if validation_results:
                for j, val_result in enumerate(validation_results, 1):
                    print(f"\n    --- Validation Result #{j} ---")
                    print(f"    Validation ID: {val_result['id']}")
                    print(f"    Passed: {val_result['validation_passed']}")
                    print(f"    Score: {val_result['validation_score']}")
                    print(f"    Confidence Penalty: {val_result['confidence_penalty']}")
                    print(f"    Failed Steps: {val_result['failed_steps']}")
                    print(f"    Validated At: {val_result['validated_at']}")

                    print(f"\n    STEP RESULTS:")
                    step_results = val_result['step_results']
                    if isinstance(step_results, str):
                        step_results = json.loads(step_results)
                    for step in step_results:
                        status = "[PASS]" if step['passed'] else "[FAIL]"
                        print(f"      {status} | {step['step_name']}: {step['message']}")
                        print(f"           Score: {step['score']}")
                        if step.get('metadata'):
                            print(f"           Metadata: {json.dumps(step['metadata'], indent=18)}")

                    print(f"\n    DATA QUALITY ISSUES:")
                    quality_issues = val_result['data_quality_issues']
                    if isinstance(quality_issues, dict):
                        print(f"      Failed Steps Count: {quality_issues.get('failed_step_count', 0)}")
                        if quality_issues.get('issues'):
                            for issue in quality_issues['issues']:
                                print(f"      - Step: {issue['step']}")
                                print(f"        Message: {issue['message']}")
                                print(f"        Metadata: {json.dumps(issue.get('metadata', {}), indent=16)}")

                    print(f"\n    RECOMMENDATIONS:")
                    recommendations = val_result['recommendations']
                    if isinstance(recommendations, str):
                        recommendations = json.loads(recommendations)
                    for rec in recommendations:
                        print(f"      - {rec}")

            else:
                print(f"    [No validation results found]")

        # Check if merging happened
        print(f"\n{'='*80}")
        print(f"MERGED DATA")
        print(f"{'='*80}")

        merged_count = await conn.fetchval("""
            SELECT COUNT(*) FROM merged_data_results
            WHERE request_id = $1
        """, latest_request['id'])

        print(f"Merged results count: {merged_count}")

        if merged_count > 0:
            merged_results = await conn.fetch("""
                SELECT
                    id, category_name, merge_method,
                    merge_confidence_score, data_quality_score,
                    sources_merged, conflicts_resolved,
                    key_findings, llm_model, llm_tokens_used,
                    llm_cost_estimate
                FROM merged_data_results
                WHERE request_id = $1
            """, latest_request['id'])

            for merged in merged_results:
                print(f"\nCategory: {merged['category_name']}")
                print(f"  Merge Method: {merged['merge_method']}")
                print(f"  Confidence: {merged['merge_confidence_score']}")
                print(f"  Quality: {merged['data_quality_score']}")
                print(f"  Sources Merged: {merged['sources_merged']}")
                print(f"  Conflicts Resolved: {len(merged['conflicts_resolved']) if merged['conflicts_resolved'] else 0}")
                print(f"  Key Findings: {len(merged['key_findings']) if merged['key_findings'] else 0}")
                if merged['llm_model']:
                    print(f"  LLM Model: {merged['llm_model']}")
                    print(f"  LLM Tokens: {merged['llm_tokens_used']}")
                    print(f"  LLM Cost: ${merged['llm_cost_estimate']:.6f}")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_validation_details())
