"""
Health checking system for pharmaceutical platform components.

Performs health checks on all system dependencies and components
for pharmaceutical operational compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
import time
import psutil
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import aiohttp

from ..schemas.health import (
    HealthStatus,
    DependencyHealth,
    APIProviderHealth,
    ConnectionPoolStatus,
    RedisStatus,
    WorkerStatus,
    MemoryUsage
)

logger = structlog.get_logger(__name__)

# Service start time for uptime calculation
SERVICE_START_TIME = datetime.utcnow()


class HealthChecker:
    """
    Performs comprehensive health checks on system components.

    Since:
        Version 1.0.0
    """

    def __init__(self, db_session: Optional[AsyncSession] = None, redis_client: Optional[redis.Redis] = None):
        """
        Initialize health checker.

        Args:
            db_session: Database session for connectivity checks
            redis_client: Redis client for cache checks

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.redis_client = redis_client

    async def check_database_health(self) -> DependencyHealth:
        """
        Check PostgreSQL database health.

        Returns:
            Database health status

        Since:
            Version 1.0.0
        """
        start_time = time.time()

        try:
            if not self.db:
                return DependencyHealth(
                    name="postgresql",
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.utcnow(),
                    error="No database session available"
                )

            # Execute simple query to test connectivity
            result = await self.db.execute(text("SELECT 1"))
            result.scalar()

            # Get connection pool stats if available
            pool_stats = {}
            if hasattr(self.db.bind, 'pool'):
                pool = self.db.bind.pool
                pool_stats = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "total": pool.total()
                }

            response_time = (time.time() - start_time) * 1000

            return DependencyHealth(
                name="postgresql",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                details=pool_stats
            )

        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return DependencyHealth(
                name="postgresql",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error=str(e)
            )

    async def check_redis_health(self) -> DependencyHealth:
        """
        Check Redis cache health.

        Returns:
            Redis health status

        Since:
            Version 1.0.0
        """
        start_time = time.time()

        try:
            if not self.redis_client:
                return DependencyHealth(
                    name="redis",
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.utcnow(),
                    error="No Redis client available"
                )

            # Ping Redis
            await self.redis_client.ping()

            # Get Redis info
            info = await self.redis_client.info()
            memory_info = info.get('memory', {})

            details = {
                "used_memory_mb": memory_info.get('used_memory', 0) / 1024 / 1024,
                "used_memory_peak_mb": memory_info.get('used_memory_peak', 0) / 1024 / 1024,
                "connected_clients": info.get('clients', {}).get('connected_clients', 0)
            }

            response_time = (time.time() - start_time) * 1000

            return DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                details=details
            )

        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return DependencyHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error=str(e)
            )

    async def check_api_provider_health(self, provider: str, test_endpoint: str) -> APIProviderHealth:
        """
        Check external API provider health.

        Args:
            provider: Provider name
            test_endpoint: Endpoint to test connectivity

        Returns:
            API provider health status

        Since:
            Version 1.0.0
        """
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(test_endpoint, timeout=5) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status < 300:
                        return APIProviderHealth(
                            provider=provider,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time,
                            last_successful_call=datetime.utcnow()
                        )
                    else:
                        return APIProviderHealth(
                            provider=provider,
                            status=HealthStatus.DEGRADED,
                            response_time_ms=response_time,
                            error_count=1
                        )

        except asyncio.TimeoutError:
            return APIProviderHealth(
                provider=provider,
                status=HealthStatus.UNHEALTHY,
                error_count=1
            )
        except Exception as e:
            logger.error(f"API provider {provider} health check failed", error=str(e))
            return APIProviderHealth(
                provider=provider,
                status=HealthStatus.UNHEALTHY,
                error_count=1
            )

    async def check_all_api_providers(self) -> List[DependencyHealth]:
        """
        Check health of all configured API providers.

        Returns:
            List of API provider health statuses

        Since:
            Version 1.0.0
        """
        providers = {
            "openai": "https://api.openai.com/v1/models",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "google": "https://www.googleapis.com/customsearch/v1",
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test"
        }

        health_checks = []
        for provider, endpoint in providers.items():
            health = await self.check_api_provider_health(provider, endpoint)
            health_checks.append(DependencyHealth(
                name=f"api_{provider}",
                status=health.status,
                response_time_ms=health.response_time_ms,
                last_check=datetime.utcnow(),
                error=f"Error count: {health.error_count}" if health.error_count > 0 else None
            ))

        return health_checks

    def get_memory_usage(self) -> MemoryUsage:
        """
        Get current memory usage statistics.

        Returns:
            Memory usage information

        Since:
            Version 1.0.0
        """
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        return MemoryUsage(
            used_mb=memory.used / 1024 / 1024,
            available_mb=memory.available / 1024 / 1024,
            total_mb=memory.total / 1024 / 1024,
            percentage_used=memory.percent,
            process_mb=process_memory.rss / 1024 / 1024
        )

    async def get_database_pool_status(self) -> ConnectionPoolStatus:
        """
        Get database connection pool status.

        Returns:
            Connection pool statistics

        Since:
            Version 1.0.0
        """
        if not self.db or not hasattr(self.db.bind, 'pool'):
            return ConnectionPoolStatus(
                active=0,
                idle=0,
                total_capacity=0,
                utilization_percentage=0.0
            )

        pool = self.db.bind.pool
        active = pool.checkedout()
        idle = pool.checkedin()
        total = pool.size()

        return ConnectionPoolStatus(
            active=active,
            idle=idle,
            total_capacity=total,
            utilization_percentage=(active / total * 100) if total > 0 else 0.0,
            wait_queue=pool.overflow if hasattr(pool, 'overflow') else 0
        )

    async def get_redis_status(self) -> RedisStatus:
        """
        Get Redis cache status.

        Returns:
            Redis statistics

        Since:
            Version 1.0.0
        """
        if not self.redis_client:
            return RedisStatus(
                connected=False,
                used_memory_mb=0,
                max_memory_mb=0,
                keys_count=0,
                hit_rate=0.0,
                response_time_ms=0
            )

        try:
            info = await self.redis_client.info()
            memory_info = info.get('memory', {})
            stats_info = info.get('stats', {})

            # Calculate hit rate
            hits = stats_info.get('keyspace_hits', 0)
            misses = stats_info.get('keyspace_misses', 0)
            hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0

            # Get key count
            db_info = info.get('db0', {})
            keys_count = db_info.get('keys', 0) if isinstance(db_info, dict) else 0

            return RedisStatus(
                connected=True,
                used_memory_mb=memory_info.get('used_memory', 0) / 1024 / 1024,
                max_memory_mb=memory_info.get('maxmemory', 0) / 1024 / 1024,
                keys_count=keys_count,
                hit_rate=hit_rate,
                response_time_ms=0  # Would need to track this separately
            )

        except Exception as e:
            logger.error("Failed to get Redis status", error=str(e))
            return RedisStatus(
                connected=False,
                used_memory_mb=0,
                max_memory_mb=0,
                keys_count=0,
                hit_rate=0.0,
                response_time_ms=0
            )

    def get_worker_status(self) -> WorkerStatus:
        """
        Get background worker status.

        Returns:
            Worker statistics

        Since:
            Version 1.0.0
        """
        # TODO: Integrate with Celery or background task system
        return WorkerStatus(
            active_workers=0,
            idle_workers=4,
            queue_depth=0,
            tasks_completed=0,
            tasks_failed=0,
            average_processing_time_ms=0
        )

    def calculate_overall_health(self, health_checks: List[DependencyHealth]) -> HealthStatus:
        """
        Calculate overall system health from dependency checks.

        Args:
            health_checks: List of dependency health statuses

        Returns:
            Overall health status

        Since:
            Version 1.0.0
        """
        if not health_checks:
            return HealthStatus.UNKNOWN

        unhealthy_count = sum(1 for check in health_checks if check.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for check in health_checks if check.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_uptime_seconds(self) -> float:
        """
        Get service uptime in seconds.

        Returns:
            Uptime in seconds

        Since:
            Version 1.0.0
        """
        uptime = datetime.utcnow() - SERVICE_START_TIME
        return uptime.total_seconds()