"""
Rate limiting implementation for API providers.

Implements token bucket algorithm with Redis for distributed rate limiting
across multiple API providers and pharmaceutical categories.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import time
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    API rate limiting with pharmaceutical cost optimization.

    Implements token bucket algorithm for rate limiting with support for
    provider-specific and category-specific limits.

    Example:
        >>> limiter = RateLimiter(redis_client)
        >>> allowed, retry_after = await limiter.check_rate_limit("chatgpt", "clinical_trials")
        >>> if allowed:
        ...     # Proceed with API call
        >>> else:
        ...     # Wait for retry_after seconds

    Since:
        Version 1.0.0
    """

    # Default rate limits per provider (requests per minute)
    DEFAULT_PROVIDER_LIMITS = {
        'chatgpt': {'rpm': 60, 'rph': 1000, 'rpd': 10000},
        'perplexity': {'rpm': 50, 'rph': 500, 'rpd': 5000},
        'grok': {'rpm': 40, 'rph': 400, 'rpd': 4000},
        'gemini': {'rpm': 60, 'rph': 600, 'rpd': 6000},
        'tavily': {'rpm': 100, 'rph': 1000, 'rpd': 10000}
    }

    # Category-specific multipliers for rate limits
    CATEGORY_MULTIPLIERS = {
        'Clinical Trials & Studies': 0.8,  # More conservative for detailed searches
        'Drug Interactions & Contraindications': 0.9,
        'Side Effects & Adverse Events': 0.9,
        'Regulatory Status & Approvals': 1.0,
        'Patent & Intellectual Property': 0.7,  # Complex searches need more time
        'Real-World Evidence': 0.8
    }

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client for distributed rate limiting

        Since:
            Version 1.0.0
        """
        self.redis = redis_client
        self.limits_cache = {}

    async def check_rate_limit(
        self,
        provider: str,
        category: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if API call is allowed under current rate limits.

        Args:
            provider: API provider name
            category: Pharmaceutical category

        Returns:
            Tuple of (allowed, retry_after_seconds)

        Since:
            Version 1.0.0
        """
        # Get provider limits
        limits = await self._get_provider_limits(provider)

        # Apply category multiplier
        multiplier = self.CATEGORY_MULTIPLIERS.get(category, 1.0)

        # Check all rate limit levels
        checks = [
            await self._check_minute_limit(provider, limits['rpm'] * multiplier),
            await self._check_hour_limit(provider, limits['rph'] * multiplier),
            await self._check_day_limit(provider, limits['rpd'] * multiplier)
        ]

        # If any check fails, return the longest retry time
        for allowed, retry_after in checks:
            if not allowed:
                return False, retry_after

        return True, None

    async def _check_minute_limit(
        self,
        provider: str,
        limit: float
    ) -> Tuple[bool, Optional[int]]:
        """
        Check per-minute rate limit using sliding window.

        Args:
            provider: Provider name
            limit: Requests per minute limit

        Returns:
            Tuple of (allowed, retry_after)

        Since:
            Version 1.0.0
        """
        key = f"rate_limit:minute:{provider}"
        current_time = time.time()
        window_start = current_time - 60

        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Set expiry
        pipe.expire(key, 60)

        results = await pipe.execute()
        count = results[1]

        if count >= limit:
            # Get oldest entry to calculate retry time
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(60 - (current_time - oldest[0][1]))
                return False, max(retry_after, 1)
            return False, 60

        return True, None

    async def _check_hour_limit(
        self,
        provider: str,
        limit: float
    ) -> Tuple[bool, Optional[int]]:
        """
        Check per-hour rate limit.

        Args:
            provider: Provider name
            limit: Requests per hour limit

        Returns:
            Tuple of (allowed, retry_after)

        Since:
            Version 1.0.0
        """
        key = f"rate_limit:hour:{provider}"
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        hour_key = f"{key}:{current_hour.isoformat()}"

        # Increment counter
        count = await self.redis.incr(hour_key)

        # Set expiry on first request
        if count == 1:
            await self.redis.expire(hour_key, 3600)

        if count > limit:
            # Calculate retry time (start of next hour)
            next_hour = current_hour + timedelta(hours=1)
            retry_after = int((next_hour - datetime.utcnow()).total_seconds())
            return False, max(retry_after, 1)

        return True, None

    async def _check_day_limit(
        self,
        provider: str,
        limit: float
    ) -> Tuple[bool, Optional[int]]:
        """
        Check per-day rate limit.

        Args:
            provider: Provider name
            limit: Requests per day limit

        Returns:
            Tuple of (allowed, retry_after)

        Since:
            Version 1.0.0
        """
        key = f"rate_limit:day:{provider}"
        today = datetime.utcnow().date()
        day_key = f"{key}:{today.isoformat()}"

        # Increment counter
        count = await self.redis.incr(day_key)

        # Set expiry on first request
        if count == 1:
            await self.redis.expire(day_key, 86400)

        if count > limit:
            # Calculate retry time (start of next day)
            tomorrow = datetime.combine(
                today + timedelta(days=1),
                datetime.min.time()
            )
            retry_after = int((tomorrow - datetime.utcnow()).total_seconds())
            return False, max(retry_after, 1)

        return True, None

    async def _get_provider_limits(self, provider: str) -> Dict[str, int]:
        """
        Get rate limits for provider from cache or database.

        Args:
            provider: Provider name

        Returns:
            Dictionary with rate limits

        Since:
            Version 1.0.0
        """
        # Check cache
        if provider in self.limits_cache:
            return self.limits_cache[provider]

        # Check Redis cache
        cache_key = f"provider_limits:{provider}"
        cached = await self.redis.hgetall(cache_key)

        if cached:
            limits = {
                'rpm': int(cached.get(b'rpm', 60)),
                'rph': int(cached.get(b'rph', 1000)),
                'rpd': int(cached.get(b'rpd', 10000))
            }
        else:
            # Use defaults
            limits = self.DEFAULT_PROVIDER_LIMITS.get(
                provider,
                {'rpm': 30, 'rph': 300, 'rpd': 3000}
            )

            # Cache in Redis for 1 hour
            await self.redis.hset(
                cache_key,
                mapping={
                    'rpm': limits['rpm'],
                    'rph': limits['rph'],
                    'rpd': limits['rpd']
                }
            )
            await self.redis.expire(cache_key, 3600)

        # Update local cache
        self.limits_cache[provider] = limits
        return limits

    async def get_remaining_quota(
        self,
        provider: str
    ) -> Dict[str, int]:
        """
        Get remaining quota for provider.

        Args:
            provider: Provider name

        Returns:
            Dictionary with remaining requests per time period

        Since:
            Version 1.0.0
        """
        limits = await self._get_provider_limits(provider)
        current_time = time.time()
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        today = datetime.utcnow().date()

        # Check minute window
        minute_key = f"rate_limit:minute:{provider}"
        await self.redis.zremrangebyscore(minute_key, 0, current_time - 60)
        minute_count = await self.redis.zcard(minute_key)

        # Check hour window
        hour_key = f"rate_limit:hour:{provider}:{current_hour.isoformat()}"
        hour_count = int(await self.redis.get(hour_key) or 0)

        # Check day window
        day_key = f"rate_limit:day:{provider}:{today.isoformat()}"
        day_count = int(await self.redis.get(day_key) or 0)

        return {
            'minute': max(0, limits['rpm'] - minute_count),
            'hour': max(0, limits['rph'] - hour_count),
            'day': max(0, limits['rpd'] - day_count)
        }

    async def reset_limits(self, provider: str):
        """
        Reset rate limits for provider (admin function).

        Args:
            provider: Provider name

        Since:
            Version 1.0.0
        """
        patterns = [
            f"rate_limit:minute:{provider}*",
            f"rate_limit:hour:{provider}*",
            f"rate_limit:day:{provider}*"
        ]

        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break

        logger.info(f"Reset rate limits for provider: {provider}")

    async def update_provider_limits(
        self,
        provider: str,
        rpm: Optional[int] = None,
        rph: Optional[int] = None,
        rpd: Optional[int] = None
    ):
        """
        Update rate limits for provider.

        Args:
            provider: Provider name
            rpm: Requests per minute
            rph: Requests per hour
            rpd: Requests per day

        Since:
            Version 1.0.0
        """
        cache_key = f"provider_limits:{provider}"
        updates = {}

        if rpm is not None:
            updates['rpm'] = rpm
        if rph is not None:
            updates['rph'] = rph
        if rpd is not None:
            updates['rpd'] = rpd

        if updates:
            await self.redis.hset(cache_key, mapping=updates)
            await self.redis.expire(cache_key, 3600)

            # Clear local cache
            if provider in self.limits_cache:
                del self.limits_cache[provider]

            logger.info(f"Updated rate limits for {provider}: {updates}")