"""
LLM-Assisted Data Merger Service
Uses GPT-5-nano to intelligently merge conflicting pharmaceutical data from multiple sources
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import structlog
from .data_storage_service import DataStorageService

logger = structlog.get_logger(__name__)


class LLMMergerService:
    """Service for using LLM to assist with intelligent data merging"""

    def __init__(self):
        """Initialize OpenAI client for GPT-5-nano"""
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-5-nano"  # Fast, cheap model for merge assistance
        self.temperature = 1  # Default temperature (some models only support this)

    async def merge_conflicting_responses(
        self,
        category_name: str,
        drug_name: str,
        responses: List[Dict[str, Any]],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to merge conflicting responses from multiple providers

        Args:
            category_name: Pharmaceutical category
            drug_name: Drug name
            responses: List of provider responses with metadata
            request_id: Optional request ID for API logging

        Returns:
            Merged data with confidence scores and conflict resolutions
        """
        logger.info(
            "Starting LLM-assisted merge",
            category=category_name,
            drug=drug_name,
            response_count=len(responses)
        )

        # Prepare data for LLM
        merge_prompt = self._create_merge_prompt(
            category_name,
            drug_name,
            responses
        )

        try:
            # Call GPT-5-nano for merge assistance
            start_time = time.time()
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": merge_prompt
                    }
                ],
                response_format={"type": "json_object"}
            )
            response_time_ms = int((time.time() - start_time) * 1000)

            # Parse LLM response
            llm_response = json.loads(completion.choices[0].message.content)

            logger.info(
                "LLM merge completed",
                confidence=llm_response.get("overall_confidence", 0),
                conflicts_resolved=len(llm_response.get("conflicts_resolved", []))
            )

            # Log API usage
            if request_id:
                try:
                    await DataStorageService.store_api_usage_log(
                        request_id=request_id,
                        category_result_id=None,
                        api_provider="openai",
                        endpoint=self.model,
                        response_status=200,
                        response_time_ms=response_time_ms,
                        token_count=completion.usage.total_tokens,
                        total_cost=self._calculate_cost(completion.usage.total_tokens),
                        category_name=category_name,
                        prompt_text=f"Merge {len(responses)} sources for {drug_name}",
                        response_data={"confidence": llm_response.get("overall_confidence"), "conflicts": len(llm_response.get("conflicts_resolved", []))},
                        request_payload={"drug_name": drug_name, "sources": len(responses), "operation": "merge"}
                    )
                except Exception as log_error:
                    logger.warning("Failed to log API usage", error=str(log_error))

            return {
                "merged_content": llm_response.get("merged_content", ""),
                "confidence_score": llm_response.get("overall_confidence", 0.5),
                "conflicts_resolved": llm_response.get("conflicts_resolved", []),
                "data_quality_score": llm_response.get("data_quality_score", 0.7),
                "key_findings": llm_response.get("key_findings", []),
                "metadata": {
                    "merge_method": "llm_assisted",
                    "model": self.model,
                    "sources_merged": len(responses),
                    "tokens_used": completion.usage.total_tokens,
                    "cost_estimate": self._calculate_cost(completion.usage.total_tokens)
                }
            }

        except Exception as e:
            logger.error(
                "LLM merge failed",
                error=str(e),
                category=category_name
            )

            # Log failed API usage
            if request_id:
                try:
                    await DataStorageService.store_api_usage_log(
                        request_id=request_id,
                        category_result_id=None,
                        api_provider="openai",
                        endpoint=self.model,
                        response_status=500,
                        response_time_ms=0,
                        token_count=0,
                        total_cost=0.0,
                        category_name=category_name,
                        error_message=str(e),
                        request_payload={"drug_name": drug_name, "sources": len(responses), "operation": "merge", "error": True}
                    )
                except Exception as log_error:
                    logger.warning("Failed to log API usage for error", error=str(log_error))

            # Fallback to simple concatenation
            return self._fallback_merge(responses)

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM merger"""
        return """You are a pharmaceutical data merger AI. Your task is to intelligently merge data from multiple sources into a single, accurate, COMPREHENSIVE summary with MAXIMUM DETAIL.

                CRITICAL REQUIREMENTS:
                1. INCLUDE ALL DETAILS: Merge ALL data from ALL sources - do NOT omit information
                2. COMPREHENSIVE OUTPUT: The merged content should contain the UNION of all information from all sources
                3. PRESERVE TABLES: If sources contain tables, preserve ALL rows and columns in the merged output
                4. COMBINE LISTS COMPLETELY: Include the full union of all lists (side effects, indications, competitors, market data, etc.)
                5. PRESERVE NUMERICAL DATA: Include ALL numeric values, ranges, and statistics from all sources
                6. MAXIMIZE INFORMATION: The goal is MAXIMUM comprehensive detail, not brevity
                7. NEVER MENTION SOURCE PROVIDERS: DO NOT reference API providers, source names, ChatGPT, Perplexity, Gemini, OpenAI, or any data sources in the merged content
                8. NO SOURCE ATTRIBUTIONS: Remove all mentions like "Source 1", "According to ChatGPT", "Perplexity reports", etc.

                When merging:
                1. Identify CONFLICTS: When sources disagree, note the conflict WITHOUT mentioning sources
                2. Resolve using CONSENSUS: Prefer information that appears in multiple sources
                3. Prefer AUTHORITATIVE sources: Government agencies > Peer-reviewed > Industry > News
                4. Keep ALL NUMERIC data: When values differ, provide range and note the variance
                5. Combine LISTS COMPLETELY: Union of ALL items from all sources - do not skip items
                6. Maintain ACCURACY: Never fabricate information
                7. Track CONFIDENCE: Higher when sources agree, lower when they conflict
                8. PRESERVE COMPLETENESS: Include all data points, even if only from one source
                9. WRITE AS FACTUAL REPORT: The merged content should read as an authoritative report, NOT as "Source X says..."

                Output JSON format:
                {
                "merged_content": "COMPREHENSIVE merged text with ALL details from ALL sources...",
                "overall_confidence": 0.85,
                "data_quality_score": 0.90,
                "key_findings": ["finding1", "finding2", ...],
                "conflicts_resolved": [
                    {
                    "field": "dosage",
                    "sources": ["10mg (ChatGPT)", "15mg (Perplexity)"],
                    "resolution": "10-15mg range",
                    "confidence": 0.7
                    }
                ]
                }"""

    def _create_merge_prompt(
        self,
        category_name: str,
        drug_name: str,
        responses: List[Dict[str, Any]]
    ) -> str:
        """Create merge prompt for LLM"""

        prompt = f"""Merge the following {len(responses)} data sources about {category_name} for {drug_name}:

"""

        for i, resp in enumerate(responses, 1):
            content = resp.get("response", "")

            # Truncate only extremely long responses to fit in context window
            # Increased limit to preserve maximum detail for consolidation
            if len(str(content)) > 15000:
                content = str(content)[:15000] + "... [truncated]"

            prompt += f"""
=== DATA SOURCE {i} ===
{content}

---
"""

        prompt += """

CRITICAL INSTRUCTIONS:
1. Merge these data sources intelligently into a COMPREHENSIVE summary that includes ALL information
2. Include the COMPLETE union of all data, tables, lists, and details
3. DO NOT omit information - include everything from all sources
4. Resolve conflicts by noting disagreements and providing ranges (WITHOUT mentioning which source)
5. The merged content should be MORE detailed than any single source
6. Preserve ALL numeric data, market figures, statistics, and measurements
7. Combine ALL lists completely (do not skip items)
8. NEVER mention source providers, API names, ChatGPT, Perplexity, Gemini, or OpenAI in the merged content
9. DO NOT write "Source 1 says...", "According to Source 2...", etc.
10. Write as an authoritative factual report

Return JSON only with comprehensive merged_content."""

        return prompt

    def _fallback_merge(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback merge when LLM fails"""
        logger.warning("Using fallback merge (LLM unavailable)")

        # Simple concatenation WITHOUT provider names
        merged_content = "\n\n---\n\n".join([
            resp.get('response', '')
            for resp in responses
        ])

        return {
            "merged_content": merged_content,
            "confidence_score": 0.5,
            "conflicts_resolved": [],
            "data_quality_score": 0.6,
            "key_findings": [],
            "metadata": {
                "merge_method": "fallback_concatenation",
                "sources_merged": len(responses)
            }
        }

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate estimated cost for GPT-5-nano"""
        # GPT-5-nano pricing (example: $0.0001 per 1K tokens)
        cost_per_1k_tokens = 0.0001
        return (tokens / 1000) * cost_per_1k_tokens

    def _get_category_schema(self, category_name: str) -> Dict[str, Any]:
        """
        Get the expected STRUCTURE schema for each category.

        IMPORTANT: These schemas define STRUCTURE ONLY - no hardcoded values!
        The LLM must extract ALL actual values from the merged content.
        """
        schemas = {
            "Market Overview": {
                "current": [
                    {
                        "region": "<string: region name>",
                        "market_size_usd": "<string: with $ and unit like billion/million>",
                        "cagr": "<string: percentage with %>",
                        "year_range": "<string: e.g. 2019-2024>"
                    }
                ],
                "forecast": [
                    {
                        "region": "<string: region name>",
                        "market_size_usd": "<string: with $ and unit>",
                        "cagr": "<string: percentage with %>",
                        "year_range": "<string: e.g. 2024-2034>"
                    }
                ]
            },
            "Competitive Landscape": {
                "competitors": [
                    {
                        "competitor": "<string: company name>",
                        "brand": "<string: brand name>",
                        "dosage_form": "<string: form type>",
                        "market_share": "<string: percentage or range>"
                    }
                ]
            },
            "Physicochemical Profile": {
                "parameters": [
                    {
                        "parameter": "<string: parameter name>",
                        "value": "<string: extracted value from text>",
                        "unit": "<string: unit if applicable>"
                    }
                ]
            },
            "Pharmacokinetics": {
                "parameters": [
                    {
                        "parameter": "<string: parameter name>",
                        "value": "<string: extracted value>",
                        "unit": "<string: unit if applicable>"
                    }
                ]
            },
            "Dosage Forms": {
                "forms": [
                    {
                        "form": "<string: form type>",
                        "strengths": ["<string: strength with unit>"],
                        "available": "<string: Yes/No>"
                    }
                ]
            },
            "Current Formulations": {
                "formulations": [
                    {
                        "brand": "<string: brand name>",
                        "manufacturer": "<string: company>",
                        "dosage_form": "<string: form>",
                        "strength": "<string: strength>",
                        "approved": "<string: Yes/No>"
                    }
                ]
            },
            "Clinical Trials & Safety": {
                "trials": [
                    {
                        "trial_id": "<string: NCT number>",
                        "phase": "<string: phase>",
                        "status": "<string: status>",
                        "indication": "<string: indication>",
                        "participants": "<string: number>"
                    }
                ],
                "safety": [
                    {
                        "adverse_event": "<string: event name>",
                        "frequency": "<string: frequency>",
                        "severity": "<string: severity>"
                    }
                ]
            },
            "Commercial Opportunities": {
                "opportunities": [
                    {
                        "opportunity": "<string: opportunity description>",
                        "market_potential": "<string: High/Medium/Low>",
                        "estimated_value": "<string: value with currency>",
                        "timeframe": "<string: time estimate>"
                    }
                ]
            },
            "Investigational Formulations": {
                "formulations": [
                    {
                        "formulation": "<string: formulation type>",
                        "developer": "<string: company>",
                        "phase": "<string: phase>",
                        "status": "<string: status>",
                        "estimated_approval": "<string: year>"
                    }
                ]
            },
            "Regulatory & Patent Status": {
                "regulatory": [
                    {
                        "region": "<string: region>",
                        "status": "<string: status>",
                        "approval_date": "<string: YYYY-MM-DD>",
                        "indication": "<string: indication>"
                    }
                ],
                "patents": [
                    {
                        "patent_number": "<string: patent number>",
                        "title": "<string: patent title>",
                        "expiry_date": "<string: YYYY-MM-DD>",
                        "status": "<string: Active/Expired>"
                    }
                ]
            }
        }
        return schemas.get(category_name, {})

    async def extract_structured_data(
        self,
        merged_content: str,
        category_name: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from merged content

        Args:
            merged_content: Merged text content
            category_name: Category for extraction schema
            request_id: Optional request ID for API logging

        Returns:
            Structured data dictionary
        """
        schema = self._get_category_schema(category_name)

        if not schema:
            # Fallback to generic extraction for unknown categories
            extraction_prompt = f"""Extract structured data from this {category_name} text:

{merged_content[:3000]}

Return JSON with relevant fields for {category_name}."""
        else:
            extraction_prompt = f"""Extract structured data from this {category_name} text and format it according to the schema structure.

TEXT TO EXTRACT FROM:
{merged_content[:20000]}

REQUIRED OUTPUT SCHEMA STRUCTURE (the "<string: ...>" parts are placeholders showing data types - REPLACE them with actual extracted values):
{json.dumps(schema, indent=2)}

CRITICAL INSTRUCTIONS - READ CAREFULLY:

1. The schema shows the JSON STRUCTURE ONLY. The values like "<string: region name>" are PLACEHOLDERS showing what type of data to extract.

2. YOU MUST EXTRACT ALL ACTUAL VALUES FROM THE TEXT ABOVE. DO NOT use the placeholder strings as actual data!

3. EXAMPLE - For Physicochemical Profile:
   WRONG: {{"parameter": "Molecular Weight", "value": "<string: extracted value from text>", "unit": "Da"}}
   CORRECT: {{"parameter": "Molecular Weight", "value": "459.5", "unit": "Da"}}

4. Category-Specific Requirements:

   For Market Overview:
   - Extract ONLY "current" and "forecast" arrays
   - Include regions found in the text (Global, North America, Europe, Asia-Pacific, Latin America, Middle East & Africa)
   - Extract ACTUAL market sizes, CAGRs, and year ranges from the text
   - Format: "$20.1 billion" for sizes, "5.2%" for CAGR

   For Competitive Landscape:
   - Extract ONLY "competitors" array
   - Each competitor must have: competitor name, brand name, dosage_form, market_share
   - Extract ACTUAL competitor information from text

   For Physicochemical Profile:
   - Extract ONLY "parameters" array
   - REQUIRED parameters (search text for each, use "Not available" if truly missing):
     * Molecular Weight (Da)
     * Melting Point (°C) - MANDATORY, must search thoroughly
     * Log P (lipophilicity)
     * Solubility (with unit)
     * pKa
   - Extract ACTUAL numeric values from the text - DO NOT make up values!

   For Pharmacokinetics:
   - Extract ONLY "parameters" array
   - Include ACTUAL values for: Bioavailability, Protein Binding, Half-life, Metabolism, Excretion
   - DO NOT use example values - extract from text

   For Dosage Forms:
   - Extract ONLY "forms" array
   - List ACTUAL dosage forms and strengths mentioned in the text
   - DO NOT use generic examples like "325 mg, 500 mg" - extract actual drug-specific strengths

   For Current Formulations:
   - Extract ONLY "formulations" array
   - List ACTUAL brand names, manufacturers, and strengths from the text

5. If specific data is NOT found in the text after thorough search, use "Not available" - never make up or hallucinate values.

6. Return ONLY valid JSON matching the schema structure with ACTUAL EXTRACTED VALUES."""

        try:
            start_time = time.time()
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=1,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction expert. Extract pharmaceutical data from text and format it according to the provided schema structure. CRITICAL: The schema shows placeholders like '<string: ...>' - you MUST replace these with ACTUAL values extracted from the text. NEVER use placeholder text as actual data. Return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ],
                response_format={"type": "json_object"}
            )
            response_time_ms = int((time.time() - start_time) * 1000)

            structured_data = json.loads(completion.choices[0].message.content)

            logger.info(
                "Structured data extracted",
                category=category_name,
                fields=len(structured_data.keys())
            )

            # Log API usage
            if request_id:
                try:
                    await DataStorageService.store_api_usage_log(
                        request_id=request_id,
                        category_result_id=None,
                        api_provider="openai",
                        endpoint=self.model,
                        response_status=200,
                        response_time_ms=response_time_ms,
                        token_count=completion.usage.total_tokens,
                        total_cost=self._calculate_cost(completion.usage.total_tokens),
                        category_name=category_name,
                        prompt_text=f"Extract structured data for {category_name}",
                        response_data={"fields_extracted": len(structured_data.keys())},
                        request_payload={"category": category_name, "operation": "extract"}
                    )
                except Exception as log_error:
                    logger.warning("Failed to log API usage", error=str(log_error))

            return structured_data

        except Exception as e:
            logger.error("Structured extraction failed", error=str(e))

            # Log failed API usage
            if request_id:
                try:
                    await DataStorageService.store_api_usage_log(
                        request_id=request_id,
                        category_result_id=None,
                        api_provider="openai",
                        endpoint=self.model,
                        response_status=500,
                        response_time_ms=0,
                        token_count=0,
                        total_cost=0.0,
                        category_name=category_name,
                        error_message=str(e),
                        request_payload={"category": category_name, "operation": "extract", "error": True}
                    )
                except Exception as log_error:
                    logger.warning("Failed to log API usage for error", error=str(log_error))

            return {}
