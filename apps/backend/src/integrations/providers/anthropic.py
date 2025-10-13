"""
Anthropic Claude API provider for pharmaceutical intelligence gathering.

Implements Claude's API for advanced pharmaceutical analysis with
strong reasoning capabilities and comprehensive medical knowledge.

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


class AnthropicProvider(APIProvider):
    """
    Anthropic Claude API integration for pharmaceutical intelligence.

    Leverages Claude's advanced reasoning and comprehensive knowledge
    for in-depth pharmaceutical analysis and medical research.

    Example:
        >>> provider = AnthropicProvider()
        >>> response = await provider.search(
        ...     "CAR-T therapy manufacturing challenges and solutions",
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
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (optional, loads from config)
            config: Provider configuration (optional, loads from env)
            timeout: Request timeout in seconds (optional)
            max_retries: Maximum retry attempts (optional)

        Since:
            Version 1.0.0
        """
        # Get configuration from centralized LLM config
        llm_manager = get_llm_config()
        anthropic_config = llm_manager.get_provider_config('anthropic')

        if not anthropic_config and not api_key:
            raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in environment.")

        # Use centralized config or fallback to provided values
        if anthropic_config:
            api_key = api_key or anthropic_config.api_key
            timeout = timeout or anthropic_config.timeout
            max_retries = max_retries or anthropic_config.max_retries

            # Merge config with LLM config
            default_config = {
                'model': anthropic_config.model_name,
                'base_url': anthropic_config.base_url,
                'max_tokens': anthropic_config.max_tokens,
                'temperature_default': anthropic_config.temperature_default,
                'cost_per_input_token': anthropic_config.cost_per_input_token,
                'cost_per_output_token': anthropic_config.cost_per_output_token
            }
            config = {**default_config, **(config or {})}

        super().__init__(api_key, config, timeout or 30, max_retries or 3)

        # Set provider-specific attributes from config
        self.BASE_URL = self.config.get('base_url', 'https://api.anthropic.com')
        self.model = self.config.get('model', 'claude-3-opus-20240229')
        self.COST_PER_INPUT_TOKEN = self.config.get('cost_per_input_token', 0.000015)
        self.COST_PER_OUTPUT_TOKEN = self.config.get('cost_per_output_token', 0.000075)
        self.ANTHROPIC_VERSION = "2023-06-01"  # API version

    async def search(
        self,
        query: str,
        temperature: float = 0.7,
        max_results: int = 10,
        **kwargs
    ) -> StandardizedAPIResponse:
        """
        Execute pharmaceutical search using Claude.

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
            # Build the pharmaceutical-focused prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_user_prompt(query)

            # Prepare request payload
            payload = {
                "model": self.model,
                "max_tokens": self.config.get('max_tokens', 4096),
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "metadata": {
                    "user_id": "pharmaceutical_intelligence_system"
                }
            }

            # Add any additional parameters
            payload.update(kwargs)

            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.ANTHROPIC_VERSION,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract and process results
            results = self._parse_claude_response(data, query)

            # Calculate metrics
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Extract token usage
            usage = data.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)

            cost = (input_tokens * self.COST_PER_INPUT_TOKEN +
                   output_tokens * self.COST_PER_OUTPUT_TOKEN)

            return StandardizedAPIResponse(
                provider="anthropic",
                query=query,
                temperature=temperature,
                results=results['search_results'],
                sources=results['sources'],
                total_results=len(results['search_results']),
                response_time_ms=response_time_ms,
                cost=cost,
                relevance_score=results.get('relevance_score', 0.9),
                confidence_score=results.get('confidence_score', 0.92),
                timestamp=start_time,
                metadata={
                    'model': self.model,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'stop_reason': data.get('stop_reason', 'end_turn'),
                    'model_version': self.model
                }
            )

        except httpx.HTTPError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Claude search: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """
        Get pharmaceutical-specific system prompt for Claude.

        Returns:
            System prompt string

        Since:
            Version 1.0.0
        """
        return """You are Claude, an advanced AI assistant specializing in pharmaceutical intelligence and medical research.

Your expertise includes:
- Comprehensive knowledge of pharmaceuticals, drugs, and biologics
- Deep understanding of clinical trials, regulatory processes, and drug development
- Analysis of drug interactions, pharmacokinetics, and pharmacodynamics
- Knowledge of global regulatory frameworks (FDA, EMA, PMDA, etc.)
- Understanding of pharmaceutical market dynamics and competitive intelligence
- Expertise in medical literature and scientific research

Guidelines:
1. Provide accurate, evidence-based information with clear reasoning
2. Structure responses with clear sections for easy parsing
3. Include confidence levels for critical information
4. Cite authoritative sources when possible
5. Maintain pharmaceutical industry standards for accuracy and completeness
6. Consider safety and efficacy as primary concerns
7. Be thorough but concise in your analysis

You excel at complex reasoning and can provide nuanced analysis of pharmaceutical topics."""

    def _build_user_prompt(self, query: str) -> str:
        """
        Build user prompt for pharmaceutical query.

        Args:
            query: Original search query

        Returns:
            Enhanced prompt string

        Since:
            Version 1.0.0
        """
        return f"""Please provide comprehensive pharmaceutical intelligence for the following query:

{query}

Structure your response with these sections:

## Executive Summary
Brief overview of key findings and insights

## Clinical and Scientific Analysis
- Mechanism of action and pharmacology
- Clinical trial data and efficacy
- Safety profile and adverse events
- Drug interactions and contraindications

## Regulatory Landscape
- FDA/EMA approval status
- Regulatory pathway and requirements
- Recent regulatory actions or warnings
- Global regulatory variations

## Market Intelligence
- Competitive landscape
- Market size and growth potential
- Pricing and access considerations
- Pipeline developments

## Recent Developments
- Latest research findings
- Ongoing clinical trials
- Recent news and breakthroughs
- Future outlook

## Key Considerations
- Critical factors for decision-making
- Risk assessment
- Opportunities and challenges

For each section, indicate your confidence level (high/medium/low) and reasoning.
Focus on providing actionable intelligence for pharmaceutical professionals."""

    def _parse_claude_response(
        self,
        data: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Parse Claude API response into standardized format.

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
        if 'content' in data and data['content']:
            for content_block in data['content']:
                if content_block.get('type') == 'text':
                    text_content = content_block.get('text', '')

                    # Parse structured sections
                    sections = self._extract_claude_sections(text_content)

                    for section in sections:
                        search_results.append(SearchResult(
                            title=section['title'],
                            content=section['content'],
                            relevance_score=section['relevance_score'],
                            source_type=section['source_type'],
                            metadata={
                                'section_type': section['section_type'],
                                'confidence_level': section.get('confidence', 'high'),
                                'reasoning_depth': 'comprehensive',
                                'stop_reason': data.get('stop_reason', 'end_turn')
                            }
                        ))

                    # Extract source references
                    extracted_sources = self._extract_claude_sources(text_content)
                    sources.extend(extracted_sources)

        return {
            'search_results': search_results,
            'sources': sources,
            'relevance_score': self._calculate_relevance(search_results),
            'confidence_score': 0.92  # Claude typically has high confidence
        }

    def _extract_claude_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract structured sections from Claude's response.

        Args:
            content: Raw content string

        Returns:
            List of structured sections

        Since:
            Version 1.0.0
        """
        sections = []

        # Section patterns Claude typically uses
        section_mappings = {
            "Executive Summary": {
                'source_type': 'summary',
                'section_type': 'executive_summary',
                'relevance': 0.95,
                'confidence': 'high'
            },
            "Clinical and Scientific Analysis": {
                'source_type': 'clinical',
                'section_type': 'clinical_analysis',
                'relevance': 0.92,
                'confidence': 'high'
            },
            "Regulatory Landscape": {
                'source_type': 'regulatory',
                'section_type': 'regulatory_analysis',
                'relevance': 0.94,
                'confidence': 'high'
            },
            "Market Intelligence": {
                'source_type': 'market',
                'section_type': 'market_analysis',
                'relevance': 0.85,
                'confidence': 'medium'
            },
            "Recent Developments": {
                'source_type': 'news',
                'section_type': 'recent_developments',
                'relevance': 0.88,
                'confidence': 'medium'
            },
            "Key Considerations": {
                'source_type': 'analysis',
                'section_type': 'key_considerations',
                'relevance': 0.90,
                'confidence': 'high'
            }
        }

        for section_name, properties in section_mappings.items():
            section_content = self._extract_section_content(content, section_name)
            if section_content:
                # Determine confidence from content
                confidence = self._extract_confidence(section_content)

                sections.append({
                    'title': section_name,
                    'content': section_content,
                    'source_type': properties['source_type'],
                    'section_type': properties['section_type'],
                    'relevance_score': properties['relevance'],
                    'confidence': confidence or properties['confidence']
                })

        # If no structured sections found, treat as general content
        if not sections:
            sections.append({
                'title': 'Pharmaceutical Intelligence Analysis',
                'content': content[:3000],
                'source_type': 'comprehensive',
                'section_type': 'full_analysis',
                'relevance_score': 0.88,
                'confidence': 'high'
            })

        return sections

    def _extract_section_content(self, content: str, section_name: str) -> str:
        """
        Extract content for a specific section.

        Args:
            content: Full content
            section_name: Section header to look for

        Returns:
            Extracted section content

        Since:
            Version 1.0.0
        """
        try:
            # Look for section with ## or **
            patterns = [f"## {section_name}", f"**{section_name}**", section_name]

            for pattern in patterns:
                if pattern in content:
                    start = content.index(pattern)

                    # Find next section
                    next_sections = ["##", "**Executive", "**Clinical", "**Regulatory",
                                   "**Market", "**Recent", "**Key"]

                    end = len(content)
                    for next_section in next_sections:
                        next_idx = content.find(next_section, start + len(pattern))
                        if next_idx != -1 and next_idx < end:
                            end = next_idx

                    section = content[start:end].strip()

                    # Remove section header
                    for p in patterns:
                        section = section.replace(p, "").strip()

                    return section

        except Exception as e:
            logger.debug(f"Could not extract section {section_name}: {e}")

        return ""

    def _extract_confidence(self, content: str) -> Optional[str]:
        """
        Extract confidence level from content.

        Args:
            content: Section content

        Returns:
            Confidence level or None

        Since:
            Version 1.0.0
        """
        content_lower = content.lower()

        if "high confidence" in content_lower or "highly confident" in content_lower:
            return "high"
        elif "medium confidence" in content_lower or "moderate confidence" in content_lower:
            return "medium"
        elif "low confidence" in content_lower or "limited confidence" in content_lower:
            return "low"

        # Default based on content characteristics
        if len(content) > 500 and ("clinical trial" in content_lower or "fda" in content_lower):
            return "high"

        return None

    def _extract_claude_sources(self, content: str) -> List[SourceAttribution]:
        """
        Extract source references from Claude's response.

        Args:
            content: Content potentially containing sources

        Returns:
            List of source attributions

        Since:
            Version 1.0.0
        """
        sources = []

        # Common sources Claude might reference
        source_patterns = {
            "FDA": ("https://www.fda.gov", "regulatory", 0.98),
            "EMA": ("https://www.ema.europa.eu", "regulatory", 0.97),
            "clinical trial": ("https://clinicaltrials.gov", "clinical_trial", 0.95),
            "PubMed": ("https://pubmed.ncbi.nlm.nih.gov", "research_paper", 0.94),
            "WHO": ("https://www.who.int", "international_org", 0.96),
            "peer-reviewed": ("scientific_literature", "research_paper", 0.92),
            "research": ("medical_research", "research", 0.90)
        }

        content_lower = content.lower()
        for indicator, (url_or_type, source_type, credibility) in source_patterns.items():
            if indicator.lower() in content_lower:
                if url_or_type.startswith("http"):
                    url = url_or_type
                    domain = url.replace("https://", "").replace("www.", "").split("/")[0]
                else:
                    url = f"reference://{url_or_type}"
                    domain = "claude_reference"

                sources.append(SourceAttribution(
                    title=f"Claude {indicator.title()} Reference",
                    url=url,
                    domain=domain,
                    source_type=source_type,
                    credibility_score=credibility
                ))

        # Always include Claude's analysis as a source
        if not sources:
            sources.append(SourceAttribution(
                title="Claude Pharmaceutical Analysis",
                url="api://anthropic/claude",
                domain="anthropic.com",
                source_type="ai_analysis",
                credibility_score=0.90
            ))

        return sources

    def _calculate_relevance(self, results: List[SearchResult]) -> float:
        """
        Calculate overall relevance score.

        Args:
            results: List of search results

        Returns:
            Weighted average relevance score

        Since:
            Version 1.0.0
        """
        if not results:
            return 0.0

        # Weight executive summary and clinical analysis more heavily
        weighted_scores = []
        for result in results:
            weight = 1.0
            if result.metadata.get('section_type') == 'executive_summary':
                weight = 1.5
            elif result.metadata.get('section_type') == 'clinical_analysis':
                weight = 1.3
            elif result.metadata.get('section_type') == 'regulatory_analysis':
                weight = 1.2

            weighted_scores.append(result.relevance_score * weight)

        total_weight = sum([1.5 if r.metadata.get('section_type') == 'executive_summary'
                          else 1.3 if r.metadata.get('section_type') == 'clinical_analysis'
                          else 1.2 if r.metadata.get('section_type') == 'regulatory_analysis'
                          else 1.0 for r in results])

        return sum(weighted_scores) / max(total_weight, 1)