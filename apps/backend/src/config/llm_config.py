from typing import List, Dict, Optional, Any
"""
LLM Model Configuration Management.

Centralizes all LLM model selection and configuration from environment variables.
Supports multiple providers with fallback configurations.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class LLMModelConfig:
    """
    Configuration for a specific LLM model.

    Attributes:
        provider: Provider name (openai, anthropic, google, etc.)
        model_name: Specific model identifier
        api_key: API key for authentication
        base_url: Optional custom base URL
        max_tokens: Maximum tokens for response
        temperature_default: Default temperature setting
        cost_per_input_token: Cost per input token in USD
        cost_per_output_token: Cost per output token in USD
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Since:
        Version 1.0.0
    """
    provider: str
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature_default: float = 0.7
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0
    timeout: int = 30
    max_retries: int = 3


class LLMConfigManager:
    """
    Manages LLM model configurations from environment variables.

    Provides centralized configuration for all AI providers used in
    pharmaceutical intelligence gathering.

    Example:
        >>> config_manager = LLMConfigManager()
        >>> openai_config = config_manager.get_provider_config('openai')
        >>> model_name = openai_config.model_name

    Since:
        Version 1.0.0
    """

    # Default model configurations (can be overridden by env vars)
    DEFAULT_MODELS = {
        'openai': {
            'model_name': 'gpt-4-turbo-preview',
            'base_url': 'https://api.openai.com/v1',
            'max_tokens': 4096,
            'temperature_default': 0.7,
            'cost_per_input_token': 0.00001,  # $0.01 per 1K tokens
            'cost_per_output_token': 0.00003,  # $0.03 per 1K tokens
            'timeout': 30,
            'max_retries': 3
        },
        'anthropic': {
            'model_name': 'claude-3-opus-20240229',
            'base_url': 'https://api.anthropic.com',
            'max_tokens': 4096,
            'temperature_default': 0.7,
            'cost_per_input_token': 0.000015,  # $0.015 per 1K tokens
            'cost_per_output_token': 0.000075,  # $0.075 per 1K tokens
            'timeout': 30,
            'max_retries': 3
        },
        'perplexity': {
            'model_name': 'pplx-70b-online',
            'base_url': 'https://api.perplexity.ai',
            'max_tokens': 4096,
            'temperature_default': 0.7,
            'cost_per_input_token': 0.00001,
            'cost_per_output_token': 0.00001,
            'timeout': 30,
            'max_retries': 3
        },
        'google': {
            'model_name': 'gemini-pro',
            'base_url': 'https://generativelanguage.googleapis.com/v1',
            'max_tokens': 4096,
            'temperature_default': 0.7,
            'cost_per_input_token': 0.000001,
            'cost_per_output_token': 0.000002,
            'timeout': 30,
            'max_retries': 3
        },
        'xai': {
            'model_name': 'grok-1',
            'base_url': 'https://api.x.ai/v1',
            'max_tokens': 4096,
            'temperature_default': 0.7,
            'cost_per_input_token': 0.00001,
            'cost_per_output_token': 0.00001,
            'timeout': 30,
            'max_retries': 3
        }
    }

    def __init__(self):
        """
        Initialize LLM configuration manager.

        Loads configurations from environment variables with fallbacks
        to default values.

        Since:
            Version 1.0.0
        """
        self.configs: Dict[str, LLMModelConfig] = {}
        self._load_configurations()

    def _load_configurations(self):
        """
        Load LLM configurations from environment variables.

        Environment variable format:
        - {PROVIDER}_API_KEY: API key for the provider
        - {PROVIDER}_MODEL_NAME: Model name override
        - {PROVIDER}_BASE_URL: Custom base URL
        - {PROVIDER}_MAX_TOKENS: Maximum tokens
        - {PROVIDER}_TEMPERATURE: Default temperature
        - {PROVIDER}_TIMEOUT: Request timeout
        - {PROVIDER}_MAX_RETRIES: Maximum retries

        Since:
            Version 1.0.0
        """
        # OpenAI Configuration
        if api_key := os.getenv('OPENAI_API_KEY'):
            self.configs['openai'] = self._create_config('openai', api_key)

        # Anthropic Configuration
        if api_key := os.getenv('ANTHROPIC_API_KEY'):
            self.configs['anthropic'] = self._create_config('anthropic', api_key)

        # Perplexity Configuration
        if api_key := os.getenv('PERPLEXITY_API_KEY'):
            self.configs['perplexity'] = self._create_config('perplexity', api_key)

        # Google Gemini Configuration
        if api_key := os.getenv('GEMINI_API_KEY'):
            self.configs['google'] = self._create_config('google', api_key)

        # X.AI Grok Configuration
        if api_key := os.getenv('GROK_API_KEY'):
            self.configs['xai'] = self._create_config('xai', api_key)

        # Tavily Configuration (search-specific)
        if api_key := os.getenv('TAVILY_API_KEY'):
            self.configs['tavily'] = LLMModelConfig(
                provider='tavily',
                model_name='tavily-search',
                api_key=api_key,
                base_url=os.getenv('TAVILY_BASE_URL', 'https://api.tavily.com'),
                max_tokens=int(os.getenv('TAVILY_MAX_RESULTS', '10')),
                temperature_default=0.0,  # Not applicable for search
                timeout=int(os.getenv('TAVILY_TIMEOUT', '30')),
                max_retries=int(os.getenv('TAVILY_MAX_RETRIES', '3'))
            )

        logger.info(
            "LLM configurations loaded",
            providers=list(self.configs.keys())
        )

    def _create_config(self, provider: str, api_key: str) -> LLMModelConfig:
        """
        Create LLM configuration for a provider.

        Args:
            provider: Provider name
            api_key: API key for authentication

        Returns:
            LLMModelConfig instance

        Since:
            Version 1.0.0
        """
        defaults = self.DEFAULT_MODELS.get(provider, {})
        env_prefix = provider.upper()

        return LLMModelConfig(
            provider=provider,
            model_name=os.getenv(
                f'{env_prefix}_MODEL_NAME',
                defaults.get('model_name', 'default')
            ),
            api_key=api_key,
            base_url=os.getenv(
                f'{env_prefix}_BASE_URL',
                defaults.get('base_url')
            ),
            max_tokens=int(os.getenv(
                f'{env_prefix}_MAX_TOKENS',
                str(defaults.get('max_tokens', 4096))
            )),
            temperature_default=float(os.getenv(
                f'{env_prefix}_TEMPERATURE',
                str(defaults.get('temperature_default', 0.7))
            )),
            cost_per_input_token=float(os.getenv(
                f'{env_prefix}_COST_INPUT',
                str(defaults.get('cost_per_input_token', 0.0))
            )),
            cost_per_output_token=float(os.getenv(
                f'{env_prefix}_COST_OUTPUT',
                str(defaults.get('cost_per_output_token', 0.0))
            )),
            timeout=int(os.getenv(
                f'{env_prefix}_TIMEOUT',
                str(defaults.get('timeout', 30))
            )),
            max_retries=int(os.getenv(
                f'{env_prefix}_MAX_RETRIES',
                str(defaults.get('max_retries', 3))
            ))
        )

    def get_provider_config(self, provider: str) -> Optional[LLMModelConfig]:
        """
        Get configuration for a specific provider.

        Args:
            provider: Provider name

        Returns:
            LLMModelConfig or None if not configured

        Since:
            Version 1.0.0
        """
        return self.configs.get(provider)

    def get_all_configs(self) -> Dict[str, LLMModelConfig]:
        """
        Get all configured LLM providers.

        Returns:
            Dictionary of provider configurations

        Since:
            Version 1.0.0
        """
        return self.configs.copy()

    def is_provider_configured(self, provider: str) -> bool:
        """
        Check if a provider is configured.

        Args:
            provider: Provider name

        Returns:
            True if provider is configured

        Since:
            Version 1.0.0
        """
        return provider in self.configs

    def get_available_providers(self) -> List[str]:
        """
        Get list of configured providers.

        Returns:
            List of provider names

        Since:
            Version 1.0.0
        """
        return list(self.configs.keys())

    def update_provider_config(
        self,
        provider: str,
        **kwargs
    ) -> Optional[LLMModelConfig]:
        """
        Update provider configuration at runtime.

        Args:
            provider: Provider name
            **kwargs: Configuration parameters to update

        Returns:
            Updated configuration or None

        Since:
            Version 1.0.0
        """
        if provider not in self.configs:
            logger.warning(f"Provider {provider} not configured")
            return None

        config = self.configs[provider]

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        logger.info(
            f"Updated configuration for {provider}",
            updates=kwargs
        )

        return config


# Global instance
llm_config = LLMConfigManager()


def get_llm_config() -> LLMConfigManager:
    """
    Get global LLM configuration manager instance.

    Returns:
        LLMConfigManager instance

    Since:
        Version 1.0.0
    """
    return llm_config