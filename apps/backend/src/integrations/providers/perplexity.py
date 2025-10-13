"""
Perplexity API provider for pharmaceutical intelligence gathering.

Implements Perplexity AI's API integration for real-time web search
and pharmaceutical data analysis with source citations.

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


class PerplexityProvider(APIProvider):
    """
    Perplexity AI API integration for pharmaceutical intelligence.

    Specializes in real-time web search with accurate source citations,
    particularly useful for recent pharmaceutical developments and news.

    Example:
        >>> provider = PerplexityProvider()
        >>> response = await provider.search(
        ...     "Latest FDA approvals for diabetes medications 2024",
        ...     temperature=0.2
        ... )

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
        Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key
            config: Provider configuration
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts

        Since:
            Version 1.0.0
        """
        super().__init__(api_key, config, timeout, max_retries)

        # Set provider-specific attributes from config
        self.BASE_URL = self.config.get('base_url', 'https://api.perplexity.ai')
        self.model = self.config.get('model', 'pplx-70b-online')
        self.COST_PER_REQUEST = self.config.get('cost_per_request', 0.001)
        self.search_domain_filter = self.config.get('domain_filter', [
            'pubmed.ncbi.nlm.nih.gov',
            'fda.gov',
            'clinicaltrials.gov',
            'nejm.org',
            'nature.com',
            'sciencedirect.com'
        ])

    async def search(
        self,
        query: str,
        temperature: float = 0.2,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using Perplexity.

        Args:
            query: Pharmaceutical search query
            temperature: Response randomness (0.0-1.0)
            max_results: Maximum number of results
            **kwargs: Additional Perplexity parameters

        Returns:
            Standardized response with pharmaceutical intelligence

        Raises:
            APIException: If Perplexity API call fails

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Prepare the request with pharmaceutical focus
            request_body = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a pharmaceutical research assistant. Provide accurate, citation-backed information about drugs, clinical trials, and medical research. Always include source URLs."
                    },
                    {
                        "role": "user",
                        "content": self._format_pharmaceutical_query(query, max_results)
                    }
                ],
                "temperature": temperature,
                "search_domain_filter": self.search_domain_filter,
                "return_citations": True,
                "search_recency_filter": kwargs.get('recency_filter', 'month')
            }

            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body
                )
                response.raise_for_status()

            # Parse response
            data = response.json()
            content = data['choices'][0]['message']['content']
            citations = data.get('citations', [])

            # Calculate response time
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Parse and build standardized response
            return StandardizedAPIResponse(
                provider="perplexity",
                query=query,
                temperature=temperature,
                results=self._parse_perplexity_results(content, citations, max_results),
                total_results=len(citations),
                sources=self._parse_perplexity_sources(citations),
                response_time_ms=response_time_ms,
                cost=self.COST_PER_REQUEST,
                timestamp=datetime.utcnow(),
                relevance_score=self._calculate_relevance_score(citations),
                confidence_score=0.85  # Perplexity provides high-quality citations
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "Perplexity API error",
                status_code=e.response.status_code,
                error=str(e)
            )
            return self._error_response(query, temperature, str(e))

        except Exception as e:
            logger.error("Perplexity provider error", error=str(e))
            return self._error_response(query, temperature, str(e))

    def _format_pharmaceutical_query(self, query: str, max_results: int) -> str:
        """
        Format query for pharmaceutical-focused Perplexity search.

        Args:
            query: Original query
            max_results: Maximum results to return

        Returns:
            Formatted query with pharmaceutical focus

        Since:
            Version 1.0.0
        """
        return f"""Search for pharmaceutical and medical information about: {query}

Focus on:
1. Clinical trial data and results
2. FDA approvals and regulatory status
3. Scientific research papers
4. Drug interactions and contraindications
5. Recent developments and news

Provide {max_results} most relevant results with proper citations.
Include publication dates and credibility assessment for each source."""

    def _parse_perplexity_results(
        self,
        content: str,
        citations: List[Dict],
        max_results: int
    ) -> List[SearchResult]:
        """
        Parse Perplexity response into standardized results.

        Args:
            content: Response content
            citations: Citation data from Perplexity
            max_results: Maximum number of results

        Returns:
            List of standardized search results

        Since:
            Version 1.0.0
        """
        results = []

        # Split content into sections if possible
        sections = content.split('\n\n')[:max_results]

        for i, section in enumerate(sections):
            if section.strip():
                # Match section with citation if available
                citation = citations[i] if i < len(citations) else {}

                results.append(SearchResult(
                    title=citation.get('title', f"Result {i+1}"),
                    content=section.strip(),
                    url=citation.get('url'),
                    relevance_score=self._assess_pharmaceutical_relevance(section),
                    source_type=self._classify_source_type(citation.get('url', '')),
                    metadata={
                        'citation_index': i,
                        'domain': citation.get('domain', 'unknown')
                    }
                ))

        return results[:max_results]

    def _parse_perplexity_sources(self, citations: List[Dict]) -> List[SourceAttribution]:
        """
        Parse Perplexity citations into source attributions.

        Args:
            citations: Citation data from Perplexity

        Returns:
            List of source attributions

        Since:
            Version 1.0.0
        """
        sources = []

        for citation in citations:
            sources.append(SourceAttribution(
                url=citation.get('url', ''),
                title=citation.get('title', 'Untitled'),
                domain=citation.get('domain', 'unknown'),
                source_type=self._classify_source_type(citation.get('url', '')),
                credibility_score=self._assess_source_credibility(citation.get('domain', '')),
                published_date=self._parse_date(citation.get('published_date'))
            ))

        return sources

    def _classify_source_type(self, url: str) -> str:
        """
        Classify source type based on URL.

        Args:
            url: Source URL

        Returns:
            Source type classification

        Since:
            Version 1.0.0
        """
        url_lower = url.lower()

        if 'clinicaltrials.gov' in url_lower:
            return 'clinical_trial'
        elif 'pubmed' in url_lower or 'ncbi' in url_lower:
            return 'research_paper'
        elif 'fda.gov' in url_lower:
            return 'regulatory'
        elif any(journal in url_lower for journal in ['nejm', 'nature', 'science', 'lancet']):
            return 'research_paper'
        elif any(news in url_lower for news in ['news', 'press', 'release']):
            return 'news'
        else:
            return 'other'

    def _assess_pharmaceutical_relevance(self, content: str) -> float:
        """
        Assess pharmaceutical relevance of content.

        Args:
            content: Text content to assess

        Returns:
            Relevance score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        pharmaceutical_keywords = [
            'clinical trial', 'fda', 'drug', 'medication', 'pharmaceutical',
            'efficacy', 'safety', 'adverse', 'interaction', 'dosage',
            'treatment', 'therapy', 'patient', 'study', 'research'
        ]

        content_lower = content.lower()
        keyword_count = sum(1 for keyword in pharmaceutical_keywords if keyword in content_lower)
        relevance = min(keyword_count / 5.0, 1.0)  # Normalize to 0-1

        return round(relevance, 2)

    def _assess_source_credibility(self, domain: str) -> float:
        """
        Assess credibility of source domain.

        Args:
            domain: Source domain

        Returns:
            Credibility score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        high_credibility_domains = {
            'pubmed.ncbi.nlm.nih.gov': 0.95,
            'fda.gov': 0.95,
            'clinicaltrials.gov': 0.95,
            'nejm.org': 0.90,
            'nature.com': 0.90,
            'sciencedirect.com': 0.85,
            'thelancet.com': 0.90,
            'bmj.com': 0.85
        }

        domain_lower = domain.lower()
        for trusted_domain, score in high_credibility_domains.items():
            if trusted_domain in domain_lower:
                return score

        return 0.5  # Default credibility for unknown sources

    def _calculate_relevance_score(self, citations: List[Dict]) -> float:
        """
        Calculate overall relevance score based on citations.

        Args:
            citations: Citation data

        Returns:
            Overall relevance score

        Since:
            Version 1.0.0
        """
        if not citations:
            return 0.0

        scores = [
            self._assess_source_credibility(c.get('domain', ''))
            for c in citations
        ]

        return round(sum(scores) / len(scores), 2)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime or None

        Since:
            Version 1.0.0
        """
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None

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
            provider="perplexity",
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
        Check Perplexity API health and availability.

        Returns:
            True if API is accessible

        Since:
            Version 1.0.0
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "pplx-7b-online",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.warning("Perplexity health check failed", error=str(e))
            return False

    def calculate_cost(self, response: StandardizedAPIResponse) -> float:
        """
        Calculate cost for Perplexity API response.

        Args:
            response: API response to calculate cost for

        Returns:
            Cost in USD

        Since:
            Version 1.0.0
        """
        return self.COST_PER_REQUEST

    def validate_config(self) -> bool:
        """
        Validate Perplexity configuration.

        Returns:
            True if configuration is valid

        Since:
            Version 1.0.0
        """
        if not self.api_key or not self.api_key.startswith('pplx-'):
            logger.error("Invalid Perplexity API key format")
            return False

        valid_models = ['pplx-70b-online', 'pplx-7b-online', 'pplx-70b-chat', 'pplx-7b-chat']
        if self.model not in valid_models:
            logger.warning(f"Invalid model selection: {self.model}")
            return False

        return True