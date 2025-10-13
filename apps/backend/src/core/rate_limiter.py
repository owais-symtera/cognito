"""
Rate limiting for pharmaceutical analysis API.

Implements token bucket algorithm for API rate limiting
with Redis-based distributed tracking.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import time
import asyncio
from typing import Optional, Tuple
import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Implements distributed rate limiting using Redis for
    pharmaceutical API compliance and fair usage.
    
    Since:
        Version 1.0.0
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        time_window: int = 60,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            redis_client: Optional Redis client for distributed limiting
        
        Since:
            Version 1.0.0
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.redis_client = redis_client
        
        # In-memory fallback if Redis not available
        self.memory_buckets = {}
    
    async def check_rate_limit(
        self,
        identifier: str,
        increment: int = 1
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (API key, IP, etc.)
            increment: Number of tokens to consume
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        
        Since:
            Version 1.0.0
        """
        if self.redis_client:
            return await self._check_redis_limit(identifier, increment)
        else:
            return await self._check_memory_limit(identifier, increment)
    
    async def _check_redis_limit(
        self,
        identifier: str,
        increment: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using Redis.
        
        Args:
            identifier: Unique identifier
            increment: Number of tokens to consume
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        
        Since:
            Version 1.0.0
        """
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - self.time_window
            
            # Use Redis pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Remove old entries
                await pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                await pipe.zcard(key)
                
                # Execute pipeline
                results = await pipe.execute()
                current_count = results[1]
                
                # Check if limit exceeded
                if current_count >= self.max_requests:
                    # Get oldest entry to calculate retry time
                    oldest = await self.redis_client.zrange(
                        key, 0, 0, withscores=True
                    )
                    if oldest:
                        retry_after = int(oldest[0][1]) + self.time_window - current_time
                        return False, max(1, retry_after)
                    return False, self.time_window
                
                # Add new request
                await self.redis_client.zadd(
                    key,
                    {f"{identifier}:{current_time}:{increment}": current_time}
                )
                
                # Set expiry
                await self.redis_client.expire(key, self.time_window)
                
                return True, None
                
        except Exception as e:
            logger.error(
                "Redis rate limit check failed, falling back to memory",
                error=str(e),
                identifier=identifier
            )
            return await self._check_memory_limit(identifier, increment)
    
    async def _check_memory_limit(
        self,
        identifier: str,
        increment: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using in-memory storage.
        
        Args:
            identifier: Unique identifier
            increment: Number of tokens to consume
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        
        Since:
            Version 1.0.0
        """
        current_time = time.time()
        
        # Initialize bucket if not exists
        if identifier not in self.memory_buckets:
            self.memory_buckets[identifier] = {
                "tokens": self.max_requests,
                "last_refill": current_time
            }
        
        bucket = self.memory_buckets[identifier]
        
        # Calculate tokens to add based on elapsed time
        elapsed = current_time - bucket["last_refill"]
        tokens_to_add = (elapsed / self.time_window) * self.max_requests
        
        # Refill bucket
        bucket["tokens"] = min(
            self.max_requests,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_refill"] = current_time
        
        # Check if enough tokens
        if bucket["tokens"] >= increment:
            bucket["tokens"] -= increment
            return True, None
        
        # Calculate retry time
        tokens_needed = increment - bucket["tokens"]
        seconds_until_tokens = (
            tokens_needed / self.max_requests
        ) * self.time_window
        
        return False, int(seconds_until_tokens) + 1
    
    async def get_remaining_quota(
        self,
        identifier: str
    ) -> Tuple[int, int]:
        """
        Get remaining request quota for identifier.
        
        Args:
            identifier: Unique identifier
        
        Returns:
            Tuple of (remaining_requests, reset_time_seconds)
        
        Since:
            Version 1.0.0
        """
        if self.redis_client:
            try:
                key = f"rate_limit:{identifier}"
                current_time = int(time.time())
                window_start = current_time - self.time_window
                
                # Remove old entries
                await self.redis_client.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                current_count = await self.redis_client.zcard(key)
                remaining = max(0, self.max_requests - current_count)
                
                return remaining, self.time_window
                
            except Exception as e:
                logger.error(
                    "Failed to get quota from Redis",
                    error=str(e),
                    identifier=identifier
                )
        
        # Fallback to memory
        if identifier in self.memory_buckets:
            bucket = self.memory_buckets[identifier]
            current_time = time.time()
            elapsed = current_time - bucket["last_refill"]
            tokens_to_add = (elapsed / self.time_window) * self.max_requests
            current_tokens = min(
                self.max_requests,
                bucket["tokens"] + tokens_to_add
            )
            return int(current_tokens), self.time_window
        
        return self.max_requests, self.time_window
    
    async def reset_limit(self, identifier: str) -> bool:
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: Unique identifier to reset
        
        Returns:
            True if reset successful
        
        Since:
            Version 1.0.0
        """
        if self.redis_client:
            try:
                key = f"rate_limit:{identifier}"
                await self.redis_client.delete(key)
                logger.info("Rate limit reset via Redis", identifier=identifier)
                return True
            except Exception as e:
                logger.error(
                    "Failed to reset limit in Redis",
                    error=str(e),
                    identifier=identifier
                )
        
        # Reset in memory
        if identifier in self.memory_buckets:
            del self.memory_buckets[identifier]
            logger.info("Rate limit reset in memory", identifier=identifier)
        
        return True