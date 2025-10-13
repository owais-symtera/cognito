"""
System diagnostics API endpoints for pharmaceutical platform monitoring.

Provides detailed system diagnostics, performance metrics, and
operational monitoring for pharmaceutical compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from ...database.connection import get_db_session
from ...schemas.health import SystemDiagnosticsResponse, SystemAlert
from ...core.health_checker import HealthChecker
from ...core.metrics_collector import metrics_collector
from ...auth.dependencies import require_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
    responses={503: {"description": "Service temporarily unavailable"}}
)


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client for diagnostics.

    Returns:
        Redis client

    Since:
        Version 1.0.0
    """
    from ...core.config import settings
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        decode_responses=True
    )


@router.get(
    "",
    response_model=SystemDiagnosticsResponse,
    summary="Get system diagnostics",
    description="Comprehensive system diagnostics including performance metrics"
)
async def get_system_diagnostics(
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> SystemDiagnosticsResponse:
    """
    Get comprehensive system diagnostics.

    Provides detailed system information including:
    - Active request counts
    - Queue depths
    - Database connection pool status
    - Redis cache status
    - Worker status
    - Memory usage
    - Performance metrics
    - Active alerts

    Args:
        db: Database session
        api_key: API key for authentication

    Returns:
        Complete system diagnostics

    Since:
        Version 1.0.0
    """
    redis_client = None

    try:
        redis_client = await get_redis_client()
        checker = HealthChecker(db, redis_client)

        # Get active requests
        active_requests = await metrics_collector.get_active_requests_count(db)

        # Get queue depth
        queue_depth = await metrics_collector.get_processing_queue_depth(db)

        # Get database pool status
        db_pool_status = await checker.get_database_pool_status()

        # Get Redis status
        redis_status = await checker.get_redis_status()

        # Get worker status
        worker_status = await metrics_collector.get_worker_metrics(db)

        # Get memory usage
        memory_usage = checker.get_memory_usage()

        # Get performance metrics
        performance_metrics = metrics_collector.get_performance_metrics()

        # Check for system alerts
        system_alerts = await check_system_alerts(
            memory_usage.percentage_used,
            queue_depth,
            performance_metrics.error_rate
        )

        logger.info(
            "System diagnostics retrieved",
            active_requests=active_requests,
            queue_depth=queue_depth,
            alerts_count=len(system_alerts)
        )

        return SystemDiagnosticsResponse(
            timestamp=datetime.utcnow(),
            active_requests=active_requests,
            processing_queue_depth=queue_depth,
            database_connections=db_pool_status,
            redis_status=redis_status,
            worker_status=worker_status,
            memory_usage=memory_usage,
            performance_metrics=performance_metrics,
            system_alerts=system_alerts
        )

    except Exception as e:
        logger.error("Failed to get system diagnostics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve diagnostics: {str(e)}"
        )
    finally:
        if redis_client:
            await redis_client.close()


@router.get(
    "/metrics",
    summary="Get performance metrics",
    description="Current system performance metrics"
)
async def get_performance_metrics(
    api_key: str = Depends(require_api_key)
) -> dict:
    """
    Get current performance metrics.

    Returns:
        Performance metrics summary

    Since:
        Version 1.0.0
    """
    metrics = metrics_collector.get_performance_metrics()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "api_response_time": {
                "average_ms": metrics.avg_api_response_time_ms,
                "p95_ms": metrics.p95_api_response_time_ms,
                "p99_ms": metrics.p99_api_response_time_ms
            },
            "database": {
                "average_query_time_ms": metrics.avg_db_query_time_ms
            },
            "throughput": {
                "requests_per_minute": metrics.requests_per_minute
            },
            "cache": {
                "hit_rate_percentage": metrics.cache_hit_rate
            },
            "errors": {
                "error_rate_percentage": metrics.error_rate
            }
        }
    }


@router.get(
    "/alerts",
    response_model=List[SystemAlert],
    summary="Get active system alerts",
    description="List of currently active system alerts"
)
async def get_active_alerts(
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> List[SystemAlert]:
    """
    Get list of active system alerts.

    Returns:
        List of active alerts

    Since:
        Version 1.0.0
    """
    alerts = []

    # Check memory usage
    checker = HealthChecker(db)
    memory = checker.get_memory_usage()

    if memory.percentage_used > 85:
        alerts.append(SystemAlert(
            alert_id=f"mem_{datetime.utcnow().timestamp()}",
            alert_type="high_memory_usage",
            severity="warning" if memory.percentage_used < 95 else "critical",
            message=f"Memory usage at {memory.percentage_used:.1f}%",
            triggered_at=datetime.utcnow(),
            component="system",
            metadata={"percentage_used": memory.percentage_used}
        ))

    # Check queue depth
    queue_depth = await metrics_collector.get_processing_queue_depth(db)
    if queue_depth > 100:
        alerts.append(SystemAlert(
            alert_id=f"queue_{datetime.utcnow().timestamp()}",
            alert_type="queue_overflow",
            severity="warning",
            message=f"Processing queue depth at {queue_depth}",
            triggered_at=datetime.utcnow(),
            component="processing",
            metadata={"queue_depth": queue_depth}
        ))

    # Check error rate
    error_rate = metrics_collector.get_error_rate()
    if error_rate > 5:
        alerts.append(SystemAlert(
            alert_id=f"error_{datetime.utcnow().timestamp()}",
            alert_type="high_error_rate",
            severity="warning" if error_rate < 10 else "critical",
            message=f"Error rate at {error_rate:.1f}%",
            triggered_at=datetime.utcnow(),
            component="api",
            metadata={"error_rate": error_rate}
        ))

    return alerts


async def check_system_alerts(
    memory_percentage: float,
    queue_depth: int,
    error_rate: float
) -> List[str]:
    """
    Check for system alert conditions.

    Args:
        memory_percentage: Memory usage percentage
        queue_depth: Processing queue depth
        error_rate: Error rate percentage

    Returns:
        List of alert messages

    Since:
        Version 1.0.0
    """
    alerts = []

    if memory_percentage > 85:
        severity = "WARNING" if memory_percentage < 95 else "CRITICAL"
        alerts.append(f"{severity}: Memory usage at {memory_percentage:.1f}%")

    if queue_depth > 100:
        alerts.append(f"WARNING: Processing queue depth at {queue_depth}")

    if error_rate > 5:
        severity = "WARNING" if error_rate < 10 else "CRITICAL"
        alerts.append(f"{severity}: Error rate at {error_rate:.1f}%")

    # Check response times
    metrics = metrics_collector.get_performance_metrics()
    if metrics.p99_api_response_time_ms > 5000:
        alerts.append(f"WARNING: P99 response time at {metrics.p99_api_response_time_ms:.0f}ms")

    return alerts