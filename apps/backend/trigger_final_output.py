"""
Manually trigger final output generation for a completed request
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from src.services.final_output_generator import FinalOutputGenerator

async def main():
    request_id = 'b50afec4-bf1e-415f-a95b-7707595ed8ab'

    print(f"Triggering final output generation for request: {request_id}")
    print("="*80)

    generator = FinalOutputGenerator()

    try:
        final_output = await generator.generate_final_output(request_id)
        print("\n✓ Final output generated successfully!")
        print(f"\nRequest ID: {final_output['request_id']}")
        print(f"Webhook Type: {final_output['webhookType']}")
        print(f"\nStructured data sections: {len(final_output['structured_data'])}")
        print("\nTop-level sections:")
        for key in final_output['structured_data'].keys():
            print(f"  - {key}")

        # Show executive summary decision
        exec_summary = final_output['structured_data'].get('executive_summary_and_decision', {})
        if exec_summary:
            print(f"\nDecision: {exec_summary.get('decision', 'N/A')}")
            print(f"Investment Priority: {exec_summary.get('investment_priority', 'N/A')}")
            print(f"Risk Level: {exec_summary.get('risk_level', 'N/A')}")

        print("\n✓ Final output stored to database successfully!")

    except Exception as e:
        print(f"\n✗ Failed to generate final output: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
