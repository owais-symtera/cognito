"""
Unit tests for rate limiting implementation.

Tests token bucket algorithm, rate limit enforcement, and quota management.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import redis.asyncio as redis

from src.integrations.rate_limiter import RateLimiter


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock(spec=redis.Redis)
    mock.pipeline = AsyncMock()
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.zcard = AsyncMock(return_value=0)
    mock.zadd = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.zrange = AsyncMock(return_value=[])
    mock.incr = AsyncMock(return_value=1)
    mock.get = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hset = AsyncMock(return_value=1)
    mock.delete = AsyncMock(return_value=1)
    mock.scan = AsyncMock(return_value=(0, []))
    return mock


@pytest.fixture
async def rate_limiter(mock_redis):
    """Create rate limiter instance with mock Redis."""
    return RateLimiter(mock_redis)


class TestRateLimiter:
    """Test suite for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit allows request when under limit."""
        # Mock Redis pipeline for sliding window
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 5, 1, True])  # 5 requests in window

        mock_redis.pipeline = lambda: pipeline_mock

        # Mock hour and day counters
        mock_redis.incr = AsyncMock(return_value=10)

        allowed, retry_after = await rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials')

        assert allowed is True
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_minute_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test per-minute rate limit enforcement."""
        # Mock pipeline to return count exceeding limit
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 61, 1, True])  # 61 requests (exceeds 60 rpm)

        mock_redis.pipeline = lambda: pipeline_mock

        # Mock zrange to return oldest entry for retry calculation
        current = time.time()
        mock_redis.zrange = AsyncMock(return_value=[('request', current - 30)])  # 30 seconds ago

        allowed, retry_after = await rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials')

        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
        assert retry_after <= 30

    @pytest.mark.asyncio
    async def test_hour_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test per-hour rate limit enforcement."""
        # Mock minute check to pass
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 50, 1, True])  # Under minute limit
        mock_redis.pipeline = lambda: pipeline_mock

        # Mock hour counter to exceed limit
        mock_redis.incr = AsyncMock(return_value=1001)  # Exceeds 1000 rph

        with patch('src.integrations.rate_limiter.datetime') as mock_datetime:
            now = datetime.utcnow()
            mock_datetime.utcnow.return_value = now

            allowed, retry_after = await rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials')

            assert allowed is False
            assert retry_after is not None
            assert retry_after > 0

    @pytest.mark.asyncio
    async def test_daily_quota_exceeded(self, rate_limiter, mock_redis):
        """Test daily quota enforcement."""
        # Mock minute and hour checks to pass
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 50, 1, True])
        mock_redis.pipeline = lambda: pipeline_mock

        # Mock counters - hour passes but day exceeds
        counter = 0

        def incr_side_effect(key):
            nonlocal counter
            counter += 1
            if 'hour' in key:
                return 500  # Under hour limit
            else:
                return 10001  # Exceeds daily quota

        mock_redis.incr = AsyncMock(side_effect=incr_side_effect)

        with patch('src.integrations.rate_limiter.datetime') as mock_datetime:
            now = datetime.utcnow()
            mock_datetime.utcnow.return_value = now
            mock_datetime.combine.return_value = datetime.combine(
                now.date() + timedelta(days=1),
                datetime.min.time()
            )

            allowed, retry_after = await rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials')

            assert allowed is False
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_category_multiplier(self, rate_limiter, mock_redis):
        """Test category-specific rate limit multipliers."""
        # Mock getting provider limits
        rate_limiter.limits_cache['chatgpt'] = {
            'rpm': 60,
            'rph': 1000,
            'rpd': 10000
        }

        # Test with category that has 0.8 multiplier
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 49, 1, True])  # 49 requests
        mock_redis.pipeline = lambda: pipeline_mock
        mock_redis.incr = AsyncMock(return_value=100)

        # 60 * 0.8 = 48 limit, 49 requests should fail
        allowed, retry_after = await rate_limiter.check_rate_limit(
            'chatgpt',
            'Clinical Trials & Studies'  # Has 0.8 multiplier
        )

        # The minute check will fail because 49 > 48
        assert allowed is False

    @pytest.mark.asyncio
    async def test_get_remaining_quota(self, rate_limiter, mock_redis):
        """Test getting remaining quota for provider."""
        # Mock provider limits
        rate_limiter.limits_cache['chatgpt'] = {
            'rpm': 60,
            'rph': 1000,
            'rpd': 10000
        }

        # Mock current usage
        mock_redis.zcard = AsyncMock(return_value=25)  # 25 requests in minute window
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            f'rate_limit:hour:chatgpt:{datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()}': '400',
            f'rate_limit:day:chatgpt:{datetime.utcnow().date().isoformat()}': '3000'
        }.get(key, '0'))

        remaining = await rate_limiter.get_remaining_quota('chatgpt')

        assert remaining['minute'] == 35  # 60 - 25
        assert remaining['hour'] == 600  # 1000 - 400
        assert remaining['day'] == 7000  # 10000 - 3000

    @pytest.mark.asyncio
    async def test_reset_limits(self, rate_limiter, mock_redis):
        """Test resetting rate limits for provider."""
        # Mock scan to return keys
        mock_redis.scan = AsyncMock(side_effect=[
            (1, [b'rate_limit:minute:chatgpt:123', b'rate_limit:minute:chatgpt:456']),
            (0, [b'rate_limit:minute:chatgpt:789'])
        ])

        await rate_limiter.reset_limits('chatgpt')

        # Verify delete was called for found keys
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_update_provider_limits(self, rate_limiter, mock_redis):
        """Test updating provider rate limits."""
        await rate_limiter.update_provider_limits(
            'chatgpt',
            rpm=100,
            rph=2000,
            rpd=20000
        )

        # Verify Redis update
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert 'provider_limits:chatgpt' in call_args[0]
        assert call_args[1]['mapping']['rpm'] == 100
        assert call_args[1]['mapping']['rph'] == 2000
        assert call_args[1]['mapping']['rpd'] == 20000

        # Verify cache cleared
        assert 'chatgpt' not in rate_limiter.limits_cache

    @pytest.mark.asyncio
    async def test_sliding_window_algorithm(self, rate_limiter, mock_redis):
        """Test sliding window algorithm for minute rate limiting."""
        current_time = time.time()

        # Mock pipeline operations
        pipeline_mock = AsyncMock()
        remove_count = 0
        request_count = 0

        def zremrangebyscore_effect(key, min_score, max_score):
            nonlocal remove_count
            remove_count = 10  # Removed 10 old requests
            return AsyncMock()

        def zcard_effect(key):
            nonlocal request_count
            request_count = 45  # 45 requests in current window
            return AsyncMock()

        pipeline_mock.zremrangebyscore = AsyncMock(side_effect=zremrangebyscore_effect)
        pipeline_mock.zcard = AsyncMock(side_effect=zcard_effect)
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[10, 45, 1, True])

        mock_redis.pipeline = lambda: pipeline_mock

        # Mock hour and day checks to pass
        mock_redis.incr = AsyncMock(return_value=100)

        allowed, _ = await rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials')

        assert allowed is True

        # Verify sliding window was applied
        pipeline_mock.zremrangebyscore.assert_called()
        zrem_call = pipeline_mock.zremrangebyscore.call_args
        assert 'rate_limit:minute:chatgpt' in zrem_call[0][0]

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_checks(self, rate_limiter, mock_redis):
        """Test concurrent rate limit checks don't cause race conditions."""
        # Mock pipeline for atomic operations
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 30, 1, True])

        mock_redis.pipeline = lambda: pipeline_mock
        mock_redis.incr = AsyncMock(return_value=500)

        # Simulate concurrent checks
        tasks = []
        for _ in range(10):
            tasks.append(rate_limiter.check_rate_limit('chatgpt', 'Clinical Trials'))

        import asyncio
        results = await asyncio.gather(*tasks)

        # All should get consistent results
        for allowed, retry_after in results:
            assert allowed is True
            assert retry_after is None