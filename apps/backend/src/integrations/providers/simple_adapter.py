"""
Simple adapter for provider calls to support the existing main_simple.py structure.
This module bridges the gap between the quick implementation and proper architecture.
"""

import aiohttp
from typing import Dict, Any, Optional
from .chatgpt import ChatGPTProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider


async def make_provider_call(
    provider: str,
    drug_name: str,
    api_key: str,
    model: str,
    temperature: float
) -> str:
    """
    Make API call to specified provider with drug query.

    Args:
        provider: Provider name (openai, claude, gemini)
        drug_name: Drug name to query
        api_key: API key for the provider
        model: Model to use
        temperature: Temperature parameter

    Returns:
        Response string from the provider
    """
    try:
        if provider.lower() in ["openai", "chatgpt"]:
            return await make_openai_call_simple(drug_name, api_key, model, temperature)
        elif provider.lower() in ["claude", "anthropic"]:
            return await make_claude_call_simple(drug_name, api_key, model, temperature)
        elif provider.lower() == "gemini":
            return await make_gemini_call_simple(drug_name, api_key, model, temperature)
        else:
            return f"Provider {provider} not yet implemented"
    except Exception as e:
        return f"Error calling {provider}: {str(e)}"


async def make_openai_call_simple(drug_name: str, api_key: str, model: str, temperature: float) -> str:
    """Make a simple OpenAI API call."""
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Check if model is a search/o1 model that doesn't support temperature
            is_restricted_model = "search" in model.lower() or "o1" in model.lower()

            # Check if model is GPT-5 that supports web search
            is_gpt5_model = "gpt-5" in model.lower()

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a pharmaceutical expert analyzing drug information with live search enabled." if is_gpt5_model else "You are a pharmaceutical expert analyzing drug information."},
                    {"role": "user", "content": f"Provide comprehensive analysis for the drug: {drug_name}. Include safety profile, efficacy, interactions, and regulatory status."}
                ],
                "max_tokens": 500
            }

            # Only add temperature for models that support it
            if not is_restricted_model:
                payload["temperature"] = temperature

            # Add web search tools for GPT-5 models
            if is_gpt5_model:
                payload["tools"] = [{"type": "web_search"}]

            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"OpenAI API error: {response.status} - {error_text[:200]}"

        except Exception as e:
            return f"OpenAI API call failed: {str(e)}"


async def make_claude_call_simple(drug_name: str, api_key: str, model: str, temperature: float) -> str:
    """Make a simple Claude API call."""
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": f"Provide comprehensive analysis for the drug: {drug_name}. Include safety profile, efficacy, interactions, and regulatory status."}
                ],
                "temperature": temperature,
                "max_tokens": 500
            }

            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["content"][0]["text"]
                else:
                    error_text = await response.text()
                    return f"Claude API error: {response.status} - {error_text[:200]}"

        except Exception as e:
            return f"Claude API call failed: {str(e)}"


async def make_gemini_call_simple(drug_name: str, api_key: str, model: str, temperature: float) -> str:
    """Make a simple Gemini API call."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Provide comprehensive analysis for the drug: {drug_name}. Include safety profile, efficacy, interactions, and regulatory status."
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 500
                }
            }

            async with session.post(url, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    error_text = await response.text()
                    return f"Gemini API error: {response.status} - {error_text[:200]}"

        except Exception as e:
            return f"Gemini API call failed: {str(e)}"