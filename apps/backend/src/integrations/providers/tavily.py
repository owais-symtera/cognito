"""
Tavily Search API provider for pharmaceutical intelligence gathering.

Implements Tavily's specialized search API for deep web research
and pharmaceutical information discovery.

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


class TavilyProvider(APIProvider):
    """
    Tavily Search API integration for pharmaceutical intelligence.

    Specialized in deep web search, research paper discovery, and
    comprehensive pharmaceutical information gathering.

    Example:
        >>> provider = TavilyProvider()
        >>> response = await provider.search(
        ...     "biosimilar approval pathways FDA Europe comparison",
        ...     temperature=0.0  # Not used for search
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
        Initialize Tavily provider.

        Args:
            api_key: Tavily API key (optional, loads from config)
            config: Provider configuration (optional, loads from env)
            timeout: Request timeout in seconds (optional)
            max_retries: Maximum retry attempts (optional)

        Since:
            Version 1.0.0
        """
        # Get configuration from centralized LLM config
        llm_manager = get_llm_config()
        tavily_config = llm_manager.get_provider_config('tavily')

        if not tavily_config and not api_key:
            raise ValueError("Tavily API key not configured. Set TAVILY_API_KEY in environment.")

        # Use centralized config or fallback to provided values
        if tavily_config:
            api_key = api_key or tavily_config.api_key
            timeout = timeout or tavily_config.timeout
            max_retries = max_retries or tavily_config.max_retries

            # Merge config with Tavily config
            default_config = {
                'base_url': tavily_config.base_url or 'https://api.tavily.com',
                'max_results': tavily_config.max_tokens or 10,  # max_tokens used for max_results
                'search_depth': 'advanced',  # 'basic' or 'advanced'
                'include_domains': [],  # Pharmaceutical domains
                'exclude_domains': [],  # Unreliable domains
            }
            config = {**default_config, **(config or {})}

        super().__init__(api_key, config, timeout or 30, max_retries or 3)

        # Set provider-specific attributes
        self.BASE_URL = self.config.get('base_url', 'https://api.tavily.com')
        self.COST_PER_SEARCH = 0.01  # Approximate cost per search

        # Pharmaceutical-focused domains
        self.PHARMA_DOMAINS = [
            "fda.gov",
            "ema.europa.eu",
            "who.int",
            "clinicaltrials.gov",
            "pubmed.ncbi.nlm.nih.gov",
            "nejm.org",
            "thelancet.com",
            "nature.com",
            "science.org",
            "bmj.com"
        ]

    async def search(
        self,
        query: str,
        temperature: float = 0.0,  # Not used for search
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using Tavily.

        Args:
            query: Search query for pharmaceutical information
            temperature: Not used for search API
            max_results: Maximum number of results to return
            **kwargs: Additional parameters

        Returns:
            StandardizedAPIResponse with search results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Enhance query for pharmaceutical context
            enhanced_query = self._enhance_pharma_query(query)

            # Prepare request payload
            payload = {
                "api_key": self.api_key,
                "query": enhanced_query,
                "search_depth": self.config.get('search_depth', 'advanced'),
                "max_results": max_results,
                "include_images": False,
                "include_answer": True,
                "include_raw_content": True,
                "include_domains": self.config.get('include_domains', []) or self.PHARMA_DOMAINS,
                "exclude_domains": self.config.get('exclude_domains', [])
            }

            # Add any additional parameters
            for key, value in kwargs.items():
                if key not in payload:
                    payload[key] = value

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    json=payload
                )
                response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract and process results
            results = self._parse_tavily_response(data, query)

            # Calculate metrics
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return StandardizedAPIResponse(
                provider="tavily",
                query=query,
                temperature=0.0,  # Not applicable for search
                results=results['search_results'],
                sources=results['sources'],
                total_results=len(results['search_results']),
                response_time_ms=response_time_ms,
                cost=self.COST_PER_SEARCH,
                relevance_score=results.get('relevance_score', 0.88),
                confidence_score=results.get('confidence_score', 0.9),
                timestamp=start_time,
                metadata={
                    'search_depth': payload['search_depth'],
                    'answer_provided': 'answer' in data,
                    'total_sources_found': data.get('total_results', 0),
                    'pharmaceutical_focused': True
                }
            )

        except httpx.HTTPError as e:
            logger.error(f"Tavily API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Tavily search: {e}")
            raise

    def _enhance_pharma_query(self, query: str) -> str:
        """
        Enhance query with pharmaceutical search terms.

        Args:
            query: Original search query

        Returns:
            Enhanced query string

        Since:
            Version 1.0.0
        """
        # Add pharmaceutical context without being too verbose
        pharma_terms = []

        # Add relevant modifiers based on query content
        query_lower = query.lower()

        if "drug" in query_lower or "medication" in query_lower:
            pharma_terms.append("pharmaceutical")

        if "trial" in query_lower:
            pharma_terms.append("clinical trial phases results")

        if "fda" not in query_lower and "regulatory" in query_lower:
            pharma_terms.append("FDA EMA regulatory")

        if "safety" in query_lower or "side effect" in query_lower:
            pharma_terms.append("adverse events contraindications")

        # Combine query with enhancements
        if pharma_terms:
            return f"{query} {' '.join(pharma_terms)}"

        return query

    def _parse_tavily_response(
        self,
        data: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Parse Tavily API response into standardized format.

        Args:
            data: Raw API response
            original_query: Original search query

        Returns:
            Parsed results dictionary

        Since:
            Version 1.0.0
        """
        search_results = []
        sources = []

        # Process answer if provided
        if 'answer' in data and data['answer']:
            search_results.append(SearchResult(
                title="Synthesized Answer",
                content=data['answer'],
                relevance_score=0.95,  # Answers are highly relevant
                source_type="synthesis",
                metadata={
                    'is_answer': True,
                    'confidence': 0.92
                }
            ))

        # Process search results
        if 'results' in data:
            for idx, result in enumerate(data['results']):
                # Extract content
                content = result.get('content', '')
                if not content and 'raw_content' in result:
                    content = result['raw_content'][:1500]  # Limit length

                # Determine source type
                source_type = self._classify_source(result.get('url', ''))

                # Calculate relevance based on score and position
                relevance = result.get('score', 0.8)
                if idx < 3:  # Boost top results
                    relevance = min(relevance * 1.1, 1.0)

                search_results.append(SearchResult(
                    title=result.get('title', f'Result {idx + 1}'),
                    content=content,
                    relevance_score=relevance,
                    source_type=source_type,
                    metadata={
                        'url': result.get('url'),
                        'published_date': result.get('published_date'),
                        'score': result.get('score'),
                        'has_raw_content': 'raw_content' in result
                    }
                ))

                # Create source attribution
                sources.append(SourceAttribution(
                    title=result.get('title', 'Unknown'),
                    url=result.get('url', ''),
                    domain=self._extract_domain(result.get('url', '')),
                    source_type=source_type,
                    credibility_score=self._calculate_credibility(
                        result.get('url', ''),
                        result.get('score', 0.7)
                    )
                ))

        # Process images if any (though we disabled them)
        if 'images' in data and data['images']:
            for image in data['images'][:3]:  # Limit to 3 images
                search_results.append(SearchResult(
                    title=f"Related Image: {image.get('title', 'Image')}",
                    content=f"Image URL: {image.get('url', '')}",
                    relevance_score=0.7,
                    source_type="image",
                    metadata={
                        'image_url': image.get('url'),
                        'is_image': True
                    }
                ))

        return {
            'search_results': search_results,
            'sources': sources,
            'relevance_score': self._calculate_overall_relevance(search_results),
            'confidence_score': 0.9 if 'answer' in data else 0.85
        }

    def _classify_source(self, url: str) -> str:
        """
        Classify source type based on URL.

        Args:
            url: Source URL

        Returns:
            Source type classification

        Since:
            Version 1.0.0
        """
        if not url:
            return "unknown"

        url_lower = url.lower()

        # Check pharmaceutical sources
        if "fda.gov" in url_lower:
            return "regulatory"
        elif "ema.europa.eu" in url_lower:
            return "regulatory"
        elif "clinicaltrials.gov" in url_lower:
            return "clinical_trial"
        elif "pubmed" in url_lower or "ncbi.nlm.nih.gov" in url_lower:
            return "research_paper"
        elif "nejm.org" in url_lower or "thelancet.com" in url_lower:
            return "medical_journal"
        elif "nature.com" in url_lower or "science.org" in url_lower:
            return "scientific_journal"
        elif ".edu" in url_lower:
            return "academic"
        elif "who.int" in url_lower:
            return "international_org"
        elif any(pharma in url_lower for pharma in ["pfizer", "merck", "novartis", "roche", "gsk"]):
            return "pharmaceutical_company"
        else:
            return "web_resource"

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain name

        Since:
            Version 1.0.0
        """
        if not url:
            return "unknown"

        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or "unknown"
        except:
            return "unknown"

    def _calculate_credibility(self, url: str, score: float) -> float:
        """
        Calculate source credibility based on URL and Tavily score.

        Args:
            url: Source URL
            score: Tavily relevance score

        Returns:
            Credibility score (0.0-1.0)

        Since:
            Version 1.0.0
        """
        if not url:
            return 0.5

        url_lower = url.lower()

        # High credibility pharmaceutical sources
        high_cred_domains = {
            "fda.gov": 0.98,
            "ema.europa.eu": 0.97,
            "who.int": 0.96,
            "clinicaltrials.gov": 0.95,
            "pubmed.ncbi.nlm.nih.gov": 0.94,
            "nejm.org": 0.93,
            "thelancet.com": 0.93,
            "nature.com": 0.92,
            "science.org": 0.92,
            "bmj.com": 0.91
        }

        for domain, cred in high_cred_domains.items():
            if domain in url_lower:
                # Combine domain credibility with Tavily score
                return (cred * 0.7) + (score * 0.3)

        # Medium credibility
        if ".edu" in url_lower:
            return (0.85 * 0.7) + (score * 0.3)

        # Default credibility based on Tavily score
        return (0.7 * 0.5) + (score * 0.5)

    def _calculate_overall_relevance(self, results: List[SearchResult]) -> float:
        """
        Calculate overall relevance score for results.

        Args:
            results: List of search results

        Returns:
            Weighted average relevance score

        Since:
            Version 1.0.0
        """
        if not results:
            return 0.0

        # Weight answer and top results more heavily
        weighted_scores = []
        for i, result in enumerate(results):
            weight = 1.0
            if result.metadata.get('is_answer'):
                weight = 2.0  # Double weight for answers
            elif i < 3:
                weight = 1.5  # 1.5x weight for top 3 results

            weighted_scores.append(result.relevance_score * weight)

        total_weight = len(results) + sum([0.5 if i < 3 else 0 for i in range(len(results))])
        if results and results[0].metadata.get('is_answer'):
            total_weight += 1  # Add extra weight for answer

        return sum(weighted_scores) / max(total_weight, 1)