"""
API provider management endpoints.

Provides RESTful endpoints for configuring and managing external
API providers for pharmaceutical intelligence gathering.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ...database.connection import get_db_session
from ...database.repositories.api_repo import APIProviderConfigRepository
from ...integrations.api_manager import MultiAPIManager
from ...schemas.api_providers import (
    APIProviderConfigResponse,
    APIProviderUpdateRequest,
    APIKeyRotationRequest,
    RateLimitUpdateRequest,
    CategoryAPIConfigRequest,
    ProviderStatusResponse
)
from ...auth.dependencies import require_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api-providers",
    tags=["api-providers"],
    dependencies=[Depends(require_api_key)]
)


@router.get("", response_model=List[APIProviderConfigResponse])
async def list_api_providers(
    include_disabled: bool = False,
    db: AsyncSession = Depends(get_db_session)
) -> List[Dict[str, Any]]:
    """
    List all API provider configurations.

    Args:
        include_disabled: Include disabled providers
        db: Database session

    Returns:
        List of API provider configurations

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        if include_disabled:
            configs = await repo.get_all_configs()
        else:
            configs = await repo.get_enabled_providers()

        return [
            {
                "provider_name": config.provider_name,
                "enabled_globally": config.enabled_globally,
                "requests_per_minute": config.requests_per_minute,
                "requests_per_hour": config.requests_per_hour,
                "daily_quota": config.daily_quota,
                "cost_per_request": config.cost_per_request,
                "cost_per_token": config.cost_per_token,
                "config_json": config.config_json,
                "key_version": config.key_version,
                "created_at": config.created_at,
                "updated_at": config.updated_at
            }
            for config in configs
        ]

    except Exception as e:
        logger.error(f"Failed to list API providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API providers"
        )


@router.get("/{provider_name}", response_model=APIProviderConfigResponse)
async def get_api_provider(
    provider_name: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get specific API provider configuration.

    Args:
        provider_name: Provider name
        db: Database session

    Returns:
        Provider configuration

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)
        config = await repo.get_provider_config(provider_name)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found"
            )

        return {
            "provider_name": config.provider_name,
            "enabled_globally": config.enabled_globally,
            "requests_per_minute": config.requests_per_minute,
            "requests_per_hour": config.requests_per_hour,
            "daily_quota": config.daily_quota,
            "cost_per_request": config.cost_per_request,
            "cost_per_token": config.cost_per_token,
            "config_json": config.config_json,
            "key_version": config.key_version,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider {provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider configuration"
        )


@router.put("/{provider_name}", response_model=APIProviderConfigResponse)
async def update_api_provider(
    provider_name: str,
    request: APIProviderUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Update API provider configuration.

    Args:
        provider_name: Provider to update
        request: Update request
        db: Database session

    Returns:
        Updated configuration

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        updates = request.dict(exclude_unset=True)
        config = await repo.update_provider_config(provider_name, updates)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found"
            )

        logger.info(f"Updated configuration for {provider_name}")

        return {
            "provider_name": config.provider_name,
            "enabled_globally": config.enabled_globally,
            "requests_per_minute": config.requests_per_minute,
            "requests_per_hour": config.requests_per_hour,
            "daily_quota": config.daily_quota,
            "cost_per_request": config.cost_per_request,
            "cost_per_token": config.cost_per_token,
            "config_json": config.config_json,
            "key_version": config.key_version,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update provider {provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider configuration"
        )


@router.post("/{provider_name}/rotate-key")
async def rotate_api_key(
    provider_name: str,
    request: APIKeyRotationRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Rotate API key for provider.

    Args:
        provider_name: Provider name
        request: Key rotation request
        db: Database session

    Returns:
        Success message with new key version

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        # In production, encrypt the key before storing
        # For now, we'll store it as-is (placeholder)
        encrypted_key = request.new_api_key  # TODO: Implement encryption

        success = await repo.rotate_api_key(provider_name, encrypted_key)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found"
            )

        logger.info(f"Rotated API key for {provider_name}")

        return {
            "message": f"API key rotated successfully for {provider_name}",
            "provider": provider_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rotate key for {provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key"
        )


@router.put("/{provider_name}/rate-limits")
async def update_rate_limits(
    provider_name: str,
    request: RateLimitUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Update rate limits for provider.

    Args:
        provider_name: Provider name
        request: Rate limit update
        db: Database session

    Returns:
        Success message

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        success = await repo.update_rate_limits(
            provider_name,
            request.requests_per_minute,
            request.requests_per_hour,
            request.daily_quota
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_name} not found"
            )

        logger.info(f"Updated rate limits for {provider_name}")

        return {
            "message": f"Rate limits updated successfully for {provider_name}",
            "provider": provider_name,
            "new_limits": {
                "requests_per_minute": request.requests_per_minute,
                "requests_per_hour": request.requests_per_hour,
                "daily_quota": request.daily_quota
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rate limits for {provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rate limits"
        )


@router.post("/{provider_name}/categories/{category_name}/enable")
async def enable_provider_for_category(
    provider_name: str,
    category_name: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Enable provider for specific category.

    Args:
        provider_name: Provider name
        category_name: Category name
        db: Database session

    Returns:
        Success message

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        success = await repo.enable_provider_for_category(provider_name, category_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to enable provider for category"
            )

        logger.info(f"Enabled {provider_name} for category {category_name}")

        return {
            "message": f"Provider {provider_name} enabled for category {category_name}",
            "provider": provider_name,
            "category": category_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable {provider_name} for {category_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable provider for category"
        )


@router.post("/{provider_name}/categories/{category_name}/disable")
async def disable_provider_for_category(
    provider_name: str,
    category_name: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Disable provider for specific category.

    Args:
        provider_name: Provider name
        category_name: Category name
        db: Database session

    Returns:
        Success message

    Since:
        Version 1.0.0
    """
    try:
        repo = APIProviderConfigRepository(db)

        success = await repo.disable_provider_for_category(provider_name, category_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to disable provider for category"
            )

        logger.info(f"Disabled {provider_name} for category {category_name}")

        return {
            "message": f"Provider {provider_name} disabled for category {category_name}",
            "provider": provider_name,
            "category": category_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable {provider_name} for {category_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable provider for category"
        )


@router.get("/status/all", response_model=Dict[str, ProviderStatusResponse])
async def get_all_provider_status(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get status of all configured providers.

    Returns:
        Dictionary with provider status information

    Since:
        Version 1.0.0
    """
    try:
        # Initialize API manager
        from ...core.config import settings
        import redis.asyncio as redis
        from ...config.logging import get_logger

        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

        audit_logger = get_logger(__name__)
        manager = MultiAPIManager(db, redis_client, audit_logger)

        await manager.initialize()
        status = await manager.get_provider_status()

        await manager.shutdown()
        await redis_client.close()

        return status

    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider status"
        )