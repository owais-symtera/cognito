"""
Integration tests for health monitoring API endpoints.

Tests health checks, system diagnostics, and monitoring endpoints
for pharmaceutical platform reliability.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from src.main import app
from src.schemas.health import HealthStatus


class TestHealthAPI:
    """
    Test suite for health monitoring endpoints.

    Since:
        Version 1.0.0
    """

    @pytest.mark.asyncio
    async def test_basic_health_check(self, async_client: AsyncClient):
        """
        Test basic health check endpoint.

        Since:
            Version 1.0.0
        """
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert data["service"] == "cognito-ai-engine"

    @pytest.mark.asyncio
    async def test_detailed_health_check(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test detailed health check with dependencies.

        Since:
            Version 1.0.0
        """
        response = await async_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        assert "uptime_seconds" in data
        assert "checks_passed" in data
        assert "checks_failed" in data

        # Check dependencies structure
        dependencies = data["dependencies"]
        assert isinstance(dependencies, list)
        if dependencies:
            dep = dependencies[0]
            assert "name" in dep
            assert "status" in dep
            assert "last_check" in dep

    @pytest.mark.asyncio
    async def test_liveness_probe(self, async_client: AsyncClient):
        """
        Test Kubernetes liveness probe.

        Since:
            Version 1.0.0
        """
        response = await async_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_probe(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test Kubernetes readiness probe.

        Since:
            Version 1.0.0
        """
        response = await async_client.get("/health/ready")

        # Should be ready if database is available
        assert response.status_code in [200, 503]
        data = response.json()

        if response.status_code == 200:
            assert data["status"] == "ready"
        else:
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_check_specific_dependency(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test checking specific dependency health.

        Since:
            Version 1.0.0
        """
        # Test PostgreSQL dependency
        response = await async_client.get("/health/dependencies/postgresql")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "postgresql"
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "last_check" in data

    @pytest.mark.asyncio
    async def test_unknown_dependency(self, async_client: AsyncClient):
        """
        Test checking unknown dependency.

        Since:
            Version 1.0.0
        """
        response = await async_client.get("/health/dependencies/unknown")

        assert response.status_code == 404
        data = response.json()
        assert "Unknown dependency" in data["detail"]

    @pytest.mark.asyncio
    async def test_health_check_with_database_failure(
        self,
        async_client: AsyncClient
    ):
        """
        Test health check when database is unavailable.

        Since:
            Version 1.0.0
        """
        with patch('src.core.health_checker.HealthChecker.check_database_health') as mock_db_check:
            mock_db_check.return_value = AsyncMock(
                status=HealthStatus.UNHEALTHY,
                error="Connection refused"
            )

            response = await async_client.get("/health/detailed")

            assert response.status_code == 200
            data = response.json()
            # Overall status should be unhealthy if database is down
            assert data["checks_failed"] > 0

    @pytest.mark.asyncio
    async def test_health_check_performance(self, async_client: AsyncClient):
        """
        Test basic health check response time.

        Since:
            Version 1.0.0
        """
        import time
        start = time.time()
        response = await async_client.get("/health")
        duration = (time.time() - start) * 1000

        assert response.status_code == 200
        # Basic health check should be fast (< 50ms)
        assert duration < 50

    @pytest.mark.asyncio
    async def test_detailed_health_check_performance(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test detailed health check response time.

        Since:
            Version 1.0.0
        """
        import time
        start = time.time()
        response = await async_client.get("/health/detailed")
        duration = (time.time() - start) * 1000

        assert response.status_code == 200
        # Detailed health check should complete within 500ms
        assert duration < 500