"""
Category management API endpoints for CognitoAI Engine pharmaceutical platform.

Provides RESTful API endpoints for managing pharmaceutical category
configurations with comprehensive audit trails and dependency validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ...core.category_manager import CategoryManager
from ...database.connection import get_db_session
from ...schemas.categories import (
    CategoryResponse,
    CategoryUpdateRequest,
    CategoryStatusRequest,
    CategoryDependencyResponse,
    CategoryExportResponse,
    CategoryImportRequest,
    CategoryImportResponse
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    responses={404: {"description": "Category not found"}}
)


async def get_current_user_id() -> str:
    """
    Get current user ID from authentication context.

    This is a placeholder - implement proper authentication.

    Returns:
        Current user ID

    Since:
        Version 1.0.0
    """
    # TODO: Implement proper authentication
    return "system_user"


async def get_correlation_id() -> str:
    """
    Get correlation ID for request tracking.

    Returns:
        Request correlation ID

    Since:
        Version 1.0.0
    """
    # TODO: Implement proper correlation ID from headers
    import uuid
    return str(uuid.uuid4())


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    phase: Optional[int] = Query(None, ge=1, le=2, description="Filter by phase"),
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> List[Dict[str, Any]]:
    """
    List pharmaceutical categories.

    Retrieves all pharmaceutical categories with optional filtering by
    active status and processing phase.

    Args:
        include_inactive: Whether to include inactive categories
        phase: Optional phase filter (1 or 2)
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        List of category configurations

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        if phase is not None:
            categories = await manager.get_categories_by_phase(phase)
        elif include_inactive:
            categories = await manager.get_all_categories(include_inactive=True)
        else:
            categories = await manager.get_active_categories()

        logger.info(
            "Categories retrieved",
            count=len(categories),
            include_inactive=include_inactive,
            phase=phase,
            user_id=user_id
        )

        return categories

    except Exception as e:
        logger.error(
            "Failed to retrieve categories",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Get specific pharmaceutical category configuration.

    Args:
        category_id: Category identifier
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Category configuration

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)
        categories = await manager.get_all_categories(include_inactive=True)

        category = next((cat for cat in categories if cat["id"] == category_id), None)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found"
            )

        return category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve category",
            category_id=category_id,
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve category: {str(e)}"
        )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    update_request: CategoryUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Update pharmaceutical category configuration.

    Updates category configuration with comprehensive audit logging
    for pharmaceutical regulatory compliance.

    Args:
        category_id: Category identifier
        update_request: Configuration updates
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Updated category configuration

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        category = await manager.update_category(
            category_id,
            update_request.dict(exclude_unset=True)
        )

        logger.info(
            "Category configuration updated",
            category_id=category_id,
            updated_by=user_id
        )

        return category

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to update category",
            category_id=category_id,
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category: {str(e)}"
        )


@router.post("/{category_id}/enable", response_model=CategoryResponse)
async def enable_category(
    category_id: int,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Enable a pharmaceutical category.

    Enables category with immediate effect through cache invalidation.

    Args:
        category_id: Category identifier
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Updated category configuration

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        category = await manager.enable_category(category_id)

        logger.info(
            "Category enabled",
            category_id=category_id,
            enabled_by=user_id
        )

        return category

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to enable category",
            category_id=category_id,
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable category: {str(e)}"
        )


@router.post("/{category_id}/disable", response_model=CategoryResponse)
async def disable_category(
    category_id: int,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Disable a pharmaceutical category.

    Disables category with dependency validation to prevent disabling
    categories required by other enabled categories.

    Args:
        category_id: Category identifier
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Updated category configuration

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        category = await manager.disable_category(category_id)

        logger.info(
            "Category disabled",
            category_id=category_id,
            disabled_by=user_id
        )

        return category

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to disable category",
            category_id=category_id,
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable category: {str(e)}"
        )


@router.get("/{category_id}/dependencies", response_model=CategoryDependencyResponse)
async def get_category_dependencies(
    category_id: int,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Get category dependency information.

    Retrieves both categories that this category depends on and
    categories that depend on this category.

    Args:
        category_id: Category identifier
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Dependency information

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        dependencies = await manager.get_category_dependencies(category_id)

        return dependencies

    except Exception as e:
        logger.error(
            "Failed to retrieve category dependencies",
            category_id=category_id,
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dependencies: {str(e)}"
        )


@router.get("/export/configuration", response_model=CategoryExportResponse)
async def export_configuration(
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Export all category configurations.

    Exports all pharmaceutical category configurations for backup
    and disaster recovery purposes.

    Args:
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Export data with all category configurations

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        export_data = await manager.export_configuration()

        logger.info(
            "Category configuration exported",
            exported_by=user_id,
            category_count=len(export_data.get("categories", []))
        )

        return export_data

    except Exception as e:
        logger.error(
            "Failed to export configuration",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )


@router.post("/import/configuration", response_model=CategoryImportResponse)
async def import_configuration(
    import_request: CategoryImportRequest,
    validate_only: bool = Query(False, description="Only validate without importing"),
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Import category configurations.

    Imports pharmaceutical category configurations from backup with
    validation to ensure configuration integrity.

    Args:
        import_request: Configuration data to import
        validate_only: If True, only validate without importing
        db: Database session
        user_id: Current user ID
        correlation_id: Request correlation ID

    Returns:
        Import result with status and details

    Since:
        Version 1.0.0
    """
    try:
        manager = CategoryManager(db, user_id, correlation_id)

        result = await manager.import_configuration(
            import_request.dict(),
            validate_only=validate_only
        )

        logger.info(
            "Category configuration import attempted",
            imported_by=user_id,
            validate_only=validate_only,
            success=result.get("success", False)
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to import configuration",
            error=str(e),
            user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import configuration: {str(e)}"
        )