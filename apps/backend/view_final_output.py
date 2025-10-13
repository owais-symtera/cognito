import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    # Get the most recent completed request
    print("Finding most recent completed request...")
    request = await conn.fetchrow("""
        SELECT r.id, r.drug_name, r.delivery_method, r.status, r.created_at
        FROM drug_requests r
        WHERE r.status = 'completed'
        ORDER BY r.created_at DESC
        LIMIT 1
    """)

    if not request:
        print("No completed requests found.")
        await conn.close()
        return

    request_id = str(request['id'])
    print(f"\nRequest: {request['drug_name']} ({request['delivery_method']})")
    print(f"Request ID: {request_id}")
    print(f"Status: {request['status']}")
    print(f"Created: {request['created_at']}")
    print("\n" + "="*80)

    # Check if final output exists
    final_output_row = await conn.fetchrow("""
        SELECT
            final_output,
            overall_td_score,
            overall_tm_score,
            td_verdict,
            tm_verdict,
            go_decision,
            investment_priority,
            risk_level,
            created_at
        FROM request_final_output
        WHERE request_id = $1
    """, request_id)

    if final_output_row:
        print("\n✓ FINAL OUTPUT FOUND")
        print("="*80)
        print(f"TD Score: {final_output_row['overall_td_score']}")
        print(f"TM Score: {final_output_row['overall_tm_score']}")
        print(f"TD Verdict: {final_output_row['td_verdict']}")
        print(f"TM Verdict: {final_output_row['tm_verdict']}")
        print(f"GO Decision: {final_output_row['go_decision']}")
        print(f"Investment Priority: {final_output_row['investment_priority']}")
        print(f"Risk Level: {final_output_row['risk_level']}")
        print(f"Generated: {final_output_row['created_at']}")

        # Get the full JSON structure
        final_output_json = final_output_row['final_output']

        print("\n" + "="*80)
        print("FINAL OUTPUT STRUCTURE:")
        print("="*80)

        if isinstance(final_output_json, dict):
            structured_data = final_output_json.get('structured_data', {})
            print(f"\nTop-level sections ({len(structured_data)} total):")
            for key in structured_data.keys():
                print(f"  - {key}")

            # Show executive summary
            if 'executive_summary_and_decision' in structured_data:
                print("\n" + "="*80)
                print("EXECUTIVE SUMMARY & DECISION:")
                print("="*80)
                exec_summary = structured_data['executive_summary_and_decision']
                print(json.dumps(exec_summary, indent=2))

            # Show suitability matrix summary
            if 'suitability_matrix' in structured_data:
                print("\n" + "="*80)
                print("SUITABILITY MATRIX (Summary):")
                print("="*80)
                matrix = structured_data['suitability_matrix']
                print(f"Summary: {matrix.get('summary', 'N/A')[:200]}...")

                if 'final_weighted_scores' in matrix:
                    print("\nFinal Weighted Scores:")
                    print(json.dumps(matrix['final_weighted_scores'], indent=2))

                if 'delivery_route_feasibility_assessment' in matrix:
                    print("\nDelivery Route Feasibility:")
                    for route in matrix['delivery_route_feasibility_assessment']:
                        print(f"\n  {route['route']}:")
                        print(f"    Score: {route['total_score']}/{route['max_possible']} ({route['percentage']})")
                        print(f"    Verdict: {route['cognito_verdict']}")
                        print(f"    Priority: {route['development_priority']}")

            # Show data coverage
            if 'data_coverage_scorecard' in structured_data:
                print("\n" + "="*80)
                print("DATA COVERAGE SCORECARD:")
                print("="*80)
                coverage = structured_data['data_coverage_scorecard']
                print(f"Summary: {coverage.get('summary', 'N/A')}")
                print(f"\nCategories covered: {len(coverage.get('data', []))}")

            # Show recommendations summary
            if 'recommendations' in structured_data:
                print("\n" + "="*80)
                print("RECOMMENDATIONS:")
                print("="*80)
                recs = structured_data['recommendations']
                print(f"Summary: {recs.get('summary', 'N/A')}")
                print(f"\nTotal recommendations: {len(recs.get('data', []))}")
                for i, rec in enumerate(recs.get('data', [])[:3], 1):
                    print(f"\n{i}. {rec.get('recommendation', 'N/A')}")
                    print(f"   Timeline: {rec.get('timeline', 'N/A')}")
                    print(f"   Owner: {rec.get('owner', 'N/A')}")

        print("\n" + "="*80)
        print("\nFull JSON saved to: final_output.json")

        # Save to file
        with open('final_output.json', 'w', encoding='utf-8') as f:
            json.dump(final_output_json, f, indent=2, ensure_ascii=False)

    else:
        print("\n✗ NO FINAL OUTPUT FOUND")
        print("The final output has not been generated yet for this request.")
        print("\nChecking Phase 2 results...")

        # Check phase2_results
        phase2_results = await conn.fetch("""
            SELECT parameter_name, extracted_value, score, weighted_score, unit
            FROM phase2_results
            WHERE request_id = $1
            ORDER BY
                CASE parameter_name
                    WHEN 'Dose' THEN 1
                    WHEN 'Molecular Weight' THEN 2
                    WHEN 'Melting Point' THEN 3
                    WHEN 'Log P' THEN 4
                END
        """, request_id)

        if phase2_results:
            print("\nPhase 2 Parameter Scoring Results:")
            print("="*80)
            for row in phase2_results:
                value = f"{row['extracted_value']} {row['unit']}" if row['extracted_value'] else "N/A"
                print(f"  {row['parameter_name']}: {value} → Score: {row['score']}, Weighted: {row['weighted_score']}")
        else:
            print("\nNo Phase 2 results found.")

    await conn.close()

asyncio.run(main())
