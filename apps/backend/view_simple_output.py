import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    print("="*80)
    print("FINAL OUTPUT SUMMARY")
    print("="*80)

    # Check latest final outputs
    outputs = await conn.fetch("""
        SELECT
            request_id,
            drug_name,
            overall_td_score,
            overall_tm_score,
            td_verdict,
            tm_verdict,
            go_decision,
            investment_priority,
            risk_level,
            created_at
        FROM request_final_output
        ORDER BY created_at DESC
        LIMIT 3
    """)

    if not outputs:
        print("\nNo final outputs found in database yet.")
        print("\nTo generate final output, the following must complete:")
        print("  1. All Phase 1 categories must finish")
        print("  2. Parameter-Based Scoring Matrix (Phase 2) must complete")
        print("  3. FinalOutputGenerator will automatically run")
    else:
        for i, output in enumerate(outputs, 1):
            print(f"\n{i}. Request ID: {output['request_id']}")
            print(f"   Drug: {output['drug_name']}")
            print(f"   TD Score: {output['overall_td_score']:.2f}/9 ({output['td_verdict']})")
            print(f"   TM Score: {output['overall_tm_score']:.2f}/9 ({output['tm_verdict']})")
            print(f"   GO Decision: {output['go_decision']}")
            print(f"   Investment Priority: {output['investment_priority']}")
            print(f"   Risk Level: {output['risk_level']}")
            print(f"   Generated: {output['created_at']}")

        print("\n" + "="*80)
        print("ACCESSING FULL JSON OUTPUT:")
        print("="*80)
        print(f"\nAPI Endpoint:")
        print(f"  GET http://localhost:8001/api/v1/results/{{request_id}}")
        print(f"\nExample:")
        print(f"  curl http://localhost:8001/api/v1/results/{outputs[0]['request_id']}")

        print(f"\n\nOr check the database directly:")
        print(f"  SELECT final_output FROM request_final_output WHERE request_id = '{outputs[0]['request_id']}';")

    await conn.close()

asyncio.run(main())
