"""
Simple LLM service wrapper for Phase 2 scoring.

Provides a unified interface for LLM calls across different providers.
"""
import os
from typing import Optional
import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)


class LLMService:
    """Simple LLM service for text generation."""

    def __init__(self):
        """Initialize LLM service with environment-based configuration."""
        self.provider = os.getenv('LLM_PROVIDER', 'openai')  # 'openai' or 'perplexity'
        self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('PERPLEXITY_API_KEY')
        self.model = os.getenv('LLM_MODEL', 'gpt-4')

        if self.provider == 'perplexity':
            self.base_url = 'https://api.perplexity.ai'
            self.model = os.getenv('LLM_MODEL', 'llama-3.1-sonar-large-128k-online')
        else:
            self.base_url = None

        if not self.api_key:
            logger.warning("No LLM API key configured - LLM features will not work")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using configured LLM.

        Args:
            prompt: User prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """
        try:
            client_kwargs = {'api_key': self.api_key}
            if self.base_url:
                client_kwargs['base_url'] = self.base_url

            client = AsyncOpenAI(**client_kwargs)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise
