"""
Test API calls to all enabled providers with competitive landscape prompt.
This script tests OpenAI, Perplexity, and Tavily APIs with a real pharmaceutical prompt.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend src to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import provider service
from src.services.provider_service import ProviderService


async def test_providers():
    """Test all enabled providers with competitive landscape prompt."""

    # Fix the provider config path before initializing
    import src.services.provider_service as ps_module
    ps_module.ProviderService.CONFIG_FILE = Path(__file__).parent.parent / "apps" / "backend" / "provider_config.json"

    # Initialize provider service
    provider_service = ProviderService()

    # Debug: check what providers are configured
    print("\nDEBUG: Checking provider configuration...")
    print(f"Config file path: {provider_service.CONFIG_FILE}")
    print(f"Number of providers: {len(provider_service.config)}")
    for pid, config in provider_service.config.items():
        print(f"  - {pid}: enabled={config.get('enabled')}, has_key={bool(config.get('api_key'))}")

    # Read the prompt template
    prompt_path = Path(__file__).parent.parent / "docs" / "prompts" / "competitive_landscape.md"
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()

    # Test drug: Apixaban (Eliquis)
    drug_name = "apixaban"
    current_year = datetime.now().year
    last_year = current_year - 1

    # Format the prompt
    prompt = prompt_template.replace("{drug_name}", drug_name)
    prompt = prompt.replace("{current_year}", str(current_year))
    prompt = prompt.replace("{last_year}", str(last_year))

    print("=" * 80)
    print("TESTING API PROVIDERS WITH COMPETITIVE LANDSCAPE PROMPT")
    print("=" * 80)
    print(f"Drug: {drug_name}")
    print(f"Prompt length: {len(prompt)} characters")
    print("\n" + "=" * 80)

    # Track results
    results = {
        "successful": [],
        "failed": [],
        "responses": {}
    }

    # Test each enabled provider
    for provider_id, config in provider_service.config.items():
        if not config.get("enabled") or not config.get("api_key"):
            print(f"\n[SKIP] Skipping {config['name']} (not enabled or no API key)")
            continue

        print(f"\n[TEST] Testing {config['name']} ({provider_id})...")
        print(f"   Model: {config.get('model')}")
        print(f"   API Key: {'SET' if config.get('api_key') else 'MISSING'}")

        # Test with each enabled temperature
        temperatures = config.get("temperatures", [])
        enabled_temps = [t for t in temperatures if t.get("enabled")]

        if not enabled_temps:
            print("   No enabled temperatures!")
            continue

        provider_results = []

        for temp_config in enabled_temps:
            temp_value = temp_config["value"]
            temp_label = temp_config["label"]

            print(f"\n   Testing with {temp_label}...")

            try:
                # Call the provider with the prompt
                response = await provider_service.call_provider_with_prompt(
                    provider_id,
                    prompt,
                    temp_value
                )

                # Check if it's an error response
                if "error" in response.lower() or "not implemented" in response.lower():
                    print(f"   [ERROR] {response[:200]}")
                    provider_results.append({
                        "temperature": temp_label,
                        "status": "error",
                        "response": response
                    })
                else:
                    # Success!
                    print(f"   [SUCCESS] Response length: {len(response)} chars")
                    print(f"   Preview: {response[:300]}...")
                    provider_results.append({
                        "temperature": temp_label,
                        "status": "success",
                        "response": response
                    })

            except Exception as e:
                print(f"   [EXCEPTION] {str(e)}")
                provider_results.append({
                    "temperature": temp_label,
                    "status": "exception",
                    "error": str(e)
                })

        # Store results
        results["responses"][provider_id] = {
            "name": config["name"],
            "model": config.get("model"),
            "results": provider_results
        }

        # Track success/failure
        if any(r["status"] == "success" for r in provider_results):
            results["successful"].append(provider_id)
        else:
            results["failed"].append(provider_id)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\n[PASS] Successful providers ({len(results['successful'])}):")
    for pid in results["successful"]:
        provider_info = results["responses"][pid]
        print(f"   - {provider_info['name']} ({provider_info['model']})")
        successful_temps = [r for r in provider_info["results"] if r["status"] == "success"]
        for temp_result in successful_temps:
            print(f"     * {temp_result['temperature']}: {len(temp_result['response'])} chars")

    if results["failed"]:
        print(f"\n[FAIL] Failed providers ({len(results['failed'])}):")
        for pid in results["failed"]:
            provider_info = results["responses"][pid]
            print(f"   - {provider_info['name']} ({provider_info['model']})")
            for temp_result in provider_info["results"]:
                if temp_result["status"] == "error":
                    print(f"     * {temp_result['temperature']}: {temp_result['response'][:100]}")
                elif temp_result["status"] == "exception":
                    print(f"     * {temp_result['temperature']}: Exception - {temp_result['error'][:100]}")

    # Save detailed results to file
    output_file = Path(__file__).parent / "test_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("API PROVIDER TEST RESULTS\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Drug: {drug_name}\n")
        f.write("=" * 80 + "\n\n")

        for provider_id, provider_data in results["responses"].items():
            f.write(f"\n{provider_data['name']} ({provider_id})\n")
            f.write(f"Model: {provider_data['model']}\n")
            f.write("-" * 40 + "\n")

            for temp_result in provider_data["results"]:
                f.write(f"\nTemperature: {temp_result['temperature']}\n")
                f.write(f"Status: {temp_result['status']}\n")

                if temp_result["status"] == "success":
                    f.write(f"Response ({len(temp_result['response'])} chars):\n")
                    f.write(temp_result['response'][:2000])
                    if len(temp_result['response']) > 2000:
                        f.write("\n... (truncated)")
                    f.write("\n")
                elif temp_result["status"] == "error":
                    f.write(f"Error: {temp_result['response']}\n")
                else:
                    f.write(f"Exception: {temp_result.get('error', 'Unknown error')}\n")

            f.write("\n" + "=" * 80 + "\n")

    print(f"\n[FILE] Detailed results saved to: {output_file}")

    return results


if __name__ == "__main__":
    print("Starting API provider tests...")
    results = asyncio.run(test_providers())

    # Exit with appropriate code
    if results["failed"]:
        sys.exit(1)  # Exit with error if any providers failed
    else:
        sys.exit(0)  # Success