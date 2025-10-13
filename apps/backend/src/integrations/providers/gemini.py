"""
Google Gemini API provider for pharmaceutical intelligence gathering.

Implements Google's Gemini Pro API for advanced pharmaceutical analysis
with multi-modal capabilities and comprehensive medical knowledge.

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


class GeminiProvider(APIProvider):
    """
    Google Gemini API integration for pharmaceutical intelligence.

    Leverages Gemini Pro's advanced capabilities for comprehensive
    pharmaceutical analysis, drug interactions, and medical research.

    Example:
        >>> provider = GeminiProvider()
        >>> response = await provider.search(
        ...     "Immunotherapy combinations for melanoma treatment",
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
        Initialize Gemini provider.

        Args:
            api_key: Gemini API key (optional, loads from config)
            config: Provider configuration (optional, loads from env)
            timeout: Request timeout in seconds (optional)
            max_retries: Maximum retry attempts (optional)

        Since:
            Version 1.0.0
        """
        # Get configuration from centralized LLM config
        llm_manager = get_llm_config()
        gemini_config = llm_manager.get_provider_config('google')

        if not gemini_config and not api_key:
            raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in environment.")

        # Use centralized config or fallback to provided values
        if gemini_config:
            api_key = api_key or gemini_config.api_key
            timeout = timeout or gemini_config.timeout
            max_retries = max_retries or gemini_config.max_retries

            # Merge config with LLM config
            default_config = {
                'model': gemini_config.model_name,
                'base_url': gemini_config.base_url,
                'max_tokens': gemini_config.max_tokens,
                'temperature_default': gemini_config.temperature_default,
                'cost_per_input_token': gemini_config.cost_per_input_token,
                'cost_per_output_token': gemini_config.cost_per_output_token
            }
            config = {**default_config, **(config or {})}

        super().__init__(api_key, config, timeout or 30, max_retries or 3)

        # Set provider-specific attributes from config
        self.BASE_URL = self.config.get('base_url', 'https://generativelanguage.googleapis.com/v1')
        self.model = self.config.get('model', 'gemini-pro')
        self.COST_PER_INPUT_TOKEN = self.config.get('cost_per_input_token', 0.000001)
        self.COST_PER_OUTPUT_TOKEN = self.config.get('cost_per_output_token', 0.000002)

    async def search(
        self,
        query: str,
        temperature: float = 0.7,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using Gemini.

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
            # Prepare the pharmaceutical-focused prompt
            prompt = self._build_pharmaceutical_prompt(query)

            # Prepare request payload
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": self.config.get('max_tokens', 4096),
                    "stopSequences": []
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"  # Allow medical content
                    }
                ]
            }

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/models/{self.model}:generateContent",
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract and process results
            results = self._parse_gemini_response(data, query)

            # Calculate metrics
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Estimate token usage (Gemini doesn't always provide exact counts)
            input_tokens = len(prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(str(results.get('content', '')).split()) * 1.3
            cost = (input_tokens * self.COST_PER_INPUT_TOKEN +
                   output_tokens * self.COST_PER_OUTPUT_TOKEN)

            return StandardizedAPIResponse(
                provider="gemini",
                query=query,
                temperature=temperature,
                results=results['search_results'],
                sources=results['sources'],
                total_results=len(results['search_results']),
                response_time_ms=response_time_ms,
                cost=cost,
                relevance_score=results.get('relevance_score', 0.85),
                confidence_score=results.get('confidence_score', 0.9),
                timestamp=start_time,
                metadata={
                    'model': self.model,
                    'estimated_input_tokens': int(input_tokens),
                    'estimated_output_tokens': int(output_tokens),
                    'safety_filtered': results.get('safety_filtered', False)
                }
            )

        except httpx.HTTPError as e:
            logger.error(f"Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini search: {e}")
            raise

    def _build_pharmaceutical_prompt(self, query: str) -> str:
        """
        Build a pharmaceutical-focused prompt for Gemini.

        Args:
            query: Original search query

        Returns:
            Enhanced prompt string

        Since:
            Version 1.0.0
        """
        return f"""You are a pharmaceutical intelligence expert assistant.
        Provide comprehensive, accurate information about the following query:

        Query: {query}

        Please provide:
        1. **Clinical Information**: Drug mechanisms, indications, contraindications
        2. **Regulatory Status**: FDA approvals, regulatory warnings, global status
        3. **Clinical Trials**: Recent and ongoing trials, phases, results
        4. **Safety Profile**: Side effects, drug interactions, black box warnings
        5. **Market Intelligence**: Competitors, pricing, market share if available
        6. **Recent Developments**: Latest research, news, breakthroughs

        Format your response with clear sections and cite sources where possible.
        Focus on evidence-based, factual information from authoritative medical sources.
        Include confidence levels for critical information.
        """

    def _parse_gemini_response(
        self,
        data: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Parse Gemini API response into standardized format.

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
        safety_filtered = False

        # Check for safety filtering
        if 'promptFeedback' in data:
            feedback = data['promptFeedback']
            if 'blockReason' in feedback:
                safety_filtered = True
                logger.warning(f"Content filtered: {feedback.get('blockReason')}")

        # Extract content from candidates
        if 'candidates' in data and data['candidates']:
            for candidate in data['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            content = part['text']

                            # Parse structured sections from content
                            sections = self._extract_sections(content)

                            for section in sections:
                                search_results.append(SearchResult(
                                    title=section['title'],
                                    content=section['content'],
                                    relevance_score=section['relevance_score'],
                                    source_type=section['source_type'],
                                    metadata={
                                        'section_type': section['section_type'],
                                        'confidence': section.get('confidence', 0.85),
                                        'finish_reason': candidate.get('finishReason', 'STOP')
                                    }
                                ))

                            # Extract sources from content
                            extracted_sources = self._extract_sources_from_content(content)
                            sources.extend(extracted_sources)

        return {
            'search_results': search_results,
            'sources': sources,
            'relevance_score': self._calculate_relevance(search_results),
            'confidence_score': 0.9 if not safety_filtered else 0.7,
            'safety_filtered': safety_filtered,
            'content': data
        }

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract structured sections from Gemini response content.

        Args:
            content: Raw content string

        Returns:
            List of structured sections

        Since:
            Version 1.0.0
        """
        sections = []

        # Define section markers and their properties
        section_markers = {
            "Clinical Information": ("clinical", "clinical_data", 0.9),
            "Regulatory Status": ("regulatory", "regulatory", 0.95),
            "Clinical Trials": ("clinical_trial", "trials", 0.88),
            "Safety Profile": ("safety", "adverse_events", 0.92),
            "Market Intelligence": ("market", "commercial", 0.75),
            "Recent Developments": ("news", "recent", 0.8)
        }

        # Try to extract each section
        for marker, (source_type, section_type, relevance) in section_markers.items():
            if marker in content:
                section_content = self._extract_section_content(content, marker)
                if section_content:
                    sections.append({
                        'title': marker,
                        'content': section_content,
                        'source_type': source_type,
                        'section_type': section_type,
                        'relevance_score': relevance,
                        'confidence': 0.9 if len(section_content) > 100 else 0.7
                    })

        # If no structured sections found, return whole content
        if not sections:
            sections.append({
                'title': 'Pharmaceutical Intelligence Summary',
                'content': content[:2000],  # Limit length
                'source_type': 'general',
                'section_type': 'summary',
                'relevance_score': 0.8,
                'confidence': 0.85
            })

        return sections

    def _extract_section_content(self, content: str, section_marker: str) -> str:
        """
        Extract content for a specific section.

        Args:
            content: Full content
            section_marker: Section header to look for

        Returns:
            Extracted section content

        Since:
            Version 1.0.0
        """
        try:
            # Find the section
            start_idx = content.find(section_marker)
            if start_idx == -1:
                return ""

            # Find the next section or end of content
            next_markers = ["**", "\n\n", "1.", "2.", "3.", "4.", "5.", "6."]
            end_idx = len(content)

            for marker in next_markers:
                marker_idx = content.find(marker, start_idx + len(section_marker) + 1)
                if marker_idx != -1 and marker_idx < end_idx:
                    end_idx = marker_idx

            # Extract and clean the section
            section = content[start_idx:end_idx].strip()

            # Remove the section header
            if ":" in section:
                section = section.split(":", 1)[1].strip()

            return section

        except Exception as e:
            logger.error(f"Error extracting section: {e}")
            return ""

    def _extract_sources_from_content(self, content: str) -> List[SourceAttribution]:
        """
        Extract source citations from content.

        Args:
            content: Content potentially containing citations

        Returns:
            List of source attributions

        Since:
            Version 1.0.0
        """
        sources = []

        # Common pharmaceutical sources to look for
        known_sources = {
            "FDA": ("https://www.fda.gov", "regulatory", 0.98),
            "ClinicalTrials.gov": ("https://clinicaltrials.gov", "clinical_trial", 0.95),
            "PubMed": ("https://pubmed.ncbi.nlm.nih.gov", "research_paper", 0.93),
            "WHO": ("https://www.who.int", "regulatory", 0.96),
            "EMA": ("https://www.ema.europa.eu", "regulatory", 0.95),
            "NEJM": ("https://www.nejm.org", "medical_journal", 0.94),
            "Lancet": ("https://www.thelancet.com", "medical_journal", 0.94),
            "JAMA": ("https://jamanetwork.com", "medical_journal", 0.93)
        }

        for source_name, (url, source_type, credibility) in known_sources.items():
            if source_name in content:
                sources.append(SourceAttribution(
                    title=f"{source_name} Reference",
                    url=url,
                    domain=url.replace("https://", "").replace("www.", "").split("/")[0],
                    source_type=source_type,
                    credibility_score=credibility
                ))

        # If no specific sources found, add a general Gemini attribution
        if not sources:
            sources.append(SourceAttribution(
                title="Gemini AI Analysis",
                url="api://gemini",
                domain="google.com",
                source_type="ai_analysis",
                credibility_score=0.85
            ))

        return sources

    def _calculate_relevance(self, results: List[SearchResult]) -> float:
        """
        Calculate overall relevance score.

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
        return sum(scores) / len(scores)