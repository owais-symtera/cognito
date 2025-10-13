"""
LLM Summary Generator Service
Generates intelligent summaries using configured LLM providers and styles
"""
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
import anthropic
import structlog

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
            system_prompt = self._substitute_variables(
                category_config['system_prompt'],
                category_name=category_name,
                drug_name=drug_name,
                style_name=category_config['style_name'],
                target_word_count=str(category_config.get('target_word_count', 500))
            )

            user_prompt = self._substitute_variables(
                category_config['user_prompt_template'],
                category_name=category_name,
                drug_name=drug_name,
                merged_content=merged_content,
                custom_instructions=category_config.get('custom_instructions', ''),
                target_word_count=str(category_config.get('target_word_count', 500))
            )

            # Calculate max_tokens based on target_word_count to enforce length limit
            # Average: 1 word ≈ 1.3 tokens, add 20% buffer for safety
            target_word_count = category_config.get('target_word_count', 500)
            calculated_max_tokens = int(target_word_count * 1.3 * 1.2)  # word-to-token ratio with buffer

            # Use the smaller of calculated limit or provider default to enforce target length
            effective_max_tokens = min(calculated_max_tokens, provider_config['max_tokens'])

            logger.info(
                "Summary length enforcement",
                target_words=target_word_count,
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

