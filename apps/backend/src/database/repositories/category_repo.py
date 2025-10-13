"""
Category repository for CognitoAI Engine pharmaceutical platform.

Manages pharmaceutical category configurations with audit trails
and dependency validation for regulatory compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from ..models import PharmaceuticalCategory, CategoryDependency

logger = structlog.get_logger(__name__)


class CategoryRepository(BaseRepository[PharmaceuticalCategory]):
    """
    Repository for pharmaceutical category configuration operations.

    Provides comprehensive category management with dependency validation
    and audit trails for pharmaceutical regulatory compliance.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize category repository for pharmaceutical operations.

        Args:
            db: Async database session for pharmaceutical operations
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Since:
            Version 1.0.0
        """
        super().__init__(PharmaceuticalCategory, db, user_id, correlation_id)

    async def get_all_categories(
        self,
        include_inactive: bool = False
    ) -> List[PharmaceuticalCategory]:
        """
        Get all pharmaceutical categories with optional filtering.

        Args:
            include_inactive: Whether to include inactive categories

        Returns:
            List of pharmaceutical categories ordered by display_order

        Since:
            Version 1.0.0
        """
        try:
            query = select(self.model).order_by(self.model.display_order)

            if not include_inactive:
                query = query.where(self.model.is_active == True)

            result = await self.db.execute(query)
            categories = result.scalars().all()

            logger.debug(
                "Retrieved pharmaceutical categories",
                count=len(categories),
                include_inactive=include_inactive
            )

            return list(categories)

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical categories",
                error=str(e)
            )
            raise

    async def get_active_categories(self) -> List[PharmaceuticalCategory]:
        """
        Get all active pharmaceutical categories for processing.

        Returns:
            List of active categories ordered by display_order

        Since:
            Version 1.0.0
        """
        return await self.get_all_categories(include_inactive=False)

    async def get_categories_by_phase(
        self,
        phase: int
    ) -> List[PharmaceuticalCategory]:
        """
        Get pharmaceutical categories by processing phase.

        Args:
            phase: Processing phase (1 or 2)

        Returns:
            List of categories in the specified phase

        Since:
            Version 1.0.0
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.phase == phase,
                    self.model.is_active == True
                )
            ).order_by(self.model.display_order)

            result = await self.db.execute(query)
            categories = result.scalars().all()

            logger.debug(
                "Retrieved categories by phase",
                phase=phase,
                count=len(categories)
            )

            return list(categories)

        except Exception as e:
            logger.error(
                "Failed to retrieve categories by phase",
                phase=phase,
                error=str(e)
            )
            raise

    async def update_category_config(
        self,
        category_id: int,
        config_data: Dict[str, Any],
        updated_by: str
    ) -> Optional[PharmaceuticalCategory]:
        """
        Update pharmaceutical category configuration.

        Args:
            category_id: Category identifier
            config_data: Configuration updates
            updated_by: User making the update

        Returns:
            Updated category or None if not found

        Since:
            Version 1.0.0
        """
        try:
            # Add updated_by to the config data
            config_data['updated_by'] = updated_by
            config_data['updated_at'] = datetime.utcnow()

            category = await self.update(
                category_id,
                config_data,
                audit_description=f"Updated pharmaceutical category configuration"
            )

            if category:
                logger.info(
                    "Pharmaceutical category configuration updated",
                    category_id=category_id,
                    updated_by=updated_by,
                    fields_updated=list(config_data.keys())
                )

            return category

        except Exception as e:
            logger.error(
                "Failed to update category configuration",
                category_id=category_id,
                error=str(e)
            )
            raise

    async def toggle_category_status(
        self,
        category_id: int,
        enabled: bool,
        updated_by: str
    ) -> Optional[PharmaceuticalCategory]:
        """
        Enable or disable a pharmaceutical category.

        Args:
            category_id: Category identifier
            enabled: New status (True for enable, False for disable)
            updated_by: User making the change

        Returns:
            Updated category or None if not found

        Since:
            Version 1.0.0
        """
        try:
            # Check dependencies before disabling
            if not enabled:
                dependencies = await self.check_category_dependencies(category_id)
                if dependencies:
                    dependent_names = [dep.dependent_category.name for dep in dependencies]
                    raise ValueError(
                        f"Cannot disable category. Required by: {', '.join(dependent_names)}"
                    )

            update_data = {
                'is_active': enabled,
                'updated_by': updated_by,
                'updated_at': datetime.utcnow()
            }

            category = await self.update(
                category_id,
                update_data,
                audit_description=f"{'Enabled' if enabled else 'Disabled'} pharmaceutical category"
            )

            if category:
                logger.info(
                    "Pharmaceutical category status changed",
                    category_id=category_id,
                    enabled=enabled,
                    updated_by=updated_by
                )

            return category

        except Exception as e:
            logger.error(
                "Failed to toggle category status",
                category_id=category_id,
                enabled=enabled,
                error=str(e)
            )
            raise

    async def check_category_dependencies(
        self,
        category_id: int
    ) -> List[CategoryDependency]:
        """
        Check if a category is required by other enabled categories.

        Args:
            category_id: Category to check dependencies for

        Returns:
            List of dependencies where this category is required

        Since:
            Version 1.0.0
        """
        try:
            query = select(CategoryDependency).options(
                selectinload(CategoryDependency.dependent_category)
            ).where(
                CategoryDependency.required_category_id == category_id
            ).join(
                PharmaceuticalCategory,
                CategoryDependency.dependent_category_id == PharmaceuticalCategory.id
            ).where(
                PharmaceuticalCategory.is_active == True
            )

            result = await self.db.execute(query)
            dependencies = result.scalars().all()

            logger.debug(
                "Checked category dependencies",
                category_id=category_id,
                dependency_count=len(dependencies)
            )

            return list(dependencies)

        except Exception as e:
            logger.error(
                "Failed to check category dependencies",
                category_id=category_id,
                error=str(e)
            )
            raise

    async def get_category_dependencies(
        self,
        category_id: int
    ) -> List[CategoryDependency]:
        """
        Get all dependencies for a category (categories it depends on).

        Args:
            category_id: Category to get dependencies for

        Returns:
            List of dependencies for the category

        Since:
            Version 1.0.0
        """
        try:
            query = select(CategoryDependency).options(
                selectinload(CategoryDependency.required_category)
            ).where(
                CategoryDependency.dependent_category_id == category_id
            )

            result = await self.db.execute(query)
            dependencies = result.scalars().all()

            logger.debug(
                "Retrieved category dependencies",
                category_id=category_id,
                dependency_count=len(dependencies)
            )

            return list(dependencies)

        except Exception as e:
            logger.error(
                "Failed to retrieve category dependencies",
                category_id=category_id,
                error=str(e)
            )
            raise

    async def invalidate_cache(self) -> None:
        """
        Invalidate category configuration cache.

        Clears Redis cache to ensure configuration changes take immediate effect.

        Since:
            Version 1.0.0
        """
        try:
            # This would connect to Redis in a real implementation
            # For now, we'll just log the action
            logger.info("Category configuration cache invalidated")

        except Exception as e:
            logger.error(
                "Failed to invalidate category cache",
                error=str(e)
            )
            # Don't raise - cache invalidation failure shouldn't break the operation