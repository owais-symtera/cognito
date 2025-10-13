"""Update provider configuration to use GPT-4o instead of GPT-5."""

import json
from pathlib import Path

config_path = Path(__file__).parent.parent / "apps" / "backend" / "provider_config.json"

# Read the configuration
with open(config_path, 'r') as f:
    config = json.load(f)

# Update OpenAI model from GPT-5 to GPT-4o
if config.get('openai', {}).get('model') == 'gpt-5':
    config['openai']['model'] = 'gpt-4o'
    print(f"Updated OpenAI model from gpt-5 to gpt-4o")

# Save the updated configuration
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    print("Configuration saved successfully!")

print(f"OpenAI model is now: {config['openai']['model']}")