"""
Repository for API provider configuration management.

Handles database operations for API provider configurations including
encryption, rate limits, and category associations.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from ..models import APIProviderConfig, CategoryAPIConfig
from .base import BaseRepository

logger = structlog.get_logger(__name__)


class APIProviderConfigRepository(BaseRepository[APIProviderConfig]):
    """
    Repository for managing API provider configurations.

    Handles CRUD operations and business logic for API provider
    configurations with pharmaceutical compliance.

    Since:
        Version 1.0.0
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize API provider config repository.

        Args:
            db: Database session

        Since:
            Version 1.0.0
        """
        super().__init__(APIProviderConfig, db)

    async def get_all_configs(self) -> List[APIProviderConfig]:
        """
        Get all API provider configurations.

        Returns:
            List of API provider configurations

        Since:
            Version 1.0.0
        """
        query = select(self.model).order_by(self.model.provider_name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_enabled_providers(self) -> List[APIProviderConfig]:
        """
        Get all globally enabled API providers.

        Returns:
            List of enabled provider configurations

        Since:
            Version 1.0.0
        """
        query = select(self.model).where(
            self.model.enabled_globally == True
        ).order_by(self.model.provider_name)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_provider_config(self, provider_name: str) -> Optional[APIProviderConfig]:
        """
        Get configuration for specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider configuration or None

        Since:
            Version 1.0.0
        """
        query = select(self.model).where(
            self.model.provider_name == provider_name
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_provider_config(
        self,
        provider_name: str,
        updates: Dict[str, Any]
    ) -> Optional[APIProviderConfig]:
        """
        Update provider configuration.

        Args:
            provider_name: Provider to update
            updates: Configuration updates

        Returns:
            Updated configuration or None

        Since:
            Version 1.0.0
        """
        config = await self.get_provider_config(provider_name)
        if not config:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()

        # Audit log the change
        await self.log_audit_trail(
            entity_type="APIProviderConfig",
            entity_id=config.id,
            action="update",
            changes=updates
        )

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def rotate_api_key(
        self,
        provider_name: str,
        new_encrypted_key: str
    ) -> bool:
        """
        Rotate API key for provider.

        Args:
            provider_name: Provider name
            new_encrypted_key: New encrypted API key

        Returns:
            True if successful

        Since:
            Version 1.0.0
        """
        config = await self.get_provider_config(provider_name)
        if not config:
            return False

        # Store old key version for rollback if needed
        old_version = config.key_version

        config.encrypted_api_key = new_encrypted_key
        config.key_version = old_version + 1
        config.updated_at = datetime.utcnow()

        # Audit log the key rotation
        await self.log_audit_trail(
            entity_type="APIProviderConfig",
            entity_id=config.id,
            action="key_rotation",
            changes={
                'old_version': old_version,
                'new_version': config.key_version
            }
        )

        await self.db.commit()
        logger.info(f"Rotated API key for {provider_name} to version {config.key_version}")
        return True

    async def update_rate_limits(
        self,
        provider_name: str,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        daily_quota: Optional[int] = None
    ) -> bool:
        """
        Update rate limits for provider.

        Args:
            provider_name: Provider name
            requests_per_minute: New RPM limit
            requests_per_hour: New RPH limit
            daily_quota: New daily quota

        Returns:
            True if successful

        Since:
            Version 1.0.0
        """
        config = await self.get_provider_config(provider_name)
        if not config:
            return False

        updates = {}
        if requests_per_minute is not None:
            config.requests_per_minute = requests_per_minute
            updates['requests_per_minute'] = requests_per_minute

        if requests_per_hour is not None:
            config.requests_per_hour = requests_per_hour
            updates['requests_per_hour'] = requests_per_hour

        if daily_quota is not None:
            config.daily_quota = daily_quota
            updates['daily_quota'] = daily_quota

        if updates:
            config.updated_at = datetime.utcnow()
            await self.log_audit_trail(
                entity_type="APIProviderConfig",
                entity_id=config.id,
                action="update_rate_limits",
                changes=updates
            )
            await self.db.commit()

        return True

    async def update_cost_config(
        self,
        provider_name: str,
        cost_per_request: Optional[float] = None,
        cost_per_token: Optional[float] = None
    ) -> bool:
        """
        Update cost configuration for provider.

        Args:
            provider_name: Provider name
            cost_per_request: Cost per API request
            cost_per_token: Cost per token (if applicable)

        Returns:
            True if successful

        Since:
            Version 1.0.0
        """
        config = await self.get_provider_config(provider_name)
        if not config:
            return False

        updates = {}
        if cost_per_request is not None:
            config.cost_per_request = cost_per_request
            updates['cost_per_request'] = cost_per_request

        if cost_per_token is not None:
            config.cost_per_token = cost_per_token
            updates['cost_per_token'] = cost_per_token

        if updates:
            config.updated_at = datetime.utcnow()
            await self.log_audit_trail(
                entity_type="APIProviderConfig",
                entity_id=config.id,
                action="update_cost_config",
                changes=updates
            )
            await self.db.commit()

        return True

    async def get_active_providers_for_category(
        self,
        category_name: str
    ) -> List[str]:
        """
        Get active API providers for a specific category.

        Args:
            category_name: Pharmaceutical category name

        Returns:
            List of active provider names

        Since:
            Version 1.0.0
        """
        # First check if there are category-specific configurations
        query = select(CategoryAPIConfig).where(
            and_(
                CategoryAPIConfig.category_name == category_name,
                CategoryAPIConfig.enabled == True
            )
        )
        result = await self.db.execute(query)
        category_configs = result.scalars().all()

        if category_configs:
            # Use category-specific configuration
            return [config.provider_name for config in category_configs]

        # Fall back to globally enabled providers
        enabled = await self.get_enabled_providers()
        return [config.provider_name for config in enabled]

    async def enable_provider_for_category(
        self,
        provider_name: str,
        category_name: str
    ) -> bool:
        """
        Enable provider for specific category.

        Args:
            provider_name: Provider to enable
            category_name: Category to enable for

        Returns:
            True if successful

        Since:
            Version 1.0.0
        """
        # Check if configuration exists
        query = select(CategoryAPIConfig).where(
            and_(
                CategoryAPIConfig.provider_name == provider_name,
                CategoryAPIConfig.category_name == category_name
            )
        )
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if config:
            config.enabled = True
            config.updated_at = datetime.utcnow()
        else:
            # Create new configuration
            config = CategoryAPIConfig(
                provider_name=provider_name,
                category_name=category_name,
                enabled=True
            )
            self.db.add(config)

        await self.log_audit_trail(
            entity_type="CategoryAPIConfig",
            entity_id=0,  # Will be set after commit
            action="enable",
            changes={
                'provider': provider_name,
                'category': category_name
            }
        )

        await self.db.commit()
        return True

    async def disable_provider_for_category(
        self,
        provider_name: str,
        category_name: str
    ) -> bool:
        """
        Disable provider for specific category.

        Args:
            provider_name: Provider to disable
            category_name: Category to disable for

        Returns:
            True if successful

        Since:
            Version 1.0.0
        """
        query = select(CategoryAPIConfig).where(
            and_(
                CategoryAPIConfig.provider_name == provider_name,
                CategoryAPIConfig.category_name == category_name
            )
        )
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if config:
            config.enabled = False
            config.updated_at = datetime.utcnow()

            await self.log_audit_trail(
                entity_type="CategoryAPIConfig",
                entity_id=config.id,
                action="disable",
                changes={
                    'provider': provider_name,
                    'category': category_name
                }
            )

            await self.db.commit()
            return True

        return False

    async def create_default_providers(self):
        """
        Create default provider configurations if they don't exist.

        Since:
            Version 1.0.0
        """
        default_providers = [
            {
                'provider_name': 'chatgpt',
                'enabled_globally': True,
                'requests_per_minute': 60,
                'requests_per_hour': 1000,
                'daily_quota': 10000,
                'cost_per_request': 0.0,
                'cost_per_token': 0.00003,
                'config_json': {'model': 'gpt-4-turbo-preview'},
                'encrypted_api_key': ''  # To be set via admin interface
            },
            {
                'provider_name': 'perplexity',
                'enabled_globally': True,
                'requests_per_minute': 50,
                'requests_per_hour': 500,
                'daily_quota': 5000,
                'cost_per_request': 0.005,
                'cost_per_token': 0.0,
                'config_json': {'model': 'pplx-70b-online'},
                'encrypted_api_key': ''
            },
            {
                'provider_name': 'grok',
                'enabled_globally': False,
                'requests_per_minute': 40,
                'requests_per_hour': 400,
                'daily_quota': 4000,
                'cost_per_request': 0.01,
                'cost_per_token': 0.0,
                'config_json': {},
                'encrypted_api_key': ''
            },
            {
                'provider_name': 'gemini',
                'enabled_globally': False,
                'requests_per_minute': 60,
                'requests_per_hour': 600,
                'daily_quota': 6000,
                'cost_per_request': 0.0,
                'cost_per_token': 0.00002,
                'config_json': {'model': 'gemini-pro'},
                'encrypted_api_key': ''
            },
            {
                'provider_name': 'tavily',
                'enabled_globally': False,
                'requests_per_minute': 100,
                'requests_per_hour': 1000,
                'daily_quota': 10000,
                'cost_per_request': 0.003,
                'cost_per_token': 0.0,
                'config_json': {},
                'encrypted_api_key': ''
            }
        ]

        for provider_data in default_providers:
            # Check if exists
            existing = await self.get_provider_config(provider_data['provider_name'])
            if not existing:
                provider = APIProviderConfig(**provider_data)
                self.db.add(provider)
                logger.info(f"Created default config for {provider_data['provider_name']}")

        await self.db.commit()