"""
API provider implementations for pharmaceutical intelligence gathering.

This package contains provider-specific implementations for various
AI and search APIs used in pharmaceutical data collection.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from .base import (
    APIProvider,
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution
)
from .chatgpt import ChatGPTProvider
from .perplexity import PerplexityProvider
from .grok import GrokProvider
from .gemini import GeminiProvider
from .tavily import TavilyProvider
from .anthropic import AnthropicProvider

__all__ = [
    'APIProvider',
    'StandardizedAPIResponse',
    'SearchResult',
    'SourceAttribution',
    'ChatGPTProvider',
    'PerplexityProvider',
    'GrokProvider',
    'GeminiProvider',
    'TavilyProvider',
    'AnthropicProvider'
]

# Provider name mapping
PROVIDER_CLASSES = {
    'chatgpt': ChatGPTProvider,
    'openai': ChatGPTProvider,  # Alias
    'perplexity': PerplexityProvider,
    'grok': GrokProvider,
    'xai': GrokProvider,  # Alias
    'gemini': GeminiProvider,
    'google': GeminiProvider,  # Alias
    'tavily': TavilyProvider,
    'anthropic': AnthropicProvider,
    'claude': AnthropicProvider  # Alias
}