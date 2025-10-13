"""
Integration tests for Multi-API Manager.

Tests coordination of multiple API providers including rate limiting,
cost tracking, and graceful degradation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.integrations.api_manager import MultiAPIManager
from src.integrations.providers.base import StandardizedAPIResponse, SearchResult
from src.config.logging import get_logger


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock(spec=redis.Redis)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.incr = AsyncMock(return_value=1)
    mock.delete = AsyncMock(return_value=1)
    mock.incrbyfloat = AsyncMock(return_value=1.0)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
async def mock_logger():
    """Create mock pharmaceutical logger."""
    logger = MagicMock()
    logger.log_processing_start = AsyncMock()
    logger.log_api_call = AsyncMock()
    return logger


@pytest.fixture
async def api_manager(mock_db_session, mock_redis, mock_logger):
    """Create API manager instance with mocks."""
    manager = MultiAPIManager(mock_db_session, mock_redis, mock_logger)
    return manager


class TestMultiAPIManager:
    """Test suite for Multi-API Manager."""

    @pytest.mark.asyncio
    async def test_initialize_providers(self, api_manager, mock_db_session):
        """Test provider initialization from database configuration."""
        # Mock database configurations
        mock_configs = [
            MagicMock(
                provider_name='chatgpt',
                enabled_globally=True,
                config_json={'model': 'gpt-4'},
                encrypted_api_key='test_key_1'
            ),
            MagicMock(
                provider_name='perplexity',
                enabled_globally=True,
                config_json={'model': 'pplx-70b'},
                encrypted_api_key='test_key_2'
            )
        ]

        with patch.object(api_manager.config_repo, 'get_all_configs', return_value=mock_configs):
            with patch('src.integrations.api_manager.PROVIDER_CLASSES', {
                'chatgpt': MagicMock(return_value=MagicMock(validate_config=lambda: True)),
                'perplexity': MagicMock(return_value=MagicMock(validate_config=lambda: True))
            }):
                await api_manager.initialize()

                assert len(api_manager.providers) == 2
                assert 'chatgpt' in api_manager.providers
                assert 'perplexity' in api_manager.providers
                assert api_manager._initialized

    @pytest.mark.asyncio
    async def test_search_all_providers(self, api_manager):
        """Test searching across all active providers."""
        # Create mock providers
        mock_chatgpt = MagicMock()
        mock_chatgpt.name = 'chatgpt'
        mock_chatgpt.search = AsyncMock(return_value=StandardizedAPIResponse(
            provider='chatgpt',
            query='test query',
            temperature=0.7,
            results=[SearchResult(
                title='Test Result 1',
                content='Test content from ChatGPT',
                relevance_score=0.9,
                source_type='research_paper'
            )],
            total_results=1,
            sources=[],
            response_time_ms=100,
            cost=0.01,
            timestamp=datetime.utcnow(),
            relevance_score=0.9,
            confidence_score=0.8
        ))

        mock_perplexity = MagicMock()
        mock_perplexity.name = 'perplexity'
        mock_perplexity.search = AsyncMock(return_value=StandardizedAPIResponse(
            provider='perplexity',
            query='test query',
            temperature=0.7,
            results=[SearchResult(
                title='Test Result 2',
                content='Test content from Perplexity',
                relevance_score=0.85,
                source_type='clinical_trial'
            )],
            total_results=1,
            sources=[],
            response_time_ms=150,
            cost=0.005,
            timestamp=datetime.utcnow(),
            relevance_score=0.85,
            confidence_score=0.9
        ))

        api_manager.providers = {
            'chatgpt': mock_chatgpt,
            'perplexity': mock_perplexity
        }
        api_manager._initialized = True

        # Mock rate limiter to allow all requests
        api_manager.rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))

        # Mock active providers
        with patch.object(api_manager, '_get_active_providers_for_category',
                         return_value=['chatgpt', 'perplexity']):
            with patch.object(api_manager, '_check_provider_health', return_value=True):
                results = await api_manager.search_all_providers(
                    'test query',
                    'Clinical Trials',
                    {'request_id': 'test_123'}
                )

                assert len(results) == 2
                assert results[0].provider == 'chatgpt'
                assert results[1].provider == 'perplexity'
                assert results[0].cost == 0.01
                assert results[1].cost == 0.005

    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_manager):
        """Test rate limiting prevents excessive API calls."""
        mock_provider = MagicMock()
        mock_provider.name = 'chatgpt'
        mock_provider.timeout = 30

        api_manager.providers = {'chatgpt': mock_provider}
        api_manager._initialized = True

        # Mock rate limiter to deny request
        api_manager.rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 60))

        with patch.object(api_manager, '_check_provider_health', return_value=True):
            result = await api_manager._search_provider_with_limits(
                mock_provider,
                'test query',
                'Clinical Trials',
                {}
            )

            assert result is None
            api_manager.rate_limiter.check_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, api_manager, mock_redis):
        """Test circuit breaker prevents calls to failing providers."""
        # Set circuit breaker to open state
        mock_redis.get = AsyncMock(side_effect=lambda key: 'open' if 'circuit_breaker' in key else None)

        is_healthy = await api_manager._check_provider_health('chatgpt')
        assert is_healthy is False

        # Test circuit breaker recovery after timeout
        mock_redis.get = AsyncMock(side_effect=lambda key: None)
        is_healthy = await api_manager._check_provider_health('chatgpt')
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_provider_failure_handling(self, api_manager):
        """Test graceful handling of provider failures."""
        mock_provider = MagicMock()
        mock_provider.name = 'chatgpt'
        mock_provider.search = AsyncMock(side_effect=Exception("API Error"))
        mock_provider.timeout = 30

        api_manager.providers = {'chatgpt': mock_provider}
        api_manager._initialized = True
        api_manager.rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))

        with patch.object(api_manager, '_check_provider_health', return_value=True):
            result = await api_manager._search_provider_with_limits(
                mock_provider,
                'test query',
                'Clinical Trials',
                {}
            )

            assert result is None
            # Verify failure was recorded
            api_manager.redis_client.incr.assert_called()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, api_manager):
        """Test timeout handling for slow API responses."""
        mock_provider = MagicMock()
        mock_provider.name = 'chatgpt'
        mock_provider.timeout = 1  # 1 second timeout

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            return StandardizedAPIResponse(
                provider='chatgpt',
                query='test',
                temperature=0.7,
                results=[],
                total_results=0,
                sources=[],
                response_time_ms=2000,
                cost=0.01,
                timestamp=datetime.utcnow(),
                relevance_score=0.0,
                confidence_score=0.0
            )

        mock_provider.search = slow_search

        api_manager.providers = {'chatgpt': mock_provider}
        api_manager._initialized = True
        api_manager.rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))

        with patch.object(api_manager, '_check_provider_health', return_value=True):
            result = await api_manager._search_provider_with_limits(
                mock_provider,
                'test query',
                'Clinical Trials',
                {'timeout': 1}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_cost_tracking(self, api_manager, mock_redis):
        """Test API call cost tracking."""
        await api_manager._track_cost('chatgpt', 'Clinical Trials', 0.05)

        # Verify Redis cost tracking calls
        mock_redis.incrbyfloat.assert_called()
        mock_redis.expire.assert_called()

        # Check that both daily and category costs are tracked
        calls = mock_redis.incrbyfloat.call_args_list
        assert len(calls) == 2
        assert 'cost:daily:chatgpt' in str(calls[0])
        assert 'cost:category:Clinical Trials' in str(calls[1])

    @pytest.mark.asyncio
    async def test_get_provider_status(self, api_manager, mock_redis):
        """Test getting comprehensive provider status."""
        mock_provider = MagicMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_provider.get_rate_limits = lambda: {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'daily_quota': 10000
        }

        api_manager.providers = {'chatgpt': mock_provider}
        api_manager._initialized = True

        mock_redis.get = AsyncMock(side_effect=lambda key: {
            'circuit_breaker:chatgpt': None,
            'provider_failures:chatgpt': '2',
            f'cost:daily:chatgpt:{datetime.utcnow().date()}': '1.25'
        }.get(key, None))

        status = await api_manager.get_provider_status()

        assert 'chatgpt' in status
        assert status['chatgpt']['healthy'] is True
        assert status['chatgpt']['circuit_breaker'] == 'closed'
        assert status['chatgpt']['recent_failures'] == 2
        assert status['chatgpt']['daily_cost'] == 1.25
        assert status['chatgpt']['rate_limits']['requests_per_minute'] == 60

    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self, api_manager):
        """Test parallel execution of multiple providers."""
        # Create 5 mock providers with different response times
        providers = {}
        for i in range(5):
            provider = MagicMock()
            provider.name = f'provider_{i}'

            async def make_search(delay=i*0.1):
                await asyncio.sleep(delay)
                return StandardizedAPIResponse(
                    provider=f'provider_{delay}',
                    query='test',
                    temperature=0.7,
                    results=[],
                    total_results=0,
                    sources=[],
                    response_time_ms=int(delay*1000),
                    cost=0.01,
                    timestamp=datetime.utcnow(),
                    relevance_score=0.5,
                    confidence_score=0.5
                )

            provider.search = AsyncMock(side_effect=make_search)
            provider.timeout = 10
            providers[provider.name] = provider

        api_manager.providers = providers
        api_manager._initialized = True
        api_manager.rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))

        with patch.object(api_manager, '_get_active_providers_for_category',
                         return_value=list(providers.keys())):
            with patch.object(api_manager, '_check_provider_health', return_value=True):
                import time
                start = time.time()

                results = await api_manager.search_all_providers(
                    'test query',
                    'Clinical Trials',
                    {}
                )

                duration = time.time() - start

                # All 5 providers should return results
                assert len(results) == 5

                # Parallel execution should complete faster than sequential
                # Sequential would take 0 + 0.1 + 0.2 + 0.3 + 0.4 = 1.0 seconds
                # Parallel should take about 0.4 seconds (max delay)
                assert duration < 0.8  # Allow some overhead