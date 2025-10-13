"""
Unit tests for pharmaceutical category manager.

Tests category configuration management, dependency validation,
and backup/restore functionality for regulatory compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.category_manager import CategoryManager
from src.database.models import PharmaceuticalCategory, CategoryDependency


class TestCategoryManager:
    """
    Test suite for pharmaceutical category management operations.

    Tests all category manager functionality including configuration
    updates, dependency validation, and backup/restore operations.

    Since:
        Version 1.0.0
    """

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_category(self):
        """Create mock pharmaceutical category."""
        category = MagicMock(spec=PharmaceuticalCategory)
        category.id = 1
        category.name = "Clinical Trials & Studies"
        category.description = "Phase I-IV clinical trials"
        category.display_order = 1
        category.phase = 1
        category.is_active = True
        category.search_parameters = {"keywords": ["clinical trial"]}
        category.processing_rules = {"min_confidence": 0.8}
        category.prompt_templates = {"search": "Find trials for {drug_name}"}
        category.verification_criteria = {"required_fields": ["phase"]}
        category.conflict_resolution_strategy = "confidence_weighted"
        category.created_at = datetime.utcnow()
        category.updated_at = datetime.utcnow()
        category.updated_by = None
        return category

    @pytest.fixture
    def category_manager(self, mock_db_session):
        """Create category manager with mock session."""
        return CategoryManager(
            db_session=mock_db_session,
            user_id="test_user",
            correlation_id="test_correlation"
        )

    @pytest.mark.asyncio
    async def test_get_all_categories(
        self,
        category_manager,
        mock_category
    ):
        """
        Test retrieving all pharmaceutical categories.

        Verifies that all categories are retrieved and properly
        converted to dictionary format.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.get_all_categories = AsyncMock(
            return_value=[mock_category]
        )

        # Execute
        categories = await category_manager.get_all_categories()

        # Verify
        assert len(categories) == 1
        assert categories[0]["id"] == 1
        assert categories[0]["name"] == "Clinical Trials & Studies"
        assert categories[0]["phase"] == 1
        assert categories[0]["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_active_categories(
        self,
        category_manager,
        mock_category
    ):
        """
        Test retrieving only active categories.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.get_active_categories = AsyncMock(
            return_value=[mock_category]
        )

        # Execute
        categories = await category_manager.get_active_categories()

        # Verify
        assert len(categories) == 1
        assert categories[0]["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_categories_by_phase(
        self,
        category_manager,
        mock_category
    ):
        """
        Test retrieving categories by processing phase.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.get_categories_by_phase = AsyncMock(
            return_value=[mock_category]
        )

        # Execute
        categories = await category_manager.get_categories_by_phase(1)

        # Verify
        assert len(categories) == 1
        assert categories[0]["phase"] == 1

    @pytest.mark.asyncio
    async def test_get_categories_by_invalid_phase(
        self,
        category_manager
    ):
        """
        Test that invalid phase raises ValueError.

        Since:
            Version 1.0.0
        """
        with pytest.raises(ValueError, match="Phase must be 1 or 2"):
            await category_manager.get_categories_by_phase(3)

    @pytest.mark.asyncio
    async def test_update_category(
        self,
        category_manager,
        mock_category
    ):
        """
        Test updating category configuration.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.update_category_config = AsyncMock(
            return_value=mock_category
        )
        category_manager.repo.invalidate_cache = AsyncMock()

        # Execute
        update_data = {
            "phase": 2,
            "prompt_templates": {"search": "Updated prompt"}
        }
        result = await category_manager.update_category(1, update_data)

        # Verify
        assert result["id"] == 1
        category_manager.repo.update_category_config.assert_called_once()
        category_manager.repo.invalidate_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_category_without_user_id(
        self,
        mock_db_session
    ):
        """
        Test that update without user ID raises ValueError.

        Since:
            Version 1.0.0
        """
        manager = CategoryManager(mock_db_session, user_id=None)

        with pytest.raises(ValueError, match="User ID required"):
            await manager.update_category(1, {"phase": 2})

    @pytest.mark.asyncio
    async def test_enable_category(
        self,
        category_manager,
        mock_category
    ):
        """
        Test enabling a pharmaceutical category.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.toggle_category_status = AsyncMock(
            return_value=mock_category
        )
        category_manager.repo.invalidate_cache = AsyncMock()

        # Execute
        result = await category_manager.enable_category(1)

        # Verify
        assert result["id"] == 1
        category_manager.repo.toggle_category_status.assert_called_with(
            1, True, "test_user"
        )
        category_manager.repo.invalidate_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_category_with_dependencies(
        self,
        category_manager
    ):
        """
        Test that disabling category with dependencies raises error.

        Since:
            Version 1.0.0
        """
        # Setup mock dependency
        mock_dependency = MagicMock()
        mock_dependency.dependent_category.name = "Safety Surveillance"

        category_manager.repo.check_category_dependencies = AsyncMock(
            return_value=[mock_dependency]
        )

        # Execute and verify
        with pytest.raises(
            ValueError,
            match="Cannot disable category. Required by: Safety Surveillance"
        ):
            await category_manager.disable_category(1)

    @pytest.mark.asyncio
    async def test_disable_category_without_dependencies(
        self,
        category_manager,
        mock_category
    ):
        """
        Test successfully disabling category without dependencies.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.check_category_dependencies = AsyncMock(
            return_value=[]
        )
        category_manager.repo.toggle_category_status = AsyncMock(
            return_value=mock_category
        )
        category_manager.repo.invalidate_cache = AsyncMock()

        # Execute
        result = await category_manager.disable_category(1)

        # Verify
        assert result["id"] == 1
        category_manager.repo.toggle_category_status.assert_called_with(
            1, False, "test_user"
        )

    @pytest.mark.asyncio
    async def test_export_configuration(
        self,
        category_manager,
        mock_category
    ):
        """
        Test exporting category configurations.

        Since:
            Version 1.0.0
        """
        # Setup mock repository
        category_manager.repo.get_all_categories = AsyncMock(
            return_value=[mock_category]
        )

        # Execute
        export_data = await category_manager.export_configuration()

        # Verify
        assert "export_timestamp" in export_data
        assert "export_version" in export_data
        assert len(export_data["categories"]) == 1
        assert export_data["categories"][0]["id"] == 1
        assert export_data["categories"][0]["name"] == "Clinical Trials & Studies"

    @pytest.mark.asyncio
    async def test_import_configuration_validation(
        self,
        category_manager
    ):
        """
        Test import configuration validation.

        Since:
            Version 1.0.0
        """
        # Invalid import data
        invalid_data = {"invalid": "data"}

        # Execute
        result = await category_manager.import_configuration(
            invalid_data,
            validate_only=True
        )

        # Verify
        assert result["success"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_import_configuration_success(
        self,
        category_manager,
        mock_category
    ):
        """
        Test successful configuration import.

        Since:
            Version 1.0.0
        """
        # Valid import data
        import_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_version": "1.0.0",
            "categories": [
                {
                    "id": 1,
                    "name": "Clinical Trials & Studies",
                    "phase": 1,
                    "is_active": True,
                    "prompt_templates": {"search": "Find trials"}
                }
            ]
        }

        # Setup mock repository
        category_manager.repo.update_category_config = AsyncMock(
            return_value=mock_category
        )
        category_manager.repo.invalidate_cache = AsyncMock()

        # Execute
        result = await category_manager.import_configuration(import_data)

        # Verify
        assert result["success"] is True
        assert result["imported_count"] == 1
        assert len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_get_category_dependencies(
        self,
        category_manager
    ):
        """
        Test retrieving category dependency information.

        Since:
            Version 1.0.0
        """
        # Setup mock dependencies
        mock_dependency = MagicMock()
        mock_dependency.required_category_id = 3
        mock_dependency.required_category.name = "Side Effects"
        mock_dependency.description = "Required for safety"

        mock_dependent = MagicMock()
        mock_dependent.dependent_category_id = 11
        mock_dependent.dependent_category.name = "Safety Surveillance"
        mock_dependent.description = "Depends on this"

        category_manager.repo.get_category_dependencies = AsyncMock(
            return_value=[mock_dependency]
        )
        category_manager.repo.check_category_dependencies = AsyncMock(
            return_value=[mock_dependent]
        )

        # Execute
        result = await category_manager.get_category_dependencies(1)

        # Verify
        assert result["category_id"] == 1
        assert len(result["depends_on"]) == 1
        assert result["depends_on"][0]["name"] == "Side Effects"
        assert len(result["required_by"]) == 1
        assert result["required_by"][0]["name"] == "Safety Surveillance"

    @pytest.mark.asyncio
    async def test_validate_category_update_invalid_phase(
        self,
        category_manager
    ):
        """
        Test that invalid phase in update raises ValueError.

        Since:
            Version 1.0.0
        """
        # Invalid update data
        update_data = {"phase": 3}

        # Execute and verify
        with pytest.raises(ValueError, match="Phase must be 1 or 2"):
            category_manager._validate_category_update(update_data)

    @pytest.mark.asyncio
    async def test_validate_category_update_invalid_json_field(
        self,
        category_manager
    ):
        """
        Test that non-dict JSON fields raise ValueError.

        Since:
            Version 1.0.0
        """
        # Invalid update data
        update_data = {"prompt_templates": "not a dict"}

        # Execute and verify
        with pytest.raises(ValueError, match="prompt_templates must be a dictionary"):
            category_manager._validate_category_update(update_data)