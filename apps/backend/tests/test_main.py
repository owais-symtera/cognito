"""
Unit tests for FastAPI main application module.

Tests the core FastAPI application setup, endpoints, middleware configuration,
and health check functionality for pharmaceutical intelligence platform.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """
    Create test client for FastAPI application.

    Provides a test client instance for API endpoint testing
    without requiring actual server startup.

    Returns:
        TestClient: FastAPI test client for pharmaceutical API testing

    Since:
        Version 1.0.0
    """
    return TestClient(app)


class TestRootEndpoint:
    """
    Test suite for root endpoint functionality.

    Validates the root API endpoint provides correct pharmaceutical
    platform information and metadata for regulatory compliance.
    """

    def test_root_endpoint_returns_correct_metadata(self, client):
        """
        Test root endpoint returns correct pharmaceutical platform metadata.

        Validates that the root endpoint provides accurate information
        about the CognitoAI Engine platform including version, status,
        and pharmaceutical-specific configuration.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "CognitoAI Engine API v1.0.0"
        assert data["description"] == "Pharmaceutical Intelligence Processing with Source Tracking"
        assert data["status"] == "operational"
        assert data["docs"] == "/api/docs"
        assert data["health"] == "/health"
        assert data["pharmaceutical_categories"] == 17
        assert data["compliance"] == "pharmaceutical_regulatory"

    def test_root_endpoint_response_structure(self, client):
        """
        Test root endpoint response contains required fields.

        Ensures the root endpoint response includes all mandatory fields
        for pharmaceutical platform identification and compliance tracking.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/")
        data = response.json()

        required_fields = [
            "message", "description", "status", "docs", "health",
            "pharmaceutical_categories", "compliance"
        ]

        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"


class TestHealthCheckEndpoint:
    """
    Test suite for health check endpoint functionality.

    Validates health monitoring capabilities required for pharmaceutical
    operational compliance and system reliability monitoring.
    """

    def test_health_endpoint_returns_healthy_status(self, client):
        """
        Test health endpoint returns healthy status.

        Validates that the health check endpoint provides accurate
        system health status for pharmaceutical operational monitoring.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["service"] == "cognito-ai-engine"

    def test_health_endpoint_includes_timestamp(self, client):
        """
        Test health endpoint includes current timestamp.

        Validates that health checks include timing information
        required for pharmaceutical system monitoring and audit trails.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/health")
        data = response.json()

        assert "timestamp" in data
        assert data["timestamp"] is not None
        # Validate ISO format timestamp
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_health_endpoint_response_time(self, client):
        """
        Test health endpoint responds within performance requirements.

        Validates that health checks meet pharmaceutical operational
        requirements for rapid system status assessment.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        import time

        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        assert response.status_code == 200

        # Health check should respond within 100ms for pharmaceutical monitoring
        response_time = (end_time - start_time) * 1000
        assert response_time < 100, f"Health check took {response_time}ms, should be < 100ms"


class TestApplicationConfiguration:
    """
    Test suite for FastAPI application configuration.

    Validates middleware setup, CORS configuration, and security
    settings required for pharmaceutical regulatory compliance.
    """

    def test_cors_middleware_configuration(self, client):
        """
        Test CORS middleware is properly configured.

        Validates CORS settings allow appropriate origins for
        pharmaceutical frontend integration while maintaining security.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        # Test preflight request
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })

        # CORS should be configured for frontend development
        assert response.status_code in [200, 204]

    def test_api_documentation_accessible(self, client):
        """
        Test API documentation endpoints are accessible.

        Validates that pharmaceutical API documentation is available
        for compliance reviews and developer integration.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        # Test OpenAPI documentation
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_application_metadata(self):
        """
        Test FastAPI application metadata configuration.

        Validates application title, description, and version
        match pharmaceutical platform requirements.

        Since:
            Version 1.0.0
        """
        assert app.title == "CognitoAI Engine API"
        assert "Pharmaceutical Intelligence Processing" in app.description
        assert app.version == "1.0.0"
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"


class TestPharmaceuticalCompliance:
    """
    Test suite for pharmaceutical regulatory compliance features.

    Validates that the application meets pharmaceutical industry
    requirements for audit trails, monitoring, and regulatory compliance.
    """

    def test_pharmaceutical_category_configuration(self, client):
        """
        Test pharmaceutical category configuration is correct.

        Validates that the system is configured for the required
        17 pharmaceutical categories as specified in compliance requirements.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/")
        data = response.json()

        # Must support exactly 17 pharmaceutical categories
        assert data["pharmaceutical_categories"] == 17

    def test_regulatory_compliance_indicators(self, client):
        """
        Test regulatory compliance indicators are present.

        Validates that the application exposes necessary compliance
        information for pharmaceutical regulatory requirements.

        Args:
            client: FastAPI test client

        Since:
            Version 1.0.0
        """
        response = client.get("/")
        data = response.json()

        # Must indicate pharmaceutical regulatory compliance
        assert data["compliance"] == "pharmaceutical_regulatory"