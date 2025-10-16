"""
LLM Summary Generator Service
Generates intelligent summaries using configured LLM providers and styles
"""
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
import anthropic
import structlog
from .data_storage_service import DataStorageService

logger = structlog.get_logger(__name__)


class LLMSummaryGenerator:
    """Service for generating summaries using LLM providers"""

    def __init__(self, summary_config_service):
        """Initialize with summary configuration service"""
        self.config_service = summary_config_service

    async def generate_summary(
        self,
        request_id: str,
        category_name: str,
        drug_name: str,
        merged_content: str
    ) -> Dict[str, Any]:
        """
        Generate a summary for merged content based on category configuration

        Args:
            request_id: Request ID for tracking
            category_name: Category name (e.g., "Market Overview")
            drug_name: Drug name
            merged_content: Merged content to summarize

        Returns:
            Dictionary with generated summary and metadata
        """
        start_time = time.time()

        try:
            # CRITICAL: Validate data quality before sending to LLM
            quality_check = self._validate_data_quality(merged_content)

            if not quality_check['is_sufficient']:
                logger.warning(
                    "Insufficient data availability for LLM summary",
                    category=category_name,
                    quality_score=quality_check['quality_score'],
                    issues=quality_check['issues']
                )

                # Return a clear message instead of generating false summary
                return {
                    "summary": f"**Insufficient Data Availability for {category_name}**\n\n"
                               f"Unable to generate a meaningful summary for {drug_name} due to limited publicly available data.\n\n"
                               f"**Data Availability Issues:**\n" + "\n".join([f"- {issue}" for issue in quality_check['issues']]) + "\n\n"
                               f"**Data Availability Score:** {quality_check['quality_score']:.2f}/1.00 (Minimum required: 0.15)\n\n"
                               f"This category requires additional data from authoritative sources to generate a comprehensive summary.",
                    "style_name": "insufficient_data",
                    "provider": "system",
                    "model": "none",
                    "generation_time_ms": int((time.time() - start_time) * 1000),
                    "tokens_used": 0,
                    "cost_estimate": 0.0,
                    "success": False,
                    "error": "Insufficient data availability",
                    "quality_check": quality_check
                }

            logger.info(
                "Data quality validation passed",
                category=category_name,
                quality_score=quality_check['quality_score']
            )
            # Get category-specific summary configuration
            category_config = await self.config_service.get_category_summary_config(category_name)

            if not category_config or not category_config.get('enabled'):
                logger.warning(
                    "No summary configuration for category",
                    category=category_name
                )
                return self._create_fallback_response(
                    merged_content,
                    "No summary configuration found"
                )

            # Get active provider configuration
            provider_config = await self.config_service.get_active_summary_provider()

            if not provider_config:
                logger.error("No active summary provider configured")
                return self._create_fallback_response(
                    merged_content,
                    "No active provider"
                )

            # Prepare prompts with variable substitution
            # Note: target_word_count column now stores character count
            target_char_count = category_config.get('target_word_count', 3000)  # Default 3000 chars

            # Add safety instructions to prevent false information generation
            data_quality_instructions = """

CRITICAL DATA QUALITY REQUIREMENTS:
- NEVER make up, invent, or hallucinate information that is not present in the source data
- If specific data points are marked as "N/A", "Not available", "Unknown", or missing, you MUST explicitly state: "Data not available" or "No information publicly available"
- DO NOT use placeholder or example values - only use actual data from the source
- If the source data is insufficient or mostly null values, state clearly: "Limited data available. [Describe what IS available]. Additional information is not publicly available at this time."
- When data conflicts or is unclear, acknowledge the uncertainty rather than choosing arbitrary values
- Preserve actual numbers, dates, and facts exactly as stated in the source
- NEVER mention API providers, source names, ChatGPT, Perplexity, Gemini, OpenAI, or any data sources
- DO NOT write "Source 1 reports...", "According to ChatGPT...", "Perplexity indicates...", etc.
- Write as an authoritative factual report WITHOUT source attributions
"""

            system_prompt = self._substitute_variables(
                category_config['system_prompt'],
                category_name=category_name,
                drug_name=drug_name,
                style_name=category_config['style_name'],
                target_char_count=str(target_char_count)
            ) + data_quality_instructions

            user_prompt = self._substitute_variables(
                category_config['user_prompt_template'],
                category_name=category_name,
                drug_name=drug_name,
                merged_content=merged_content,
                custom_instructions=category_config.get('custom_instructions', ''),
                target_char_count=str(target_char_count)
            )

            # Calculate max_tokens based on target_char_count to enforce length limit
            # Average: 1 character ≈ 0.25 tokens (4 chars per token), add 20% buffer
            calculated_max_tokens = int(target_char_count * 0.25 * 1.2)

            # Use the smaller of calculated limit or provider default to enforce target length
            effective_max_tokens = min(calculated_max_tokens, provider_config['max_tokens'])

            logger.info(
                "Summary length enforcement",
                target_chars=target_char_count,
                calculated_tokens=calculated_max_tokens,
                provider_max_tokens=provider_config['max_tokens'],
                effective_max_tokens=effective_max_tokens
            )

            # Generate summary using configured provider with enforced max_tokens
            result = await self._call_llm_provider(
                provider_config=provider_config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                override_max_tokens=effective_max_tokens
            )

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Log API usage
            try:
                await DataStorageService.store_api_usage_log(
                    request_id=request_id,
                    category_result_id=None,
                    api_provider=provider_config['key'],
                    endpoint=provider_config['model'],
                    response_status=200,
                    response_time_ms=generation_time_ms,
                    token_count=result.get('tokens_used', 0),
                    total_cost=result.get('cost_estimate', 0.0),
                    category_name=category_name,
                    prompt_text=f"System: {system_prompt[:200]}... | User: {user_prompt[:200]}...",
                    response_data={"summary_length": len(result.get('summary', '')), "success": True},
                    request_payload={"drug_name": drug_name, "style": category_config['style_name']}
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))

            # Save to history
            await self.config_service.save_summary_history(
                request_id=request_id,
                category_name=category_name,
                drug_name=drug_name,
                summary_style_id=category_config['summary_style_id'],
                provider_name=provider_config['key'],
                model_name=provider_config['model'],
                temperature=provider_config['temperature'],
                max_tokens=provider_config['max_tokens'],
                input_merged_content=merged_content,
                generated_summary=result['summary'],
                tokens_used=result.get('tokens_used'),
                cost_estimate=result.get('cost_estimate'),
                generation_time_ms=generation_time_ms,
                success=True,
                metadata=result.get('metadata')
            )

            logger.info(
                "Summary generated successfully",
                request_id=request_id,
                category=category_name,
                provider=provider_config['key'],
                time_ms=generation_time_ms
            )

            return {
                "summary": result['summary'],
                "style_name": category_config['style_name'],
                "provider": provider_config['key'],
                "model": provider_config['model'],
                "generation_time_ms": generation_time_ms,
                "tokens_used": result.get('tokens_used'),
                "cost_estimate": result.get('cost_estimate'),
                "success": True
            }

        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Summary generation failed",
                request_id=request_id,
                error=str(e)
            )

            # Try to save failed attempt to history if we have config
            try:
                category_config = await self.config_service.get_category_summary_config(category_name)
                provider_config = await self.config_service.get_active_summary_provider()

                if category_config and provider_config:
                    await self.config_service.save_summary_history(
                        request_id=request_id,
                        category_name=category_name,
                        drug_name=drug_name,
                        summary_style_id=category_config['summary_style_id'],
                        provider_name=provider_config['key'],
                        model_name=provider_config['model'],
                        input_merged_content=merged_content,
                        generated_summary="",
                        generation_time_ms=generation_time_ms,
                        success=False,
                        error_message=str(e)
                    )

                    # Log failed API usage
                    try:
                        await DataStorageService.store_api_usage_log(
                            request_id=request_id,
                            category_result_id=None,
                            api_provider=provider_config['key'],
                            endpoint=provider_config['model'],
                            response_status=500,
                            response_time_ms=generation_time_ms,
                            token_count=0,
                            total_cost=0.0,
                            category_name=category_name,
                            error_message=str(e),
                            request_payload={"drug_name": drug_name, "error": True}
                        )
                    except Exception as log_error:
                        logger.warning("Failed to log API usage for error", error=str(log_error))
            except:
                pass  # Failed to save history, but don't crash

            return self._create_fallback_response(merged_content, str(e))

    def _substitute_variables(self, template: str, **kwargs) -> str:
        """Substitute variables in prompt template"""
        result = template
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    async def _call_llm_provider(
        self,
        provider_config: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        override_max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Call the configured LLM provider"""
        provider_key = provider_config['key']
        model = provider_config['model']
        temperature = provider_config['temperature']
        max_tokens = override_max_tokens if override_max_tokens is not None else provider_config['max_tokens']
        api_key = provider_config['api_key']

        if provider_key == 'openai':
            return await self._call_openai(
                api_key, model, system_prompt, user_prompt,
                temperature, max_tokens
            )
        elif provider_key == 'claude':
            return await self._call_anthropic(
                api_key, model, system_prompt, user_prompt,
                temperature, max_tokens
            )
        elif provider_key == 'gemini':
            return await self._call_gemini(
                api_key, model, system_prompt, user_prompt,
                temperature, max_tokens
            )
        elif provider_key == 'perplexity':
            return await self._call_perplexity(
                api_key, model, system_prompt, user_prompt,
                temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_key}")

    async def _call_openai(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call OpenAI API"""
        client = AsyncOpenAI(api_key=api_key)

        completion = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        summary = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens
        cost_estimate = self._calculate_openai_cost(model, tokens_used)

        return {
            "summary": summary,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "metadata": {"model": model}
        }

    async def _call_anthropic(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        client = anthropic.AsyncAnthropic(api_key=api_key)

        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        summary = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens
        cost_estimate = self._calculate_anthropic_cost(model, message.usage)

        return {
            "summary": summary,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "metadata": {"model": model}
        }

    async def _call_gemini(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call Google Gemini API"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai package is required for Gemini. "
                "Install it with: pip install google-generativeai"
            )

        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model)

        # Combine prompts for Gemini
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = await gemini_model.generate_content_async(
            combined_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )

        summary = response.text
        # Gemini doesn't provide token counts easily, estimate
        tokens_used = len(summary.split()) * 1.3  # rough estimate
        cost_estimate = 0.0  # Gemini pricing varies

        return {
            "summary": summary,
            "tokens_used": int(tokens_used),
            "cost_estimate": cost_estimate,
            "metadata": {"model": model}
        }

    async def _call_perplexity(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call Perplexity API (OpenAI-compatible)"""
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )

        completion = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        summary = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens if hasattr(completion.usage, 'total_tokens') else 0
        cost_estimate = 0.0  # Perplexity pricing varies

        return {
            "summary": summary,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "metadata": {"model": model}
        }

    def _calculate_openai_cost(self, model: str, tokens: int) -> float:
        """Calculate OpenAI cost estimate"""
        # Pricing as of 2024 (approximate)
        pricing = {
            "gpt-4o": 0.005 / 1000,  # $0.005 per 1K tokens
            "gpt-4": 0.03 / 1000,
            "gpt-3.5-turbo": 0.0015 / 1000,
        }

        rate = pricing.get(model, 0.005 / 1000)
        return tokens * rate

    def _calculate_anthropic_cost(self, model: str, usage) -> float:
        """Calculate Anthropic cost estimate"""
        # Pricing as of 2024 (approximate)
        input_rate = 0.015 / 1000  # $0.015 per 1K input tokens
        output_rate = 0.075 / 1000  # $0.075 per 1K output tokens

        input_cost = usage.input_tokens * input_rate
        output_cost = usage.output_tokens * output_rate
        return input_cost + output_cost

    def _validate_data_quality(self, merged_content: str) -> Dict[str, Any]:
        """
        Validate the quality of merged content before sending to LLM

        Detects:
        - Mostly null/N/A/empty values
        - Very short content
        - Repetitive placeholder text
        - Generic error messages

        Returns:
            Dictionary with is_sufficient, quality_score, and issues
        """
        if not merged_content or not merged_content.strip():
            return {
                "is_sufficient": False,
                "quality_score": 0.0,
                "issues": ["Content is empty or null"]
            }

        content = merged_content.strip().lower()
        content_length = len(content)
        issues = []
        quality_score = 1.0

        # Check 1: Minimum length (at least 200 characters of meaningful content)
        if content_length < 200:
            issues.append(f"Content too short ({content_length} chars, minimum 200)")
            quality_score -= 0.4

        # Check 2: Count null/N/A indicators
        null_indicators = [
            'not available', 'n/a', 'na', 'null', 'none', 'no data',
            'no information', 'not found', 'unknown', 'not specified',
            'data not available', 'information not available',
            'no results', 'not applicable', 'not disclosed'
        ]

        null_count = sum(content.count(indicator) for indicator in null_indicators)

        # If more than 30% of sentences contain null indicators, data is poor
        sentence_count = max(content.count('.'), content.count('\n'), 1)
        null_ratio = null_count / sentence_count

        if null_ratio > 0.3:
            issues.append(f"High ratio of null/N/A values ({null_count} occurrences in {sentence_count} sentences)")
            quality_score -= 0.4

        # Check 3: Detect placeholder patterns
        placeholder_patterns = [
            '<string:', '<number:', '[insert ', '[add ', '[fill ',
            '{{', '}}', 'placeholder', 'example value', 'sample data'
        ]

        placeholder_count = sum(content.count(pattern) for pattern in placeholder_patterns)
        if placeholder_count > 5:
            issues.append(f"Contains placeholder text ({placeholder_count} instances)")
            quality_score -= 0.3

        # Check 4: Detect error messages
        error_patterns = [
            'error:', 'failed to', 'exception:', 'could not',
            'unable to retrieve', 'request failed', 'api error',
            'timeout', 'connection error', 'invalid response'
        ]

        error_count = sum(content.count(pattern) for pattern in error_patterns)
        if error_count > 2:
            issues.append(f"Contains error messages ({error_count} instances)")
            quality_score -= 0.3

        # Check 5: Repetitive content (same phrase repeated many times)
        words = content.split()
        if len(words) > 0:
            word_diversity = len(set(words)) / len(words)
            if word_diversity < 0.3:  # Less than 30% unique words
                issues.append(f"Low content diversity ({word_diversity:.2f}, expected > 0.3)")
                quality_score -= 0.2

        # Check 6: Meaningful numeric data (at least some numbers for quantitative categories)
        numeric_chars = sum(c.isdigit() for c in content)
        numeric_ratio = numeric_chars / content_length if content_length > 0 else 0

        # For quantitative categories, expect at least 2% numeric content
        if numeric_ratio < 0.02 and content_length > 500:
            # Only penalize if it's a long response with almost no numbers
            issues.append(f"Very little numeric data ({numeric_ratio:.2%}, expected > 2%)")
            quality_score -= 0.1

        # Check 7: Table data completeness (detect tables with mostly empty rows)
        # Look for table-like structures with row separators
        if '|' in content or '\n' in content:
            lines = content.split('\n')
            table_rows = [line for line in lines if '|' in line or ':' in line]

            if len(table_rows) > 5:  # Only check if we have a table-like structure
                # Count rows that are mostly empty (very short or only separators)
                empty_rows = 0
                data_rows = 0

                for row in table_rows:
                    # Remove table separators and whitespace
                    cleaned_row = row.replace('|', '').replace('-', '').replace('_', '').strip()

                    # Check if row is empty or has only null indicators
                    if len(cleaned_row) < 10 or cleaned_row.lower() in ['', 'n/a', 'na', 'not available', 'none', 'null']:
                        empty_rows += 1
                    else:
                        data_rows += 1

                # If more than 60% of rows are empty, flag it
                if data_rows > 0:
                    empty_ratio = empty_rows / (empty_rows + data_rows)
                    if empty_ratio > 0.60:
                        issues.append(f"Table has mostly empty rows ({empty_rows} empty out of {empty_rows + data_rows} total, {empty_ratio:.0%} empty)")
                        quality_score -= 0.5  # Heavy penalty for empty tables

        # Ensure quality score doesn't go below 0
        quality_score = max(0.0, quality_score)

        # RELAXED threshold: Allow partial summaries if there's SOME data
        # Only reject if quality is extremely poor (< 0.15) or too many critical issues (>= 5)
        # This allows summaries with partial data like "2 rows filled, 8 empty"
        is_sufficient = quality_score >= 0.15 and len(issues) < 5

        logger.info(
            "Data quality validation",
            quality_score=quality_score,
            is_sufficient=is_sufficient,
            issues_count=len(issues),
            content_length=content_length
        )

        return {
            "is_sufficient": is_sufficient,
            "quality_score": quality_score,
            "issues": issues,
            "content_length": content_length,
            "null_ratio": null_ratio
        }

    def _create_fallback_response(
        self,
        merged_content: str,
        error: str
    ) -> Dict[str, Any]:
        """Create a fallback response when LLM generation fails"""
        # Simple truncation fallback
        max_len = 1000
        fallback_summary = merged_content[:max_len]
        if len(merged_content) > max_len:
            fallback_summary += "... [truncated]"

        return {
            "summary": fallback_summary,
            "style_name": "fallback",
            "provider": "fallback",
            "model": "none",
            "generation_time_ms": 0,
            "tokens_used": 0,
            "cost_estimate": 0.0,
            "success": False,
            "error": error
        }

