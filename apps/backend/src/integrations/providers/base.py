"""
Abstract base class for pharmaceutical intelligence API providers.

Provides standardized interface for all external API integrations
including search, health checks, and cost calculation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SourceAttribution(BaseModel):
    """
    Source attribution metadata for API responses.

    Since:
        Version 1.0.0
    """
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Source title")
    domain: str = Field(..., description="Source domain")
    source_type: str = Field(..., description="Source type (research_paper, clinical_trial, news, etc.)")
    credibility_score: float = Field(..., ge=0.0, le=1.0, description="Source credibility score")
    published_date: Optional[datetime] = Field(None, description="Publication date if available")


class SearchResult(BaseModel):
    """
    Individual search result from API provider.

    Since:
        Version 1.0.0
    """
    title: str = Field(..., description="Result title")
    content: str = Field(..., description="Result content")
    url: Optional[str] = Field(None, description="Result URL if available")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source_type: str = Field(..., description="Type of source")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class StandardizedAPIResponse(BaseModel):
    """
    Standardized response format for all API providers.

    Since:
        Version 1.0.0
    """
    provider: str = Field(..., description="API provider name")
    query: str = Field(..., description="Original query")
    temperature: float = Field(..., description="Temperature parameter used")

    # Response content
    results: List[SearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., description="Total number of results")

    # Source attribution
    sources: List[SourceAttribution] = Field(default_factory=list, description="Source attributions")

    # Metadata
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    cost: float = Field(..., description="Cost of this API call")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    # Quality metrics
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Overall relevance score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in results")

    # Error handling
    error: Optional[str] = Field(None, description="Error message if any")
    warning: Optional[str] = Field(None, description="Warning message if any")


class APIProvider(ABC):
    """
    Abstract base class for all pharmaceutical intelligence API providers.

    This class defines the standard interface that all API providers must
    implement for pharmaceutical data gathering and intelligence processing.

    Attributes:
        name: Provider name (e.g., 'chatgpt', 'perplexity')
        api_key: API authentication key
        config: Provider-specific configuration
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts

    Example:
        >>> class ChatGPTProvider(APIProvider):
        ...     async def search(self, query, temperature=0.7, max_results=10):
        ...         # Implementation specific to ChatGPT
        ...         pass

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        api_key: str,
        config: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize API provider.

        Args:
            api_key: API authentication key
            config: Provider-specific configuration
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts

        Since:
            Version 1.0.0
        """
        self.name = self.__class__.__name__.replace('Provider', '').lower()
        self.api_key = api_key
        self.config = config or {}
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    async def search(
        self,
        query: str,
        temperature: float = 0.7,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical intelligence search.

        Args:
            query: Search query for pharmaceutical data
            temperature: Randomness parameter (0.0 to 1.0)
            max_results: Maximum number of results to return
            **kwargs: Provider-specific parameters

        Returns:
            Standardized API response with search results

        Raises:
            APIException: If API call fails
            RateLimitException: If rate limit exceeded
            TimeoutException: If request times out

        Since:
            Version 1.0.0
        """
        raise NotImplementedError("Subclasses must implement search method")

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check API provider health and availability.

        Returns:
            True if provider is healthy and available

        Since:
            Version 1.0.0
        """
        raise NotImplementedError("Subclasses must implement health_check method")

    @abstractmethod
    def calculate_cost(self, response: StandardizedAPIResponse) -> float:
        """
        Calculate cost for this API response.

        Args:
            response: The API response to calculate cost for

        Returns:
            Cost in USD for this API call

        Since:
            Version 1.0.0
        """
        raise NotImplementedError("Subclasses must implement calculate_cost method")

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate provider configuration and API key.

        Returns:
            True if configuration is valid

        Since:
            Version 1.0.0
        """
        raise NotImplementedError("Subclasses must implement validate_config method")

    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get rate limiting configuration for this provider.

        Returns:
            Dictionary with rate limit settings:
            - requests_per_minute: Max requests per minute
            - requests_per_hour: Max requests per hour
            - daily_quota: Daily request quota

        Since:
            Version 1.0.0
        """
        return {
            'requests_per_minute': self.config.get('requests_per_minute', 60),
            'requests_per_hour': self.config.get('requests_per_hour', 1000),
            'daily_quota': self.config.get('daily_quota', 10000)
        }

    def get_timeout_settings(self) -> Dict[str, int]:
        """
        Get timeout configuration for this provider.

        Returns:
            Dictionary with timeout settings:
            - connect_timeout: Connection timeout in seconds
            - read_timeout: Read timeout in seconds
            - total_timeout: Total request timeout in seconds

        Since:
            Version 1.0.0
        """
        return {
            'connect_timeout': self.config.get('connect_timeout', 5),
            'read_timeout': self.config.get('read_timeout', 25),
            'total_timeout': self.timeout
        }