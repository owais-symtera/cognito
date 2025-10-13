"""
Health monitoring API endpoints for pharmaceutical platform.

Provides health checks, system diagnostics, and monitoring endpoints
for pharmaceutical operational compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from ...database.connection import get_db_session
from ...schemas.health import (
    HealthStatus,
    HealthResponse,
    DetailedHealthResponse,
    DependencyHealth,
    SystemDiagnosticsResponse
)
from ...core.health_checker import HealthChecker
from ...core.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={503: {"description": "Service unavailable"}}
)


async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for health checks.

    Returns:
        Redis client or None

    Since:
        Version 1.0.0
    """
    try:
        # TODO: Implement proper Redis connection pooling
        from ...core.config import settings
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        return client
    except Exception as e:
        logger.error("Failed to create Redis client", error=str(e))
        return None


@router.get(
    "",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Simple health check for load balancers and monitoring"
)
async def basic_health_check() -> HealthResponse:
    """
    Basic service health check.

    Returns immediately with service status without checking dependencies.
    Used for load balancer health probes.

    Returns:
        Basic health status

    Since:
        Version 1.0.0
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        service="cognito-ai-engine"
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Comprehensive health check including all dependencies"
)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db_session)
) -> DetailedHealthResponse:
    """
    Comprehensive health check with dependency validation.

    Checks all system dependencies including database, Redis, and external APIs.
    Returns detailed health information for monitoring dashboards.

    Args:
        db: Database session

    Returns:
        Detailed health status with dependency information

    Since:
        Version 1.0.0
    """
    redis_client = await get_redis_client()
    checker = HealthChecker(db, redis_client)

    health_checks = []

    # Check database
    db_health = await checker.check_database_health()
    health_checks.append(db_health)

    # Check Redis
    redis_health = await checker.check_redis_health()
    health_checks.append(redis_health)

    # Check external API providers
    api_health_checks = await checker.check_all_api_providers()
    health_checks.extend(api_health_checks)

    # Calculate overall status
    overall_status = checker.calculate_overall_health(health_checks)

    # Count passed/failed checks
    checks_passed = sum(1 for check in health_checks if check.status == HealthStatus.HEALTHY)
    checks_failed = sum(1 for check in health_checks if check.status == HealthStatus.UNHEALTHY)

    # Get uptime
    uptime = checker.get_uptime_seconds()

    # Clean up Redis connection
    if redis_client:
        await redis_client.close()

    logger.info(
        "Detailed health check completed",
        overall_status=overall_status.value,
        checks_passed=checks_passed,
        checks_failed=checks_failed
    )

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        dependencies=health_checks,
        uptime_seconds=uptime,
        checks_passed=checks_passed,
        checks_failed=checks_failed
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint"
)
async def liveness_probe() -> dict:
    """
    Kubernetes liveness probe.

    Returns simple OK response to indicate service is alive.
    Does not check dependencies.

    Returns:
        Liveness status

    Since:
        Version 1.0.0
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint"
)
async def readiness_probe(
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Kubernetes readiness probe.

    Checks if service is ready to handle requests by validating
    critical dependencies.

    Args:
        db: Database session

    Returns:
        Readiness status

    Since:
        Version 1.0.0
    """
    checker = HealthChecker(db)

    # Check critical dependencies
    db_health = await checker.check_database_health()

    if db_health.status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready - database unavailable"
        )

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/dependencies/{dependency}",
    response_model=DependencyHealth,
    summary="Check specific dependency",
    description="Health check for a specific dependency"
)
async def check_specific_dependency(
    dependency: str,
    db: AsyncSession = Depends(get_db_session)
) -> DependencyHealth:
    """
    Check health of specific dependency.

    Args:
        dependency: Dependency name (postgresql, redis, openai, etc.)
        db: Database session

    Returns:
        Dependency health status

    Since:
        Version 1.0.0
    """
    redis_client = await get_redis_client()
    checker = HealthChecker(db, redis_client)

    try:
        if dependency == "postgresql":
            health = await checker.check_database_health()
        elif dependency == "redis":
            health = await checker.check_redis_health()
        elif dependency in ["openai", "anthropic", "google", "pubmed"]:
            provider_map = {
                "openai": "https://api.openai.com/v1/models",
                "anthropic": "https://api.anthropic.com/v1/messages",
                "google": "https://www.googleapis.com/customsearch/v1",
                "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test"
            }
            api_health = await checker.check_api_provider_health(
                dependency,
                provider_map[dependency]
            )
            health = DependencyHealth(
                name=dependency,
                status=api_health.status,
                response_time_ms=api_health.response_time_ms,
                last_check=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown dependency: {dependency}"
            )

        return health

    finally:
        if redis_client:
            await redis_client.close()