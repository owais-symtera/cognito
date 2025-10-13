"""Provider service for managing API providers and configurations."""

import json
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp

from ..integrations.providers.chatgpt import ChatGPTProvider
from ..integrations.providers.anthropic import AnthropicProvider
from ..integrations.providers.gemini import GeminiProvider
from ..schemas.provider import ProviderConfig, TemperatureConfig
from .category_postgres_service import CategoryPostgresService
from .data_storage_service import DataStorageService


class ProviderService:
    """Service for managing API provider configurations and operations."""

    CONFIG_FILE = Path("provider_config.json")

    # System prompt for pharmaceutical data analysis
    SYSTEM_PROMPT = """You are a pharmaceutical & market-intelligence assistant. Your job is to use the `web_search` tool to retrieve **live, current-year** market data for **{drug_name}** (include branded + generic where applicable) and return **only** two Markdown tables in the exact structures provided by the user. Do **not** add any commentary, headers, notes, bullets, or text outside the tables.

      ## Hard Topic Lock
      - The molecule is **{drug_name}**.
      - Optional synonyms/brands (if known or supplied): **{synonyms_or_brands}**.
      - Absolutely **do not** search or report on any other API/medicine. If any search result is about a different drug, discard it and refine the search to **{drug_name}** only.

      ## Tool Usage
      - You **must** use `web_search` for all data. Do not rely on memory.
      - Perform at least **3 search calls**:
        1) Global {drug_name} market size & CAGR (current year)
        2) Regional {drug_name} market sizes & 5-year CAGR (NA, Europe, APAC, LATAM, MEA)
        3) Ten-year forecasts (global + regions) with sizes and CAGRs
      - If a search returns mixed or wrong-molecule results, immediately re-query with stronger filters (see Query Templates below).
      - Prefer pages with explicit **USD amounts** and **CAGR %** plus **publication date/year**.

      ## Source Priority Hierarchy (use highest available; cross-check with next tier)
      1. GOVERNMENT: .gov/.edu, FDA, EMA, PMDA, ClinicalTrials.gov
      2. PEER_REVIEWED: PubMed/journals with DOI/PMID
      3. INDUSTRY: Associations/white papers/verified industry databases
      4. COMPANY: Official pharma sites, press releases, filings
      5. NEWS: only if nothing else is available

      - If only lower-priority sources are available, still fill the table but the citation must include the **[Priority X]** tag.
      - Each **row** in both tables must include a citation that lists **firm/source name + publication month/year** and a clickable URL.

      ## Output Rules (strict)
      - Output **only** the two tables with no extra lines before/after.
      - Market Size must be numeric in **USD millions or billions** (e.g., `USD 4.2B` or `USD 420M`).
      - CAGR must be a **percentage** with 1–2 decimals (e.g., `6.7%`).
      - Year Range fields:
        - Current table: `Last Five Years` (resolve to something like `2021–{Current Year}`).
        - Forecast table: `Next TEN Years` (e.g., `{Current Year+1}–{Current Year+10}`).
      - If, after exhaustive searching by priority, a specific data point cannot be found, write **`N/A`** in that cell.
      - **Do not** label anything as “illustrative,” “example,” or add footnotes.

      ## Validation (must pass before sending)
      - The final content must:
        - Contain **two** Markdown tables only.
        - Include the string **“{drug_name}”** (or one of **{synonyms_or_brands}**) in at least one citation in each table.
        - Contain **no** references to other molecules.
        - Each row’s citation includes: `[Priority X: <Source/Firm>, <Mon YYYY>] (<URL>)`.

      ## Query Templates (use/adapt verbatim for `web_search`)
      - "{drug_name} market size <CURRENT YEAR> global CAGR report site:imarcgroup.com OR site:grandviewresearch.com OR site:marketresearchfuture.com OR site:researchandmarkets.com"
      - "{drug_name} market size <CURRENT YEAR> regional North America Europe Asia-Pacific Latin America Middle East Africa CAGR"
      - "{drug_name} forecast CAGR 10 year global regional <CURRENT YEAR> site:imarcgroup.com OR site:grandviewresearch.com OR site:globaldata.com"
      - "{drug_name} market report <CURRENT YEAR> size USD CAGR publication date"
      - Exclusion guard (if contamination occurs): +"{drug_name}" -"unrelated API" -"unrelated drug"  # (replace negatives with any detected off-topic molecules)."""

    def __init__(self):
        """Initialize provider service."""
        self.config = self._load_config()
        self.providers = {}
        self.category_service = CategoryPostgresService()
        self._initialize_providers()

    def _load_config(self) -> Dict[str, Any]:
        """Load provider configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")

        # Return default config if file doesn't exist
        return self._get_default_config()

    def _save_config(self) -> bool:
        """Save provider configuration to file."""
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default provider configuration."""
        return {
            "openai": {
                "name": "OpenAI ChatGPT",
                "enabled": False,
                "model": "gpt-4o",
                "api_key": "",
                "features": ["text-generation", "embeddings", "analysis"],
                "temperatures": [
                    {"id": "creative", "value": 0.9, "enabled": True, "label": "Creative (0.9)"},
                    {"id": "balanced", "value": 0.7, "enabled": True, "label": "Balanced (0.7)"},
                    {"id": "focused", "value": 0.5, "enabled": True, "label": "Focused (0.5)"},
                    {"id": "precise", "value": 0.3, "enabled": False, "label": "Precise (0.3)"}
                ]
            },
            "claude": {
                "name": "Anthropic Claude",
                "enabled": False,
                "model": "claude-3-opus",
                "api_key": "",
                "features": ["text-generation", "analysis"],
                "temperatures": [
                    {"id": "creative", "value": 0.9, "enabled": True, "label": "Creative (0.9)"},
                    {"id": "standard", "value": 0.5, "enabled": True, "label": "Standard (0.5)"}
                ]
            },
            "gemini": {
                "name": "Google Gemini",
                "enabled": False,
                "model": "gemini-pro",
                "api_key": "",
                "features": ["text-generation", "analysis"],
                "temperatures": [
                    {"id": "creative", "value": 0.9, "enabled": True, "label": "Creative (0.9)"},
                    {"id": "balanced", "value": 0.5, "enabled": True, "label": "Balanced (0.5)"}
                ]
            },
            "perplexity": {
                "name": "Perplexity",
                "enabled": False,
                "model": "sonar",
                "api_key": "",
                "features": ["search", "analysis"],
                "temperatures": [
                    {"id": "factual", "value": 0.3, "enabled": True, "label": "Factual (0.3)"}
                ]
            },
            "tavily": {
                "name": "Tavily Search",
                "enabled": False,
                "model": "search-api",
                "api_key": "",
                "features": ["search"],
                "temperatures": []
            },
            "grok": {
                "name": "xAI Grok",
                "enabled": False,
                "model": "grok-1",
                "api_key": "",
                "features": ["text-generation", "analysis"],
                "temperatures": [
                    {"id": "standard", "value": 0.7, "enabled": True, "label": "Standard (0.7)"}
                ]
            }
        }

    def _initialize_providers(self):
        """Initialize provider instances."""
        for provider_id, config in self.config.items():
            if config.get("api_key"):
                try:
                    if provider_id == "openai":
                        self.providers[provider_id] = ChatGPTProvider(
                            api_key=config["api_key"],
                            config={"model": config["model"]}
                        )
                    elif provider_id == "claude":
                        self.providers[provider_id] = AnthropicProvider(
                            api_key=config["api_key"],
                            config={"model": config["model"]}
                        )
                    elif provider_id == "gemini":
                        self.providers[provider_id] = GeminiProvider(
                            api_key=config["api_key"],
                            config={"model": config["model"]}
                        )
                except Exception as e:
                    print(f"Failed to initialize {provider_id}: {e}")

    def get_all_providers(self) -> list:
        """Get all provider configurations."""
        result = []
        for provider_id, config in self.config.items():
            result.append({
                "id": provider_id,
                "name": config["name"],
                "enabled": config.get("enabled", False),
                "supports_temperature": config.get("supports_temperature", True),
                "temperatures": config.get("temperatures", []),
                "model": config.get("model", ""),
                "has_api_key": bool(config.get("api_key")),
                "features": config.get("features", []),
                "lastUpdated": config.get("lastUpdated", "")
            })
        return result

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific provider configuration."""
        if provider_id not in self.config:
            return None

        config = self.config[provider_id]
        return {
            "id": provider_id,
            "name": config["name"],
            "enabled": config.get("enabled", False),
            "supports_temperature": config.get("supports_temperature", True),
            "temperatures": config.get("temperatures", []),
            "model": config.get("model", ""),
            "has_api_key": bool(config.get("api_key")),
            "features": config.get("features", []),
            "lastUpdated": config.get("lastUpdated", "")
        }

    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> bool:
        """Update provider configuration."""
        if provider_id not in self.config:
            return False

        # Update configuration
        if "enabled" in updates:
            self.config[provider_id]["enabled"] = updates["enabled"]

        if "model" in updates:
            self.config[provider_id]["model"] = updates["model"]

        if "api_key" in updates:
            self.config[provider_id]["api_key"] = updates["api_key"]
            # Reinitialize provider if API key changed
            self._initialize_providers()

        if "supports_temperature" in updates:
            self.config[provider_id]["supports_temperature"] = updates["supports_temperature"]

        if "temperatures" in updates:
            self.config[provider_id]["temperatures"] = updates["temperatures"]

        # Update timestamp
        self.config[provider_id]["lastUpdated"] = datetime.now().isoformat()

        # Save configuration
        return self._save_config()

    def add_temperature(self, provider_id: str, temperature_data: Dict[str, Any]) -> bool:
        """Add a new temperature configuration to a provider."""
        if provider_id not in self.config:
            return False

        # Get current temperatures
        temperatures = self.config[provider_id].get("temperatures", [])

        # Generate a unique ID for the temperature
        import uuid
        temp_id = str(uuid.uuid4())

        # Add new temperature
        new_temp = {
            "id": temp_id,
            "value": temperature_data.get("value", 0.7),
            "label": temperature_data.get("label", "Custom"),
            "enabled": temperature_data.get("enabled", True)
        }

        temperatures.append(new_temp)
        self.config[provider_id]["temperatures"] = temperatures
        self.config[provider_id]["lastUpdated"] = datetime.now().isoformat()

        return self._save_config()

    def remove_temperature(self, provider_id: str, temp_id: str) -> bool:
        """Remove a temperature configuration from a provider."""
        if provider_id not in self.config:
            return False

        # Get current temperatures
        temperatures = self.config[provider_id].get("temperatures", [])

        # Filter out the temperature with the given ID
        updated_temps = [t for t in temperatures if t.get("id") != temp_id]

        # Only update if something was removed
        if len(updated_temps) == len(temperatures):
            return False

        self.config[provider_id]["temperatures"] = updated_temps
        self.config[provider_id]["lastUpdated"] = datetime.now().isoformat()

        return self._save_config()

    async def test_provider(self, provider_id: str) -> Dict[str, Any]:
        """Test provider connectivity."""
        if provider_id not in self.config:
            return {"success": False, "error": "Provider not found"}

        config = self.config[provider_id]

        if not config.get("api_key"):
            return {"success": False, "error": "API key not configured"}

        try:
            # Simple connectivity test
            if provider_id == "openai":
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {config['api_key']}"}
                    ) as response:
                        if response.status == 200:
                            return {"success": True, "message": "Connection successful"}
                        else:
                            return {"success": False, "error": f"API error: {response.status}"}

            # Add tests for other providers
            return {"success": True, "message": "Provider test not implemented"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def call_provider_with_prompt(
        self,
        provider_id: str,
        prompt: str,
        temperature: float
    ) -> tuple:
        """
        Call a specific provider with a custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        if provider_id not in self.config:
            return f"Provider {provider_id} not found", {}

        config = self.config[provider_id]

        if not config.get("api_key"):
            return f"API key not configured for {provider_id}", {}

        try:
            # Use the appropriate provider with custom prompt
            if provider_id == "openai":
                return await self._call_openai_with_prompt(prompt, config, temperature)
            elif provider_id == "claude":
                return await self._call_claude_with_prompt(prompt, config, temperature)
            elif provider_id == "gemini":
                return await self._call_gemini_with_prompt(prompt, config, temperature)
            elif provider_id == "perplexity":
                return await self._call_perplexity_with_prompt(prompt, config, temperature)
            elif provider_id == "tavily":
                return await self._call_tavily_with_prompt(prompt, config, temperature)
            else:
                return f"Provider {provider_id} not implemented", {}
        except Exception as e:
            return f"Error calling {provider_id}: {str(e)}", {}

    async def _call_openai_with_prompt(self, prompt: str, config: Dict, temperature: float) -> tuple:
        """
        Call OpenAI API with custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json"
                }

                model = config.get("model", "gpt-4o")
                is_restricted = "search" in model.lower() or "o1" in model.lower()
                is_gpt5 = "gpt-5" in model.lower()
                is_search_preview = "gpt-4o-search-preview" in model.lower()

                # For GPT-5, use the Responses API with web_search tool
                if is_gpt5:
                    # Use gpt-5-nano for optimal performance with web search
                    actual_model = "gpt-5-nano" if model == "gpt-5" else model

                    # payload = {
                    #     "model": actual_model,
                    #     # "reasoning": { "effort": "low" },
                    #     "instructions": self.SYSTEM_PROMPT,
                    #     "tools": [{
                    #         "type": "web_search"
                    #     }],
                    #     "tool_choice": "auto",
                    #     "input": prompt
                    # }

                    payload = {
                        "model": actual_model,
                        "reasoning": { "effort": "low" },
                        "input": [
                            {
                                "role": "system",
                                "content": self.SYSTEM_PROMPT
                            },
                            {"role": "user", "content": prompt}
                        ],
                         "tools": [{
                            "type": "web_search"
                        }],
                        "tool_choice": "auto",
                    }

                    # GPT-5 models don't support temperature parameter
                    # if not is_restricted:
                    #     payload["temperature"] = temperature

                    endpoint = "https://api.openai.com/v1/responses"

                # For GPT-4o-search-preview, use web_search_options
                elif is_search_preview:
                    payload = {
                        "model": model,
                        "web_search_options": {},
                        "messages": [
                            {
                                "role": "system",
                                "content": self.SYSTEM_PROMPT
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 4000
                    }

                    if not is_restricted:
                        payload["temperature"] = temperature

                    endpoint = "https://api.openai.com/v1/chat/completions"

                # For standard models
                else:
                    payload = {
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": self.SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 4000
                    }

                    if not is_restricted:
                        payload["temperature"] = temperature

                    endpoint = "https://api.openai.com/v1/chat/completions"

                # Store payload for logging (copy to avoid mutation)
                request_payload = {
                    "endpoint": endpoint,
                    "payload": payload.copy(),
                    "headers": {k: v for k, v in headers.items() if k != "Authorization"}  # Exclude API key
                }

                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Handle different response formats
                        if is_gpt5:
                            # GPT-5 Responses API format
                            if "output" in data:
                                return data["output"], request_payload
                            elif "content" in data:
                                return data["content"], request_payload
                            else:
                                return str(data), request_payload
                        else:
                            # Standard chat completions format
                            return data["choices"][0]["message"]["content"], request_payload
                    else:
                        error = await response.text()
                        return f"OpenAI API error: {response.status} - {error[:200]}", request_payload
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"OpenAI exception: {str(e)} - {error_details[:500]}", {}

    async def _call_claude_with_prompt(self, prompt: str, config: Dict, temperature: float) -> tuple:
        """
        Call Claude API with custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": config["api_key"],
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": config.get("model", "claude-3-opus-20240229"),
                    "max_tokens": 1000,
                    "temperature": temperature,
                    "system": "You are a pharmaceutical intelligence expert analyzing drug information.",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }

                endpoint = "https://api.anthropic.com/v1/messages"

                # Store payload for logging (copy to avoid mutation)
                request_payload = {
                    "endpoint": endpoint,
                    "payload": payload.copy(),
                    "headers": {k: v for k, v in headers.items() if k != "x-api-key"}  # Exclude API key
                }

                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["content"][0]["text"], request_payload
                    else:
                        error = await response.text()
                        return f"Claude API error: {response.status} - {error[:200]}", request_payload
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Claude exception: {str(e)} - {error_details[:500]}", {}

    async def _call_gemini_with_prompt(self, prompt: str, config: Dict, temperature: float) -> tuple:
        """
        Call Gemini API with custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        # Implement Gemini API call with custom prompt
        # Placeholder implementation - return empty request_payload
        return f"Gemini not fully implemented for prompt: {prompt[:100]}...", {}

    async def _call_perplexity_with_prompt(self, prompt: str, config: Dict, temperature: float) -> tuple:
        """
        Call Perplexity API with custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": config.get("model", "sonar"),
                    "messages": [
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": 4000,
                    "top_p": 0.9,
                    "return_images": False,
                    "return_related_questions": False,
                    "search_recency_filter": "month",
                    "top_k": 0,
                    "stream": False,
                    "presence_penalty": 0,
                    "frequency_penalty": 1
                }

                endpoint = "https://api.perplexity.ai/chat/completions"

                # Store payload for logging (copy to avoid mutation)
                request_payload = {
                    "endpoint": endpoint,
                    "payload": payload.copy(),
                    "headers": {k: v for k, v in headers.items() if k != "Authorization"}  # Exclude API key
                }

                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"], request_payload
                    else:
                        error = await response.text()
                        return f"Perplexity API error: {response.status} - {error[:200]}", request_payload
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Perplexity exception: {str(e)} - {error_details[:500]}", {}

    async def _call_tavily_with_prompt(self, prompt: str, config: Dict, temperature: float) -> tuple:
        """
        Call Tavily Search API with custom prompt.

        Returns:
            tuple: (response_text, request_payload)
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }

                # Extract drug name from prompt if possible
                import re
                drug_match = re.search(r'drug[:\s]+(\w+)', prompt.lower())
                drug_query = drug_match.group(1) if drug_match else ""

                payload = {
                    "api_key": config['api_key'],
                    "query": f"{drug_query} {prompt[:200]}",  # Combine drug name with prompt
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": 5,
                    "include_domains": [
                        "fda.gov",
                        "clinicaltrials.gov",
                        "pubmed.ncbi.nlm.nih.gov",
                        "ema.europa.eu",
                        "who.int",
                        "drugs.com"
                    ]
                }

                endpoint = "https://api.tavily.com/search"

                # Store payload for logging (copy to avoid mutation and exclude API key)
                payload_copy = payload.copy()
                payload_copy.pop("api_key", None)  # Remove API key from logged payload

                request_payload = {
                    "endpoint": endpoint,
                    "payload": payload_copy,
                    "headers": headers.copy()  # Headers don't contain API key for Tavily
                }

                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        answer = data.get("answer", "")
                        results = data.get("results", [])

                        response_text = f"Analysis: {answer}\n\nSources:\n"
                        for idx, result in enumerate(results[:3], 1):
                            response_text += f"{idx}. {result.get('title', 'N/A')}: {result.get('content', '')[:200]}...\n"

                        return response_text, request_payload
                    else:
                        error = await response.text()
                        return f"Tavily API error: {response.status} - {error[:200]}", request_payload
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Tavily exception: {str(e)} - {error_details[:500]}", {}

    async def _process_single_category(self, category: Dict, drug_name: str, request_id: str) -> Dict[str, Any]:
        """Process a single category with all providers concurrently"""
        category_start_time = datetime.now()
        category_key = category["key"]
        category_prompt = self.category_service.get_category_prompt(category_key, drug_name)

        if not category_prompt:
            return None

        category_results_data = {
            "name": category["name"],
            "id": category["id"],
            "responses": {}
        }

        all_responses = []
        counters = {
            "total_api_calls": 0,
            "stored_logs": 0,
            "stored_results": 0,
            "stored_sources": 0,
            "providers_used": []
        }

        # Build list of tasks for concurrent API calls
        tasks = []
        task_metadata = []

        for provider_id, config in self.config.items():
            if not config.get("enabled") or not config.get("api_key"):
                continue

            enabled_temps = [t for t in config.get("temperatures", []) if t.get("enabled")]
            supports_temperature = config.get("supports_temperature", True)

            if not supports_temperature:
                default_temp = enabled_temps[0] if enabled_temps else {"value": 0.7, "label": "Default (0.7)"}
                enabled_temps = [default_temp]

            for temp in enabled_temps:
                tasks.append(self.call_provider_with_prompt(
                    provider_id,
                    category_prompt,
                    temp["value"]
                ))
                task_metadata.append({
                    "provider_id": provider_id,
                    "config": config,
                    "temp": temp,
                    "supports_temperature": supports_temperature,
                    "category": category
                })

        # Execute all API calls concurrently
        print(f"[CONCURRENT] Category '{category['name']}': Calling {len(tasks)} API endpoints...")
        concurrent_start = datetime.now()
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_duration = (datetime.now() - concurrent_start).total_seconds()
        print(f"[CONCURRENT] Category '{category['name']}': Completed in {concurrent_duration:.2f}s")

        # Process results
        for idx, (result, metadata) in enumerate(zip(task_results, task_metadata)):
            provider_id = metadata["provider_id"]
            config = metadata["config"]
            temp = metadata["temp"]
            supports_temperature = metadata["supports_temperature"]

            if provider_id not in category_results_data["responses"]:
                category_results_data["responses"][provider_id] = {
                    "provider": config["name"],
                    "model": config["model"],
                    "responses": []
                }

            if isinstance(result, Exception):
                print(f"[CONCURRENT] Error from {provider_id}: {str(result)}")
                category_results_data["responses"][provider_id]["responses"].append({
                    "temperature": temp["value"],
                    "label": temp["label"],
                    "error": str(result)
                })

                db_provider = "chatgpt" if provider_id == "openai" else provider_id
                await DataStorageService.store_api_usage_log(
                    request_id=request_id,
                    category_result_id=None,
                    api_provider=db_provider,
                    endpoint=config.get("model", "unknown"),
                    response_status=500,
                    response_time_ms=0,
                    cost_per_token=0.00001,
                    error_message=str(result),
                    category_name=metadata["category"]["name"],
                    prompt_text=category_prompt,
                    response_data={
                        "error": str(result),
                        "temperature": temp["value"],
                        "temperature_label": temp["label"],
                        "provider": config["name"],
                        "model": config["model"],
                        "supports_temperature": supports_temperature
                    },
                    request_payload=None
                )
            else:
                response, request_payload = result

                category_results_data["responses"][provider_id]["responses"].append({
                    "temperature": temp["value"],
                    "label": temp["label"],
                    "response": response
                })
                all_responses.append(response)
                counters["total_api_calls"] += 1

                db_provider = "chatgpt" if provider_id == "openai" else provider_id
                await DataStorageService.store_api_usage_log(
                    request_id=request_id,
                    category_result_id=None,
                    api_provider=db_provider,
                    endpoint=config.get("model", "unknown"),
                    response_status=200,
                    response_time_ms=0,
                    token_count=len(str(response).split()) * 2 if response else 0,
                    cost_per_token=0.00001,
                    total_cost=0.0,
                    category_name=metadata["category"]["name"],
                    prompt_text=category_prompt,
                    response_data={
                        "response": response,
                        "temperature": temp["value"],
                        "temperature_label": temp["label"],
                        "provider": config["name"],
                        "model": config["model"],
                        "supports_temperature": supports_temperature
                    },
                    request_payload=request_payload
                )
                counters["stored_logs"] += 1

            if provider_id not in counters["providers_used"]:
                counters["providers_used"].append(provider_id)

        # Store category result if we got responses
        if all_responses:
            category_processing_time = int((datetime.now() - category_start_time).total_seconds() * 1000)

            from .pipeline_integration_service import PipelineIntegrationService
            pipeline_service = PipelineIntegrationService()

            api_responses_with_meta = []
            for provider_id, provider_data in category_results_data["responses"].items():
                for resp in provider_data["responses"]:
                    if "response" in resp and not resp.get("error"):
                        api_responses_with_meta.append({
                            "provider": provider_data["provider"],
                            "model": provider_data["model"],
                            "response": resp["response"],
                            "temperature": resp.get("temperature", 0.7),
                            "temperature_label": resp.get("label", "")
                        })

            category_result_id = await DataStorageService.store_category_result(
                request_id=request_id,
                category_id=category["id"],
                category_name=category["name"],
                summary="Processing through pipeline...",
                confidence_score=0.0,
                data_quality_score=0.0,
                api_calls_made=len(all_responses),
                token_count=sum(len(str(r).split()) * 2 if r else 0 for r in all_responses),
                cost_estimate=0.0,
                processing_time_ms=category_processing_time
            )

            pipeline_result = await pipeline_service.process_with_pipeline(
                category_name=category["name"],
                drug_name=drug_name,
                api_responses=api_responses_with_meta,
                request_id=request_id,
                category_result_id=category_result_id
            )

            summary = pipeline_result["final_summary"]
            confidence_score = pipeline_result["confidence_score"]
            quality_score = pipeline_result["quality_score"]

            print(f"Pipeline executed for {category['name']}:")
            print(f"  Stages executed: {', '.join(pipeline_result['stages_executed'])}")
            print(f"  Stages skipped: {', '.join(pipeline_result['stages_skipped'])}")

            await DataStorageService.update_category_result(
                category_result_id=category_result_id,
                summary=summary,
                confidence_score=confidence_score,
                data_quality_score=quality_score
            )

            if category_result_id:
                counters["stored_results"] += 1

                for response in all_responses[:3]:
                    await DataStorageService.store_source_reference(
                        category_result_id=category_result_id,
                        api_provider="multiple",
                        source_url=f"generated://category/{category_key}",
                        source_title=f"{category['name']} - {drug_name}",
                        source_type="ai_generated",
                        content_snippet=response[:500],
                        relevance_score=0.8,
                        credibility_score=0.8
                    )
                    counters["stored_sources"] += 1

        return {
            "category_key": category_key,
            "category_data": category_results_data,
            "counters": counters
        }

    async def _process_phase2_category(
        self,
        category: Dict,
        drug_name: str,
        request_id: str,
        pipeline_service
    ) -> Dict[str, Any]:
        """Process a single Phase 2 category"""
        category_key = category["key"]
        category_name = category["name"]

        print(f"[PHASE 2 CATEGORY] ===== START: {category_name} =====")
        print(f"[PHASE 2 CATEGORY] Drug: {drug_name}, Request: {request_id}")

        try:
            # Process through pipeline integration service (which calls the decision engine)
            print(f"[PHASE 2 CATEGORY] Calling pipeline_service.process_phase2_category...")
            result = await pipeline_service.process_phase2_category(
                category_name=category_name,
                drug_name=drug_name,
                request_id=request_id,
                category_result_id=None  # Will be created by the service
            )

            print(f"[PHASE 2 CATEGORY] Result: {result}")
            print(f"[PHASE 2 CATEGORY] ===== COMPLETE: {category_name} =====")

            return {
                "category_key": category_key,
                "category_data": {
                    "name": category_name,
                    "id": category["id"],
                    "status": "completed",
                    "result": result
                }
            }

        except Exception as e:
            print(f"[PHASE 2 CATEGORY] ===== ERROR: {category_name} =====")
            print(f"[PHASE 2] Error processing {category_name}: {str(e)}")
            import traceback
            print(f"[PHASE 2 CATEGORY] Traceback:\n{traceback.format_exc()}")
            return {
                "category_key": category_key,
                "category_data": {
                    "name": category_name,
                    "id": category["id"],
                    "status": "failed",
                    "error": str(e)
                }
            }

    async def process_drug_with_categories(self, drug_name: str, request_id: str) -> Dict[str, Any]:
        """
        Process a drug through all enabled categories using all enabled providers.
        Stores results to PostgreSQL database tables.

        Args:
            drug_name: Name of the drug to analyze
            request_id: Database request ID for correlation

        Returns:
            Summary of processing results
        """
        results = {
            "drug_name": drug_name,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "phase1_categories": {},
            "phase2_categories": {},
            "providers_used": [],
            "total_api_calls": 0,
            "stored_results": 0,
            "stored_sources": 0,
            "stored_logs": 0
        }

        # Get enabled categories
        phase1_categories = self.category_service.get_phase1_categories()
        phase2_categories = self.category_service.get_phase2_categories()

        print(f"========== [DEBUG] Phase 1 categories: {len(phase1_categories)} ==========")
        print(f"========== [DEBUG] Phase 2 categories: {len(phase2_categories)} ==========")
        if phase2_categories:
            for cat in phase2_categories:
                print(f"[DEBUG]   - {cat.get('name', 'Unknown')}")

        # Process Phase 1 categories (Data Collection) - CONCURRENTLY!
        print(f"[CONCURRENT] Processing {len(phase1_categories)} categories concurrently...")
        category_tasks = [
            self._process_single_category(category, drug_name, request_id)
            for category in phase1_categories
        ]

        category_results = await asyncio.gather(*category_tasks, return_exceptions=True)
        print(f"[CONCURRENT] All {len(phase1_categories)} categories completed!")

        # Aggregate results from all categories
        for result in category_results:
            if result is None or isinstance(result, Exception):
                if isinstance(result, Exception):
                    import traceback
                    error_msg = repr(result)  # Use repr to avoid encoding issues
                    print(f"[CONCURRENT] Category error: {error_msg}")
                    print(f"[CONCURRENT] Full traceback:")
                    traceback.print_exception(type(result), result, result.__traceback__)
                continue

            # Add category data to results
            results["phase1_categories"][result["category_key"]] = result["category_data"]

            # Aggregate counters
            counters = result["counters"]
            results["total_api_calls"] += counters["total_api_calls"]
            results["stored_logs"] += counters["stored_logs"]
            results["stored_results"] += counters["stored_results"]
            results["stored_sources"] += counters["stored_sources"]

            # Merge providers_used lists (avoid duplicates)
            for provider in counters["providers_used"]:
                if provider not in results["providers_used"]:
                    results["providers_used"].append(provider)

        # Process Phase 2 categories (Decision Intelligence) - these use Phase 1 data
        print(f"\n{'='*80}")
        print(f"[PHASE 2 CHECK] phase2_categories: {phase2_categories}")
        print(f"[PHASE 2 CHECK] len(phase2_categories): {len(phase2_categories) if phase2_categories else 0}")
        print(f"{'='*80}\n")

        if phase2_categories:
            print(f"[PHASE 2] *** STARTING PHASE 2 PROCESSING ***")
            print(f"[PHASE 2] Processing {len(phase2_categories)} Phase 2 categories...")
            print(f"[PHASE 2] Categories: {[c.get('name', 'Unknown') for c in phase2_categories]}")

            from .pipeline_integration_service import PipelineIntegrationService
            pipeline_service = PipelineIntegrationService()

            # CRITICAL: Parameter-Based Scoring Matrix MUST run first and succeed
            # Separate Parameter-Based Scoring Matrix from other Phase 2 categories
            scoring_matrix_category = None
            other_phase2_categories = []

            for category in phase2_categories:
                if category.get('name') == 'Parameter-Based Scoring Matrix':
                    scoring_matrix_category = category
                    print(f"[PHASE 2] Found MANDATORY category: {category.get('name')}")
                else:
                    other_phase2_categories.append(category)

            # Process Parameter-Based Scoring Matrix FIRST (mandatory)
            if scoring_matrix_category:
                print(f"[PHASE 2] *** STEP 1: Processing MANDATORY Parameter-Based Scoring Matrix ***")
                print(f"[PHASE 2] This category MUST complete successfully before other Phase 2 categories can proceed")

                try:
                    scoring_result = await self._process_phase2_category(
                        scoring_matrix_category, drug_name, request_id, pipeline_service
                    )

                    # Check if scoring matrix succeeded
                    if scoring_result and isinstance(scoring_result, dict):
                        scoring_status = scoring_result.get("category_data", {}).get("status", "failed")

                        if scoring_status == "completed":
                            print(f"[PHASE 2] ✓ Parameter-Based Scoring Matrix COMPLETED successfully")
                            print(f"[PHASE 2] Storing scoring matrix result...")

                            category_key = scoring_result["category_key"]
                            results["phase2_categories"][category_key] = scoring_result["category_data"]
                            results["stored_results"] += 1

                            print(f"[PHASE 2] *** STEP 2: Processing {len(other_phase2_categories)} dependent Phase 2 categories ***")

                            # Now process other Phase 2 categories
                            if other_phase2_categories:
                                phase2_tasks = []
                                for category in other_phase2_categories:
                                    print(f"[PHASE 2] Creating task for: {category.get('name', 'Unknown')}")
                                    phase2_tasks.append(
                                        self._process_phase2_category(
                                            category, drug_name, request_id, pipeline_service
                                        )
                                    )

                                print(f"[PHASE 2] Awaiting {len(phase2_tasks)} dependent Phase 2 tasks...")
                                phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
                                print(f"[PHASE 2] All dependent Phase 2 categories completed!")

                                # Aggregate Phase 2 results
                                for i, result in enumerate(phase2_results):
                                    if result is None or isinstance(result, Exception):
                                        if isinstance(result, Exception):
                                            print(f"[PHASE 2] Category error [{i}]: {str(result)}")
                                            import traceback
                                            print(f"[PHASE 2] Traceback: {traceback.format_exc()}")
                                        else:
                                            print(f"[PHASE 2] Result [{i}] is None")
                                        continue

                                    category_key = result["category_key"]
                                    print(f"[PHASE 2] Storing result for {category_key}: {result['category_data'].get('status', 'unknown')}")
                                    results["phase2_categories"][category_key] = result["category_data"]
                                    results["stored_results"] += 1
                            else:
                                print(f"[PHASE 2] No other Phase 2 categories to process")

                        else:
                            print(f"[PHASE 2] ✗ Parameter-Based Scoring Matrix FAILED with status: {scoring_status}")
                            print(f"[PHASE 2] ERROR: Cannot proceed with other Phase 2 categories without successful scoring matrix")
                            print(f"[PHASE 2] Skipping {len(other_phase2_categories)} dependent Phase 2 categories")

                            # Store the failed scoring result
                            category_key = scoring_result["category_key"]
                            results["phase2_categories"][category_key] = scoring_result["category_data"]

                    else:
                        print(f"[PHASE 2] ✗ Parameter-Based Scoring Matrix returned invalid result")
                        print(f"[PHASE 2] ERROR: Cannot proceed with other Phase 2 categories")
                        print(f"[PHASE 2] Skipping {len(other_phase2_categories)} dependent Phase 2 categories")

                except Exception as e:
                    print(f"[PHASE 2] ✗ CRITICAL ERROR: Parameter-Based Scoring Matrix failed with exception")
                    print(f"[PHASE 2] Exception: {str(e)}")
                    import traceback
                    print(f"[PHASE 2] Traceback: {traceback.format_exc()}")
                    print(f"[PHASE 2] ERROR: Cannot proceed with other Phase 2 categories")
                    print(f"[PHASE 2] Skipping {len(other_phase2_categories)} dependent Phase 2 categories")

            else:
                print(f"[PHASE 2] WARNING: Parameter-Based Scoring Matrix not found in Phase 2 categories!")
                print(f"[PHASE 2] This is unexpected - all Phase 2 categories depend on scoring matrix")
                print(f"[PHASE 2] Proceeding with available Phase 2 categories anyway...")

                # Fallback: process all available Phase 2 categories
                phase2_tasks = []
                for category in other_phase2_categories:
                    print(f"[PHASE 2] Creating task for: {category.get('name', 'Unknown')}")
                    phase2_tasks.append(
                        self._process_phase2_category(
                            category, drug_name, request_id, pipeline_service
                        )
                    )

                if phase2_tasks:
                    print(f"[PHASE 2] Awaiting {len(phase2_tasks)} Phase 2 tasks...")
                    phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

                    for i, result in enumerate(phase2_results):
                        if result is None or isinstance(result, Exception):
                            if isinstance(result, Exception):
                                print(f"[PHASE 2] Category error [{i}]: {str(result)}")
                            continue

                        category_key = result["category_key"]
                        results["phase2_categories"][category_key] = result["category_data"]
                        results["stored_results"] += 1

            print(f"[PHASE 2] *** PHASE 2 PROCESSING COMPLETE ***")
            print(f"[PHASE 2] Total Phase 2 results stored: {len(results['phase2_categories'])}")
        else:
            print(f"[PHASE 2] *** NO PHASE 2 CATEGORIES TO PROCESS ***")

        return results
# Phase 2 processing is enabled

