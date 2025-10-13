"""
ChatGPT API provider for pharmaceutical intelligence gathering.

Implements OpenAI's GPT-4 API integration for comprehensive
pharmaceutical data search and analysis.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import structlog

from .base import (
    APIProvider,
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution
)
from ...config.llm_config import get_llm_config

logger = structlog.get_logger(__name__)


class ChatGPTProvider(APIProvider):
    """
    ChatGPT/OpenAI API integration for pharmaceutical intelligence.

    Utilizes GPT-4 for comprehensive pharmaceutical data analysis,
    including clinical trials, drug interactions, and regulatory information.

    Example:
        >>> provider = ChatGPTProvider()
        >>> response = await provider.search(
        ...     "Metformin clinical trials phase 3",
        ...     temperature=0.7
        ... )

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize ChatGPT provider.

        Args:
            api_key: OpenAI API key (optional, loads from config)
            config: Provider configuration (optional, loads from env)
            timeout: Request timeout in seconds (optional)
            max_retries: Maximum retry attempts (optional)

        Since:
            Version 1.0.0
        """
        # Get configuration from centralized LLM config
        llm_manager = get_llm_config()
        openai_config = llm_manager.get_provider_config('openai')

        if not openai_config and not api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in environment.")

        # Use centralized config or fallback to provided values
        if openai_config:
            api_key = api_key or openai_config.api_key
            timeout = timeout or openai_config.timeout
            max_retries = max_retries or openai_config.max_retries

            # Merge config with LLM config
            default_config = {
                'model': openai_config.model_name,
                'base_url': openai_config.base_url,
                'max_tokens': openai_config.max_tokens,
                'temperature_default': openai_config.temperature_default,
                'cost_per_input_token': openai_config.cost_per_input_token,
                'cost_per_output_token': openai_config.cost_per_output_token
            }
            config = {**default_config, **(config or {})}

        super().__init__(api_key, config, timeout or 30, max_retries or 3)

        # Set provider-specific attributes from config
        self.BASE_URL = self.config.get('base_url', 'https://api.openai.com/v1')
        self.model = self.config.get('model', 'gpt-4-turbo-preview')
        self.COST_PER_INPUT_TOKEN = self.config.get('cost_per_input_token', 0.00001)
        self.COST_PER_OUTPUT_TOKEN = self.config.get('cost_per_output_token', 0.00003)
        self.system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """
        Get pharmaceutical-specific system prompt.

        Returns:
            System prompt for pharmaceutical intelligence gathering

        Since:
            Version 1.0.0
        """
        return """You are a pharmaceutical intelligence expert assistant.
        Provide comprehensive, accurate information about drugs, clinical trials,
        regulatory status, and medical research. Always cite sources when available
        and indicate confidence levels in your responses. Focus on factual,
        evidence-based information relevant to pharmaceutical professionals."""

    async def search(
        self,
        query: str,
        temperature: float = 0.7,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using ChatGPT.

        Args:
            query: Pharmaceutical search query
            temperature: Response randomness (0.0-1.0)
            max_results: Maximum number of results
            **kwargs: Additional OpenAI parameters

        Returns:
            Standardized response with pharmaceutical intelligence

        Raises:
            APIException: If OpenAI API call fails

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Check if model is restricted or GPT-5
            is_restricted_model = "search" in self.model.lower() or "o1" in self.model.lower()
            is_gpt5_model = "gpt-5" in self.model.lower()

            # Prepare the request
            messages = [
                {"role": "system", "content": self.system_prompt + (" with live search enabled" if is_gpt5_model else "")},
                {
                    "role": "user",
                    "content": self._format_query(query, max_results)
                }
            ]

            # Build request payload
            request_json = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get('max_tokens', 4000),
                "response_format": {"type": "json_object"}
            }

            # Only add temperature for models that support it
            if not is_restricted_model:
                request_json["temperature"] = temperature

            # Add web search tools for GPT-5 models
            if is_gpt5_model:
                request_json["tools"] = [{"type": "web_search"}]

            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_json
                )
                response.raise_for_status()

            # Parse response
            data = response.json()
            content = data['choices'][0]['message']['content']

            # Parse JSON response
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                parsed_content = {"results": [], "sources": []}

            # Calculate response time
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Build standardized response
            return StandardizedAPIResponse(
                provider="chatgpt",
                query=query,
                temperature=temperature,
                results=self._parse_results(parsed_content.get('results', [])),
                total_results=len(parsed_content.get('results', [])),
                sources=self._parse_sources(parsed_content.get('sources', [])),
                response_time_ms=response_time_ms,
                cost=self._calculate_token_cost(data.get('usage', {})),
                timestamp=datetime.utcnow(),
                relevance_score=self._calculate_relevance(parsed_content),
                confidence_score=parsed_content.get('confidence', 0.8)
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "ChatGPT API error",
                status_code=e.response.status_code,
                error=str(e)
            )
            return self._error_response(query, temperature, str(e))

        except Exception as e:
            logger.error("ChatGPT provider error", error=str(e))
            return self._error_response(query, temperature, str(e))

    def _format_query(self, query: str, max_results: int) -> str:
        """
        Format query for optimal ChatGPT response.

        Args:
            query: Original query
            max_results: Maximum results to return

        Returns:
            Formatted query with instructions

        Since:
            Version 1.0.0
        """
        return f"""Provide comprehensive pharmaceutical intelligence for: {query}

Please return a JSON response with the following structure:
{{
    "results": [
        {{
            "title": "Result title",
            "content": "Detailed pharmaceutical information",
            "source_type": "research_paper|clinical_trial|regulatory|news|other",
            "relevance": 0.0-1.0
        }}
    ],
    "sources": [
        {{
            "title": "Source title",
            "url": "Source URL if known",
            "domain": "Source domain",
            "source_type": "Type of source",
            "credibility": 0.0-1.0
        }}
    ],
    "confidence": 0.0-1.0
}}

Limit results to {max_results} most relevant items.
Focus on pharmaceutical, clinical, and regulatory information."""

    def _parse_results(self, results: List[Dict]) -> List[SearchResult]:
        """
        Parse ChatGPT results into standardized format.

        Args:
            results: Raw results from ChatGPT

        Returns:
            List of standardized search results

        Since:
            Version 1.0.0
        """
        parsed_results = []
        for result in results:
            parsed_results.append(SearchResult(
                title=result.get('title', 'Untitled'),
                content=result.get('content', ''),
                url=result.get('url'),
                relevance_score=float(result.get('relevance', 0.5)),
                source_type=result.get('source_type', 'other'),
                metadata=result.get('metadata', {})
            ))
        return parsed_results

    def _parse_sources(self, sources: List[Dict]) -> List[SourceAttribution]:
        """
        Parse source attributions from ChatGPT.

        Args:
            sources: Raw sources from ChatGPT

        Returns:
            List of source attributions

        Since:
            Version 1.0.0
        """
        parsed_sources = []
        for source in sources:
            parsed_sources.append(SourceAttribution(
                url=source.get('url', ''),
                title=source.get('title', ''),
                domain=source.get('domain', 'unknown'),
                source_type=source.get('source_type', 'other'),
                credibility_score=float(source.get('credibility', 0.5))
            ))
        return parsed_sources

    def _calculate_relevance(self, content: Dict) -> float:
        """
        Calculate overall relevance score.

        Args:
            content: Parsed response content

        Returns:
            Relevance score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        results = content.get('results', [])
        if not results:
            return 0.0

        scores = [r.get('relevance', 0.5) for r in results]
        return sum(scores) / len(scores)

    def _calculate_token_cost(self, usage: Dict) -> float:
        """
        Calculate API call cost based on token usage.

        Args:
            usage: Token usage from OpenAI response

        Returns:
            Cost in USD

        Since:
            Version 1.0.0
        """
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        input_cost = (input_tokens / 1000) * self.COST_PER_INPUT_TOKEN * 1000
        output_cost = (output_tokens / 1000) * self.COST_PER_OUTPUT_TOKEN * 1000

        return round(input_cost + output_cost, 4)

    def _error_response(self, query: str, temperature: float, error: str) -> StandardizedAPIResponse:
        """
        Create error response in standardized format.

        Args:
            query: Original query
            temperature: Temperature parameter
            error: Error message

        Returns:
            Standardized error response

        Since:
            Version 1.0.0
        """
        return StandardizedAPIResponse(
            provider="chatgpt",
            query=query,
            temperature=temperature,
            results=[],
            total_results=0,
            sources=[],
            response_time_ms=0,
            cost=0.0,
            timestamp=datetime.utcnow(),
            relevance_score=0.0,
            confidence_score=0.0,
            error=error
        )

    async def health_check(self) -> bool:
        """
        Check ChatGPT API health and availability.

        Returns:
            True if API is accessible

        Since:
            Version 1.0.0
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("ChatGPT health check failed", error=str(e))
            return False

    def calculate_cost(self, response: StandardizedAPIResponse) -> float:
        """
        Calculate cost for ChatGPT API response.

        Args:
            response: API response to calculate cost for

        Returns:
            Cost in USD

        Since:
            Version 1.0.0
        """
        return response.cost

    def validate_config(self) -> bool:
        """
        Validate ChatGPT configuration.

        Returns:
            True if configuration is valid

        Since:
            Version 1.0.0
        """
        if not self.api_key or not self.api_key.startswith('sk-'):
            logger.error("Invalid ChatGPT API key format")
            return False

        if self.model not in ['gpt-4-turbo-preview', 'gpt-4', 'gpt-4o', 'gpt-5-nano', 'gpt-3.5-turbo']:
            logger.warning(f"Unusual model selection: {self.model}")

        return True