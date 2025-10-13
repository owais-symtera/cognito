"""
Debug OpenAI API calls to understand why they're failing.
"""

import asyncio
import aiohttp
import os
import sys
from pathlib import Path

# Add backend src to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def test_openai_direct():
    """Test OpenAI API directly with detailed error handling."""

    # Read the provider config
    config_path = Path(__file__).parent.parent / "apps" / "backend" / "provider_config.json"
    import json

    with open(config_path, 'r') as f:
        config = json.load(f)

    openai_config = config['openai']
    api_key = openai_config['api_key']

    if not api_key:
        print("ERROR: No API key found for OpenAI")
        return

    print(f"API Key (first 10 chars): {api_key[:10]}...")
    print(f"Model: {openai_config.get('model', 'gpt-4o')}")

    # Test with GPT-4 first to verify API key
    model = 'gpt-4o'  # Force GPT-4 for testing
    is_gpt5 = False  # Disable GPT-5 for now

    print(f"\nTesting with model: {model}")
    print(f"Is GPT-5: {is_gpt5}")

    if is_gpt5:
        print("\nTesting GPT-5 with Responses API...")

        actual_model = "gpt-5-nano" if model == "gpt-5" else model

        payload = {
            "model": actual_model,
            "tools": [{
                "type": "web_search",
                "filters": {
                    "allowed_domains": [
                        "pubmed.ncbi.nlm.nih.gov",
                        "clinicaltrials.gov",
                        "www.who.int",
                        "www.cdc.gov",
                        "www.fda.gov"
                    ]
                }
            }],
            "tool_choice": "auto",
            "input": "Search for information about the drug apixaban."
        }

        endpoint = "https://api.openai.com/v1/responses"

        print(f"Endpoint: {endpoint}")
        print(f"Payload model: {actual_model}")
    else:
        print("\nTesting standard model with Chat Completions API...")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a pharmaceutical expert."},
                {"role": "user", "content": "What is apixaban?"}
            ],
            "max_tokens": 50
        }

        endpoint = "https://api.openai.com/v1/chat/completions"

        print(f"Endpoint: {endpoint}")
        print(f"Payload model: {model}")

    # Make the API call
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            print("\nMaking API call...")

            async with session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                print(f"Response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"Success! Response keys: {data.keys()}")

                    if is_gpt5:
                        if "output" in data:
                            print(f"GPT-5 Output: {data['output'][:200]}...")
                        elif "content" in data:
                            print(f"GPT-5 Content: {data['content'][:200]}...")
                        else:
                            print(f"Unexpected GPT-5 response format: {str(data)[:200]}...")
                    else:
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"]["content"]
                            print(f"Response: {content[:200]}...")
                        else:
                            print(f"Unexpected response format: {str(data)[:200]}...")
                else:
                    error_text = await response.text()
                    print(f"ERROR {response.status}: {error_text}")

    except asyncio.TimeoutError:
        print("ERROR: Request timed out after 30 seconds")
    except aiohttp.ClientError as e:
        print(f"ERROR: Client error - {str(e)}")
    except Exception as e:
        print(f"ERROR: Unexpected error - {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing OpenAI API directly...")
    print("=" * 60)
    asyncio.run(test_openai_direct())