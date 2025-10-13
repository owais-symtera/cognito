"""
Tests for temperature variation search strategy.

Validates multi-temperature execution, caching, performance optimization,
and effectiveness analytics for pharmaceutical intelligence.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from src.core.temperature_strategy import (
    TemperatureStrategy,
    TemperatureSearchManager,
    TemperatureResult
)
from src.integrations.providers.base import (
    StandardizedAPIResponse,
    SearchResult
)
from src.integrations.api_manager import MultiAPIManager


@pytest.fixture
async def mock_persistence_manager():
    """Create mock persistence manager."""
    manager = AsyncMock()
    manager.store_api_response = AsyncMock(return_value="response-id-123")
    return manager


@pytest.fixture
async def mock_audit_logger():
    """Create mock audit logger."""
    logger = AsyncMock()
    logger.log_api_call = AsyncMock()
    logger.log_data_access = AsyncMock()
    return logger


@pytest.fixture
async def mock_provider():
    """Create mock API provider."""
    provider = AsyncMock()
    provider.name = "test_provider"
    provider.search = AsyncMock()
    return provider


@pytest.fixture
async def sample_api_response():
    """Create sample API response."""
    return StandardizedAPIResponse(
        provider="test_provider",
        query="Test query",
        temperature=0.5,
        results=[
            SearchResult(
                title="Result 1",
                content="Content 1",
                relevance_score=0.9,
                source_type="research_paper"
            ),
            SearchResult(
                title="Result 2",
                content="Content 2",
                relevance_score=0.85,
                source_type="clinical_trial"
            )
        ],
        sources=[],
        total_results=2,
        response_time_ms=500,
        cost=0.04,
        relevance_score=0.88,
        confidence_score=0.9,
        timestamp=datetime.utcnow()
    )


class TestTemperatureStrategy:
    """Tests for TemperatureStrategy configuration."""

    def test_default_temperatures(self):
        """Test default temperature configuration."""
        strategy = TemperatureStrategy()
        assert strategy.temperatures == [0.1, 0.5, 0.9]
        assert strategy.min_temperature == 0.0
        assert strategy.max_temperature == 1.0

    def test_category_specific_temperatures(self):
        """Test category-specific temperature overrides."""
        strategy = TemperatureStrategy(
            category_overrides={
                "Oncology": [0.3, 0.6, 0.8],
                "Cardiology": [0.2, 0.7]
            }
        )

        assert strategy.get_temperatures_for_category("Oncology") == [0.3, 0.6, 0.8]
        assert strategy.get_temperatures_for_category("Cardiology") == [0.2, 0.7]
        assert strategy.get_temperatures_for_category("Other") == [0.1, 0.5, 0.9]

    def test_api_specific_temperatures(self):
        """Test API provider-specific temperature configuration."""
        strategy = TemperatureStrategy(
            api_specific={
                "chatgpt": [0.1, 0.7],
                "perplexity": [0.3, 0.5, 0.9]
            }
        )

        assert strategy.get_temperatures_for_api("chatgpt", "Any") == [0.1, 0.7]
        assert strategy.get_temperatures_for_api("perplexity", "Any") == [0.3, 0.5, 0.9]
        assert strategy.get_temperatures_for_api("other", "Any") == [0.1, 0.5, 0.9]


class TestTemperatureSearchManager:
    """Tests for TemperatureSearchManager."""

    @pytest.mark.asyncio
    async def test_parallel_temperature_execution(
        self,
        mock_persistence_manager,
        mock_audit_logger,
        mock_provider,
        sample_api_response
    ):
        """Test parallel execution of multiple temperature searches."""
        manager = TemperatureSearchManager(
            mock_persistence_manager,
            mock_audit_logger
        )

        # Setup mock provider responses for different temperatures
        responses = []
        for temp in [0.1, 0.5, 0.9]:
            response = sample_api_response.copy()
            response.temperature = temp
            response.relevance_score = 0.7 + temp * 0.2  # Vary by temperature
            responses.append(response)

        mock_provider.search.side_effect = responses

        # Execute temperature searches
        results = await manager.execute_temperature_searches(
            provider=mock_provider,
            query="Test query",
            temperatures=[0.1, 0.5, 0.9],
            category="Test Category",
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-789",
            pharmaceutical_compound="Test Drug"
        )

        # Verify parallel execution
        assert len(results) == 3
        assert mock_provider.search.call_count == 3

        # Verify results are sorted by temperature
        assert results[0].temperature == 0.1
        assert results[1].temperature == 0.5
        assert results[2].temperature == 0.9

        # Verify persistence calls
        assert mock_persistence_manager.store_api_response.call_count == 3

    @pytest.mark.asyncio
    async def test_cache_functionality(
        self,
        mock_persistence_manager,
        mock_audit_logger,
        mock_provider,
        sample_api_response
    ):
        """Test caching of temperature search results."""
        manager = TemperatureSearchManager(
            mock_persistence_manager,
            mock_audit_logger,
            cache_ttl_minutes=60
        )

        mock_provider.search.return_value = sample_api_response

        # First execution - should hit API
        results1 = await manager.execute_temperature_searches(
            provider=mock_provider,
            query="Test query",
            temperatures=[0.5],
            category="Test Category",
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-789",
            pharmaceutical_compound="Test Drug"
        )

        assert len(results1) == 1
        assert not results1[0].cached
        assert mock_provider.search.call_count == 1

        # Second execution with same parameters - should use cache
        results2 = await manager.execute_temperature_searches(
            provider=mock_provider,
            query="Test query",
            temperatures=[0.5],
            category="Test Category",
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-790",
            pharmaceutical_compound="Test Drug"
        )

        assert len(results2) == 1
        assert results2[0].cached
        assert results2[0].cost == 0  # No cost for cached
        assert mock_provider.search.call_count == 1  # Still 1, didn't call again

    @pytest.mark.asyncio
    async def test_effectiveness_analysis(
        self,
        mock_persistence_manager,
        mock_audit_logger,
        sample_api_response
    ):
        """Test temperature effectiveness analysis."""
        manager = TemperatureSearchManager(
            mock_persistence_manager,
            mock_audit_logger
        )

        # Create mock results with varying metrics
        results = [
            TemperatureResult(
                temperature=0.1,
                response=sample_api_response,
                response_id="id-1",
                execution_time_ms=500,
                cost=0.04,
                relevance_score=0.75,
                result_count=5,
                cached=False
            ),
            TemperatureResult(
                temperature=0.5,
                response=sample_api_response,
                response_id="id-2",
                execution_time_ms=550,
                cost=0.04,
                relevance_score=0.88,
                result_count=8,
                cached=False
            ),
            TemperatureResult(
                temperature=0.9,
                response=sample_api_response,
                response_id="id-3",
                execution_time_ms=600,
                cost=0.04,
                relevance_score=0.82,
                result_count=10,
                cached=False
            )
        ]

        # Analyze effectiveness
        analysis = await manager.analyze_temperature_effectiveness(
            results,
            "Test Category"
        )

        # Verify analysis structure
        assert analysis['category'] == "Test Category"
        assert analysis['temperature_count'] == 3
        assert 'metrics' in analysis
        assert 'recommendations' in analysis
        assert 'optimal_temperature' in analysis

        # Verify metrics
        assert len(analysis['metrics']) == 3
        for metric in analysis['metrics']:
            assert 'temperature' in metric
            assert 'relevance_score' in metric
            assert 'diversity_score' in metric

        # Verify optimal temperature selection (0.5 has best relevance)
        assert analysis['optimal_temperature'] == 0.5

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        mock_persistence_manager,
        mock_audit_logger,
        mock_provider
    ):
        """Test error handling in temperature searches."""
        manager = TemperatureSearchManager(
            mock_persistence_manager,
            mock_audit_logger
        )

        # Setup provider to fail
        mock_provider.search.side_effect = Exception("API Error")

        # Execute should handle error gracefully
        with pytest.raises(Exception) as exc_info:
            await manager.execute_temperature_searches(
                provider=mock_provider,
                query="Test query",
                temperatures=[0.5],
                category="Test Category",
                process_id="process-123",
                request_id="request-456",
                correlation_id="corr-789",
                pharmaceutical_compound="Test Drug"
            )

        assert "API Error" in str(exc_info.value)


class TestMultiAPITemperatureIntegration:
    """Tests for temperature integration with MultiAPIManager."""

    @pytest.mark.asyncio
    async def test_multi_provider_temperature_search(self):
        """Test temperature search across multiple providers."""
        db = AsyncMock()
        redis_client = AsyncMock()
        audit_logger = AsyncMock()

        manager = MultiAPIManager(db, redis_client, audit_logger)

        # Mock providers
        provider1 = AsyncMock()
        provider1.name = "provider1"
        provider1.search = AsyncMock()

        provider2 = AsyncMock()
        provider2.name = "provider2"
        provider2.search = AsyncMock()

        manager.providers = {
            "provider1": provider1,
            "provider2": provider2
        }
        manager._initialized = True

        # Mock temperature manager
        temp_manager = AsyncMock()
        temp_manager.execute_temperature_searches = AsyncMock()
        manager.temperature_manager = temp_manager

        # Setup return values
        temp_manager.execute_temperature_searches.side_effect = [
            [TemperatureResult(
                temperature=0.5,
                response=MagicMock(),
                response_id="id-1",
                execution_time_ms=500,
                cost=0.04,
                relevance_score=0.85,
                result_count=5,
                cached=False
            )],
            [TemperatureResult(
                temperature=0.5,
                response=MagicMock(),
                response_id="id-2",
                execution_time_ms=600,
                cost=0.05,
                relevance_score=0.88,
                result_count=7,
                cached=False
            )]
        ]

        # Execute search
        results = await manager.search_with_temperature_variation(
            query="Test query",
            category="Test Category",
            pharmaceutical_compound="Test Drug",
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-789"
        )

        # Verify results from both providers
        assert len(results) == 2
        assert "provider1" in results
        assert "provider2" in results

        # Verify temperature searches were executed
        assert temp_manager.execute_temperature_searches.call_count == 2

    @pytest.mark.asyncio
    async def test_temperature_effectiveness_aggregation(self):
        """Test aggregation of temperature effectiveness across providers."""
        db = AsyncMock()
        redis_client = AsyncMock()
        audit_logger = AsyncMock()

        manager = MultiAPIManager(db, redis_client, audit_logger)
        manager._initialized = True

        # Mock temperature manager
        temp_manager = AsyncMock()
        temp_manager.analyze_temperature_effectiveness = AsyncMock()
        manager.temperature_manager = temp_manager

        # Setup mock analysis results
        temp_manager.analyze_temperature_effectiveness.side_effect = [
            {
                'optimal_temperature': 0.5,
                'recommendations': ['Use 0.5 for best results']
            },
            {
                'optimal_temperature': 0.7,
                'recommendations': ['Use 0.7 for best diversity']
            }
        ]

        # Create test data
        temperature_results = {
            'provider1': [MagicMock()],
            'provider2': [MagicMock()]
        }

        # Analyze
        analysis = await manager.analyze_temperature_effectiveness(
            temperature_results,
            "Test Category"
        )

        # Verify aggregation
        assert analysis['category'] == "Test Category"
        assert 'providers' in analysis
        assert 'overall_recommendations' in analysis
        assert 'recommended_temperature' in analysis

        # Should recommend average of 0.5 and 0.7
        assert analysis['recommended_temperature'] == 0.6