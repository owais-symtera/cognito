"""
External API integrations for pharmaceutical intelligence gathering.

This package provides integration with multiple AI and search APIs
for comprehensive pharmaceutical data collection.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from .api_manager import MultiAPIManager
from .rate_limiter import RateLimiter
from .providers import (
    APIProvider,
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution,
    ChatGPTProvider,
    PerplexityProvider
)

__all__ = [
    'MultiAPIManager',
    'RateLimiter',
    'APIProvider',
    'StandardizedAPIResponse',
    'SearchResult',
    'SourceAttribution',
    'ChatGPTProvider',
    'PerplexityProvider'
]