"""
Integration tests for pharmaceutical category API endpoints.

Tests category management API endpoints with database integration
for pharmaceutical regulatory compliance validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import json

from src.main import app
from src.database.models import PharmaceuticalCategory, CategoryDependency


class TestCategoryAPI:
    """
    Integration test suite for category management API.

    Tests all category API endpoints with real database operations
    for pharmaceutical intelligence platform.

    Since:
        Version 1.0.0
    """

    @pytest.mark.asyncio
    async def test_list_categories(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test listing pharmaceutical categories endpoint.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/")

        # Verify
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0  # Should have default categories

        # Check first category structure
        if categories:
            category = categories[0]
            assert "id" in category
            assert "name" in category
            assert "phase" in category
            assert "is_active" in category
            assert "search_parameters" in category
            assert "prompt_templates" in category

    @pytest.mark.asyncio
    async def test_list_categories_by_phase(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test filtering categories by processing phase.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/?phase=1")

        # Verify
        assert response.status_code == 200
        categories = response.json()
        assert all(cat["phase"] == 1 for cat in categories)

    @pytest.mark.asyncio
    async def test_list_categories_include_inactive(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test including inactive categories in listing.

        Since:
            Version 1.0.0
        """
        # Execute
        response_active = await async_client.get("/api/v1/categories/")
        response_all = await async_client.get(
            "/api/v1/categories/?include_inactive=true"
        )

        # Verify
        assert response_active.status_code == 200
        assert response_all.status_code == 200

        # All categories should include at least active ones
        assert len(response_all.json()) >= len(response_active.json())

    @pytest.mark.asyncio
    async def test_get_specific_category(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test retrieving specific category by ID.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/1")

        # Verify
        assert response.status_code == 200
        category = response.json()
        assert category["id"] == 1
        assert "name" in category
        assert "prompt_templates" in category

    @pytest.mark.asyncio
    async def test_get_nonexistent_category(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test retrieving non-existent category returns 404.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/9999")

        # Verify
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_category(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test updating category configuration.

        Since:
            Version 1.0.0
        """
        # Update data
        update_data = {
            "phase": 2,
            "prompt_templates": {
                "search": "Updated search prompt for {drug_name}",
                "analysis": "Updated analysis prompt"
            }
        }

        # Execute
        response = await async_client.put(
            "/api/v1/categories/1",
            json=update_data
        )

        # Verify
        assert response.status_code == 200
        updated_category = response.json()
        assert updated_category["phase"] == 2
        assert "Updated search prompt" in updated_category["prompt_templates"]["search"]

    @pytest.mark.asyncio
    async def test_update_category_invalid_phase(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test updating category with invalid phase fails.

        Since:
            Version 1.0.0
        """
        # Invalid update data
        update_data = {"phase": 3}

        # Execute
        response = await async_client.put(
            "/api/v1/categories/1",
            json=update_data
        )

        # Verify
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_enable_category(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test enabling a pharmaceutical category.

        Since:
            Version 1.0.0
        """
        # First disable a category
        await async_client.post("/api/v1/categories/6/disable")

        # Then enable it
        response = await async_client.post("/api/v1/categories/6/enable")

        # Verify
        assert response.status_code == 200
        category = response.json()
        assert category["is_active"] is True

    @pytest.mark.asyncio
    async def test_disable_category_without_dependencies(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test disabling category that has no dependencies.

        Since:
            Version 1.0.0
        """
        # Execute - Category 6 (Patent) has no dependencies by default
        response = await async_client.post("/api/v1/categories/6/disable")

        # Verify
        assert response.status_code == 200
        category = response.json()
        assert category["is_active"] is False

    @pytest.mark.asyncio
    async def test_disable_category_with_dependencies(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test that disabling category with dependencies fails.

        Since:
            Version 1.0.0
        """
        # Execute - Category 1 (Clinical Trials) has dependencies
        response = await async_client.post("/api/v1/categories/1/disable")

        # Verify
        assert response.status_code == 400
        assert "Required by" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_category_dependencies(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test retrieving category dependency information.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/11/dependencies")

        # Verify
        assert response.status_code == 200
        dependencies = response.json()
        assert "category_id" in dependencies
        assert "depends_on" in dependencies
        assert "required_by" in dependencies
        assert isinstance(dependencies["depends_on"], list)
        assert isinstance(dependencies["required_by"], list)

    @pytest.mark.asyncio
    async def test_export_configuration(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test exporting category configurations.

        Since:
            Version 1.0.0
        """
        # Execute
        response = await async_client.get("/api/v1/categories/export/configuration")

        # Verify
        assert response.status_code == 200
        export_data = response.json()
        assert "export_timestamp" in export_data
        assert "export_version" in export_data
        assert "categories" in export_data
        assert len(export_data["categories"]) == 17  # All default categories

    @pytest.mark.asyncio
    async def test_import_configuration_validation(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test import configuration validation without actual import.

        Since:
            Version 1.0.0
        """
        # Export current configuration first
        export_response = await async_client.get(
            "/api/v1/categories/export/configuration"
        )
        export_data = export_response.json()

        # Validate import
        response = await async_client.post(
            "/api/v1/categories/import/configuration?validate_only=true",
            json=export_data
        )

        # Verify
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "Validation successful" in result["message"]

    @pytest.mark.asyncio
    async def test_import_configuration(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test importing category configurations.

        Since:
            Version 1.0.0
        """
        # Prepare import data with modified configuration
        import_data = {
            "export_timestamp": "2024-01-26T00:00:00",
            "export_version": "1.0.0",
            "categories": [
                {
                    "id": 1,
                    "name": "Clinical Trials & Studies",
                    "phase": 1,
                    "is_active": True,
                    "prompt_templates": {
                        "search": "Imported search prompt for {drug_name}"
                    },
                    "search_parameters": {"keywords": ["imported"]},
                    "processing_rules": {"min_confidence": 0.9},
                    "verification_criteria": {"required_fields": ["phase"]}
                }
            ]
        }

        # Execute
        response = await async_client.post(
            "/api/v1/categories/import/configuration",
            json=import_data
        )

        # Verify
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["imported_count"] > 0

        # Verify the import was applied
        category_response = await async_client.get("/api/v1/categories/1")
        category = category_response.json()
        assert "Imported search prompt" in category["prompt_templates"]["search"]

    @pytest.mark.asyncio
    async def test_import_invalid_configuration(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test that importing invalid configuration fails.

        Since:
            Version 1.0.0
        """
        # Invalid import data
        import_data = {
            "invalid": "data"
        }

        # Execute
        response = await async_client.post(
            "/api/v1/categories/import/configuration",
            json=import_data
        )

        # Verify
        assert response.status_code == 422 or response.status_code == 400