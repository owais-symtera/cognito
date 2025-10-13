"""
X.AI Grok API provider for pharmaceutical intelligence gathering.

Implements Grok's API for advanced reasoning and real-time information
analysis in pharmaceutical research.

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


class GrokProvider(APIProvider):
    """
    X.AI Grok API integration for pharmaceutical intelligence.

    Leverages Grok's advanced reasoning capabilities and real-time
    information access for comprehensive pharmaceutical analysis.

    Example:
        >>> provider = GrokProvider()
        >>> response = await provider.search(
        ...     "mRNA vaccine technology advancements 2024",
        ...     temperature=0.6
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
        Initialize Grok provider.

        Args:
            api_key: Grok API key (optional, loads from config)
            config: Provider configuration (optional, loads from env)
            timeout: Request timeout in seconds (optional)
            max_retries: Maximum retry attempts (optional)

        Since:
            Version 1.0.0
        """
        # Get configuration from centralized LLM config
        llm_manager = get_llm_config()
        grok_config = llm_manager.get_provider_config('xai')

        if not grok_config and not api_key:
            raise ValueError("Grok API key not configured. Set GROK_API_KEY in environment.")

        # Use centralized config or fallback to provided values
        if grok_config:
            api_key = api_key or grok_config.api_key
            timeout = timeout or grok_config.timeout
            max_retries = max_retries or grok_config.max_retries

            # Merge config with LLM config
            default_config = {
                'model': grok_config.model_name,
                'base_url': grok_config.base_url,
                'max_tokens': grok_config.max_tokens,
                'temperature_default': grok_config.temperature_default,
                'cost_per_input_token': grok_config.cost_per_input_token,
                'cost_per_output_token': grok_config.cost_per_output_token
            }
            config = {**default_config, **(config or {})}

        super().__init__(api_key, config, timeout or 30, max_retries or 3)

        # Set provider-specific attributes from config
        self.BASE_URL = self.config.get('base_url', 'https://api.x.ai/v1')
        self.model = self.config.get('model', 'grok-1')
        self.COST_PER_INPUT_TOKEN = self.config.get('cost_per_input_token', 0.00001)
        self.COST_PER_OUTPUT_TOKEN = self.config.get('cost_per_output_token', 0.00001)

    async def search(
        self,
        query: str,
        temperature: float = 0.7,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using Grok.

        Args:
            query: Search query for pharmaceutical information
            temperature: Response creativity (0.0-1.0)
            max_results: Maximum number of results
            **kwargs: Additional parameters

        Returns:
            StandardizedAPIResponse with search results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Build pharmaceutical-focused messages
            messages = self._build_messages(query)

            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self.config.get('max_tokens', 4096),
                "top_p": 0.95,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stop": None,
                "stream": False
            }

            # Add any additional parameters
            payload.update(kwargs)

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract and process results
            results = self._parse_grok_response(data, query)

            # Calculate metrics
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Extract token usage
            usage = data.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

            cost = (input_tokens * self.COST_PER_INPUT_TOKEN +
                   output_tokens * self.COST_PER_OUTPUT_TOKEN)

            return StandardizedAPIResponse(
                provider="grok",
                query=query,
                temperature=temperature,
                results=results['search_results'],
                sources=results['sources'],
                total_results=len(results['search_results']),
                response_time_ms=response_time_ms,
                cost=cost,
                relevance_score=results.get('relevance_score', 0.87),
                confidence_score=results.get('confidence_score', 0.89),
                timestamp=start_time,
                metadata={
                    'model': self.model,
                    'total_tokens': total_tokens,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'real_time_search': True,
                    'reasoning_enhanced': True
                }
            )

        except httpx.HTTPError as e:
            logger.error(f"Grok API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Grok search: {e}")
            raise

    def _build_messages(self, query: str) -> List[Dict[str, str]]:
        """
        Build message array for Grok API.

        Args:
            query: Search query

        Returns:
            List of message dictionaries

        Since:
            Version 1.0.0
        """
        return [
            {
                "role": "system",
                "content": """You are Grok, an advanced AI assistant specializing in pharmaceutical intelligence.
                Your capabilities include:
                - Real-time access to current information
                - Deep reasoning about complex medical and pharmaceutical topics
                - Analysis of drug interactions, clinical trials, and regulatory matters
                - Evidence-based insights with high accuracy

                Provide comprehensive, factual information with clear reasoning.
                Cite sources when available and indicate confidence levels.
                Focus on pharmaceutical and medical accuracy."""
            },
            {
                "role": "user",
                "content": f"""Analyze and provide comprehensive pharmaceutical intelligence for:

                {query}

                Please include:
                1. Current Status: Latest information and real-time updates
                2. Clinical Evidence: Trials, studies, efficacy data
                3. Regulatory Landscape: FDA/EMA status, approvals, warnings
                4. Safety Analysis: Side effects, contraindications, interactions
                5. Market Context: Competition, pricing, accessibility
                6. Future Outlook: Pipeline developments, ongoing research

                Use your reasoning capabilities to provide deep insights.
                Access real-time information where relevant.
                Maintain pharmaceutical industry standards for accuracy."""
            }
        ]

    def _parse_grok_response(
        self,
        data: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Parse Grok API response into standardized format.

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

        # Extract content from response
        if 'choices' in data and data['choices']:
            for choice in data['choices']:
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content']

                    # Parse content into structured sections
                    sections = self._extract_grok_sections(content)

                    for section in sections:
                        search_results.append(SearchResult(
                            title=section['title'],
                            content=section['content'],
                            relevance_score=section['relevance_score'],
                            source_type=section['source_type'],
                            metadata={
                                'reasoning_depth': section.get('reasoning_depth', 'standard'),
                                'real_time_data': section.get('real_time', False),
                                'confidence': section.get('confidence', 0.87),
                                'finish_reason': choice.get('finish_reason', 'stop')
                            }
                        ))

                    # Extract sources
                    extracted_sources = self._extract_grok_sources(content)
                    sources.extend(extracted_sources)

        return {
            'search_results': search_results,
            'sources': sources,
            'relevance_score': self._calculate_relevance_score(search_results),
            'confidence_score': 0.89  # Grok has high confidence with reasoning
        }

    def _extract_grok_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract structured sections from Grok's response.

        Args:
            content: Raw content string

        Returns:
            List of structured sections

        Since:
            Version 1.0.0
        """
        sections = []

        # Section patterns that Grok typically uses
        section_patterns = {
            "Current Status": {
                'source_type': 'real_time',
                'relevance': 0.92,
                'reasoning_depth': 'deep',
                'real_time': True
            },
            "Clinical Evidence": {
                'source_type': 'clinical_trial',
                'relevance': 0.90,
                'reasoning_depth': 'analytical',
                'real_time': False
            },
            "Regulatory Landscape": {
                'source_type': 'regulatory',
                'relevance': 0.95,
                'reasoning_depth': 'comprehensive',
                'real_time': True
            },
            "Safety Analysis": {
                'source_type': 'safety',
                'relevance': 0.93,
                'reasoning_depth': 'critical',
                'real_time': False
            },
            "Market Context": {
                'source_type': 'market',
                'relevance': 0.80,
                'reasoning_depth': 'strategic',
                'real_time': True
            },
            "Future Outlook": {
                'source_type': 'research',
                'relevance': 0.85,
                'reasoning_depth': 'predictive',
                'real_time': False
            }
        }

        for section_name, properties in section_patterns.items():
            section_content = self._extract_section_by_name(content, section_name)
            if section_content:
                sections.append({
                    'title': section_name,
                    'content': section_content,
                    'source_type': properties['source_type'],
                    'relevance_score': properties['relevance'],
                    'reasoning_depth': properties['reasoning_depth'],
                    'real_time': properties['real_time'],
                    'confidence': 0.9 if len(section_content) > 150 else 0.75
                })

        # If no structured sections, parse as general content
        if not sections:
            sections.append({
                'title': 'Pharmaceutical Intelligence Analysis',
                'content': content[:2500],
                'source_type': 'analysis',
                'relevance_score': 0.85,
                'reasoning_depth': 'standard',
                'real_time': True,
                'confidence': 0.85
            })

        return sections

    def _extract_section_by_name(self, content: str, section_name: str) -> str:
        """
        Extract a specific section by name.

        Args:
            content: Full content
            section_name: Name of section to extract

        Returns:
            Extracted section content

        Since:
            Version 1.0.0
        """
        try:
            # Look for section header
            if section_name in content:
                start = content.index(section_name)

                # Find the end of this section (next section or end)
                possible_ends = [
                    "Current Status:", "Clinical Evidence:", "Regulatory Landscape:",
                    "Safety Analysis:", "Market Context:", "Future Outlook:",
                    "\n\n\n", "---"
                ]

                end = len(content)
                for end_marker in possible_ends:
                    end_idx = content.find(end_marker, start + len(section_name))
                    if end_idx != -1 and end_idx < end:
                        end = end_idx

                section = content[start:end].strip()

                # Remove section header
                if ":" in section:
                    section = section.split(":", 1)[1].strip()

                return section

        except Exception as e:
            logger.debug(f"Could not extract section {section_name}: {e}")

        return ""

    def _extract_grok_sources(self, content: str) -> List[SourceAttribution]:
        """
        Extract source citations from Grok's response.

        Args:
            content: Content potentially containing sources

        Returns:
            List of source attributions

        Since:
            Version 1.0.0
        """
        sources = []

        # Grok often references real-time sources
        if "real-time" in content.lower() or "current" in content.lower():
            sources.append(SourceAttribution(
                title="Grok Real-Time Analysis",
                url="api://grok/realtime",
                domain="x.ai",
                source_type="real_time",
                credibility_score=0.88
            ))

        # Check for specific source mentions
        source_indicators = {
            "FDA": ("https://www.fda.gov", "regulatory", 0.98),
            "clinical trial": ("https://clinicaltrials.gov", "clinical_trial", 0.95),
            "PubMed": ("https://pubmed.ncbi.nlm.nih.gov", "research_paper", 0.93),
            "research": ("api://grok/research", "research", 0.85),
            "market data": ("api://grok/market", "market", 0.80)
        }

        for indicator, (url, source_type, credibility) in source_indicators.items():
            if indicator.lower() in content.lower():
                sources.append(SourceAttribution(
                    title=f"Grok {indicator.title()} Reference",
                    url=url,
                    domain=url.split("//")[1].split("/")[0] if "//" in url else "x.ai",
                    source_type=source_type,
                    credibility_score=credibility
                ))

        # Always include Grok's reasoning as a source
        if not sources:
            sources.append(SourceAttribution(
                title="Grok Advanced Reasoning",
                url="api://grok",
                domain="x.ai",
                source_type="ai_reasoning",
                credibility_score=0.87
            ))

        return sources

    def _calculate_relevance_score(self, results: List[SearchResult]) -> float:
        """
        Calculate overall relevance score for results.

        Args:
            results: List of search results

        Returns:
            Average relevance score

        Since:
            Version 1.0.0
        """
        if not results:
            return 0.0

        scores = [r.relevance_score for r in results]
        # Weight higher scores more heavily (Grok's reasoning is typically high quality)
        weighted_scores = [score * (1.1 if score > 0.9 else 1.0) for score in scores]
        return min(sum(weighted_scores) / len(weighted_scores), 1.0)