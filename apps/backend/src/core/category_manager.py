"""
Category management logic for CognitoAI Engine pharmaceutical platform.

Handles category configuration, dependency validation, and backup/restore
functionality for pharmaceutical intelligence categories.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.repositories.category_repo import CategoryRepository
from ..database.models import PharmaceuticalCategory, CategoryDependency

logger = structlog.get_logger(__name__)


class CategoryManager:
    """
    Manager for pharmaceutical category configuration operations.

    Provides business logic for category management including dependency
    validation, configuration updates, and backup/restore functionality.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db_session: AsyncSession,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize category manager.

        Args:
            db_session: Database session for operations
            user_id: Current user for audit tracking
            correlation_id: Correlation ID for request tracking

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.repo = CategoryRepository(db_session, user_id, correlation_id)

    async def get_all_categories(
        self,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all pharmaceutical categories as dictionaries.

        Args:
            include_inactive: Whether to include inactive categories

        Returns:
            List of category dictionaries with full configuration

        Since:
            Version 1.0.0
        """
        categories = await self.repo.get_all_categories(include_inactive)

        return [
            self._category_to_dict(cat) for cat in categories
        ]

    async def get_active_categories(self) -> List[Dict[str, Any]]:
        """
        Get all active pharmaceutical categories.

        Returns:
            List of active category dictionaries

        Since:
            Version 1.0.0
        """
        categories = await self.repo.get_active_categories()

        return [
            self._category_to_dict(cat) for cat in categories
        ]

    async def get_categories_by_phase(self, phase: int) -> List[Dict[str, Any]]:
        """
        Get categories by processing phase.

        Args:
            phase: Processing phase (1 or 2)

        Returns:
            List of category dictionaries in the specified phase

        Since:
            Version 1.0.0
        """
        if phase not in [1, 2]:
            raise ValueError("Phase must be 1 or 2")

        categories = await self.repo.get_categories_by_phase(phase)

        return [
            self._category_to_dict(cat) for cat in categories
        ]

    async def update_category(
        self,
        category_id: int,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update category configuration.

        Args:
            category_id: Category to update
            update_data: Configuration updates

        Returns:
            Updated category dictionary

        Raises:
            ValueError: If category not found or update invalid

        Since:
            Version 1.0.0
        """
        if not self.user_id:
            raise ValueError("User ID required for category updates")

        # Validate update data
        self._validate_category_update(update_data)

        category = await self.repo.update_category_config(
            category_id,
            update_data,
            self.user_id
        )

        if not category:
            raise ValueError(f"Category {category_id} not found")

        # Invalidate cache after update
        await self.repo.invalidate_cache()

        logger.info(
            "Category configuration updated",
            category_id=category_id,
            updated_by=self.user_id
        )

        return self._category_to_dict(category)

    async def enable_category(self, category_id: int) -> Dict[str, Any]:
        """
        Enable a pharmaceutical category.

        Args:
            category_id: Category to enable

        Returns:
            Updated category dictionary

        Raises:
            ValueError: If category not found

        Since:
            Version 1.0.0
        """
        if not self.user_id:
            raise ValueError("User ID required for category status changes")

        category = await self.repo.toggle_category_status(
            category_id,
            True,
            self.user_id
        )

        if not category:
            raise ValueError(f"Category {category_id} not found")

        # Invalidate cache after status change
        await self.repo.invalidate_cache()

        logger.info(
            "Category enabled",
            category_id=category_id,
            enabled_by=self.user_id
        )

        return self._category_to_dict(category)

    async def disable_category(self, category_id: int) -> Dict[str, Any]:
        """
        Disable a pharmaceutical category.

        Args:
            category_id: Category to disable

        Returns:
            Updated category dictionary

        Raises:
            ValueError: If category not found or has dependencies

        Since:
            Version 1.0.0
        """
        if not self.user_id:
            raise ValueError("User ID required for category status changes")

        # Check dependencies before disabling
        dependencies = await self.repo.check_category_dependencies(category_id)
        if dependencies:
            dependent_names = [dep.dependent_category.name for dep in dependencies]
            raise ValueError(
                f"Cannot disable category. Required by: {', '.join(dependent_names)}"
            )

        category = await self.repo.toggle_category_status(
            category_id,
            False,
            self.user_id
        )

        if not category:
            raise ValueError(f"Category {category_id} not found")

        # Invalidate cache after status change
        await self.repo.invalidate_cache()

        logger.info(
            "Category disabled",
            category_id=category_id,
            disabled_by=self.user_id
        )

        return self._category_to_dict(category)

    async def get_category_dependencies(
        self,
        category_id: int
    ) -> Dict[str, Any]:
        """
        Get dependency information for a category.

        Args:
            category_id: Category to check

        Returns:
            Dictionary with dependency information

        Since:
            Version 1.0.0
        """
        # Get categories this one depends on
        dependencies = await self.repo.get_category_dependencies(category_id)

        # Get categories that depend on this one
        dependents = await self.repo.check_category_dependencies(category_id)

        return {
            "category_id": category_id,
            "depends_on": [
                {
                    "id": dep.required_category_id,
                    "name": dep.required_category.name,
                    "description": dep.description
                }
                for dep in dependencies
            ],
            "required_by": [
                {
                    "id": dep.dependent_category_id,
                    "name": dep.dependent_category.name,
                    "description": dep.description
                }
                for dep in dependents
            ]
        }

    async def export_configuration(self) -> Dict[str, Any]:
        """
        Export all category configurations for backup.

        Returns:
            Dictionary with all category configurations

        Since:
            Version 1.0.0
        """
        categories = await self.repo.get_all_categories(include_inactive=True)

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_version": "1.0.0",
            "categories": [
                self._category_to_export_dict(cat) for cat in categories
            ]
        }

        logger.info(
            "Category configuration exported",
            category_count=len(categories),
            exported_by=self.user_id
        )

        return export_data

    async def import_configuration(
        self,
        import_data: Dict[str, Any],
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Import category configurations from backup.

        Args:
            import_data: Configuration data to import
            validate_only: If True, only validate without importing

        Returns:
            Import result with status and details

        Since:
            Version 1.0.0
        """
        if not self.user_id:
            raise ValueError("User ID required for configuration import")

        # Validate import data structure
        validation_result = self._validate_import_data(import_data)

        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"]
            }

        if validate_only:
            return {
                "success": True,
                "message": "Validation successful",
                "category_count": len(import_data.get("categories", []))
            }

        # Perform the import
        imported_count = 0
        errors = []

        for cat_data in import_data.get("categories", []):
            try:
                category_id = cat_data.get("id")
                if category_id:
                    update_data = {
                        "prompt_templates": cat_data.get("prompt_templates"),
                        "search_parameters": cat_data.get("search_parameters"),
                        "processing_rules": cat_data.get("processing_rules"),
                        "verification_criteria": cat_data.get("verification_criteria"),
                        "is_active": cat_data.get("is_active"),
                        "phase": cat_data.get("phase")
                    }

                    await self.repo.update_category_config(
                        category_id,
                        update_data,
                        self.user_id
                    )
                    imported_count += 1

            except Exception as e:
                errors.append(f"Failed to import category {cat_data.get('name')}: {str(e)}")
                logger.error(
                    "Failed to import category",
                    category_name=cat_data.get("name"),
                    error=str(e)
                )

        # Invalidate cache after import
        await self.repo.invalidate_cache()

        logger.info(
            "Category configuration imported",
            imported_count=imported_count,
            error_count=len(errors),
            imported_by=self.user_id
        )

        return {
            "success": imported_count > 0,
            "imported_count": imported_count,
            "errors": errors
        }

    def _category_to_dict(self, category: PharmaceuticalCategory) -> Dict[str, Any]:
        """Convert category model to dictionary."""
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "display_order": category.display_order,
            "phase": category.phase,
            "is_active": category.is_active,
            "search_parameters": category.search_parameters,
            "processing_rules": category.processing_rules,
            "prompt_templates": category.prompt_templates,
            "verification_criteria": category.verification_criteria,
            "conflict_resolution_strategy": category.conflict_resolution_strategy,
            "created_at": category.created_at.isoformat() if category.created_at else None,
            "updated_at": category.updated_at.isoformat() if category.updated_at else None,
            "updated_by": category.updated_by
        }

    def _category_to_export_dict(self, category: PharmaceuticalCategory) -> Dict[str, Any]:
        """Convert category model to export dictionary."""
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "phase": category.phase,
            "is_active": category.is_active,
            "prompt_templates": category.prompt_templates,
            "search_parameters": category.search_parameters,
            "processing_rules": category.processing_rules,
            "verification_criteria": category.verification_criteria,
            "conflict_resolution_strategy": category.conflict_resolution_strategy
        }

    def _validate_category_update(self, update_data: Dict[str, Any]) -> None:
        """Validate category update data."""
        # Validate phase if provided
        if "phase" in update_data:
            if update_data["phase"] not in [1, 2]:
                raise ValueError("Phase must be 1 or 2")

        # Validate JSON fields if provided
        json_fields = [
            "prompt_templates",
            "search_parameters",
            "processing_rules",
            "verification_criteria"
        ]

        for field in json_fields:
            if field in update_data:
                if not isinstance(update_data[field], dict):
                    raise ValueError(f"{field} must be a dictionary")

    def _validate_import_data(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate import data structure."""
        errors = []

        if not isinstance(import_data, dict):
            errors.append("Import data must be a dictionary")

        if "categories" not in import_data:
            errors.append("Import data must contain 'categories' field")

        if not isinstance(import_data.get("categories", []), list):
            errors.append("Categories must be a list")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }