"""
API endpoints for collection status reporting and monitoring.

Provides real-time visibility into data collection progress with
comprehensive audit reporting and quality indicators.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ...database.session import get_db, get_redis
from ...core.collection_monitoring import (
    CollectionMonitor,
    CollectionMetrics,
    QualityIndicators,
    CollectionStatus,
    AlertSeverity
)
from ...config.logging import PharmaceuticalLogger

router = APIRouter(prefix="/collection", tags=["Collection Monitoring"])
logger = PharmaceuticalLogger(service_name="collection_api")


class CollectionProgressResponse(BaseModel):
    """Collection progress response model."""
    process_id: str
    request_id: str
    category: str
    status: str
    completion_percentage: float
    sources_found: int
    unique_sources: int
    total_cost: float
    quality_score: float
    data_volume_mb: float
    apis_queried: Dict[str, int]
    errors: List[str]
    warnings: List[str]
    start_time: datetime
    end_time: Optional[datetime]


class SourceCoverageResponse(BaseModel):
    """Source coverage report response."""
    category: str
    total_sources: int
    source_types: Dict[str, int]
    priority_distribution: Dict[str, int]
    temperature_coverage: Dict[str, int]
    provider_coverage: Dict[str, int]
    coverage_percentage: float


class QualityIndicatorsResponse(BaseModel):
    """Quality indicators response."""
    source_priority_distribution: Dict[str, int]
    temperature_coverage: Dict[str, int]
    duplicate_count: int
    high_priority_percentage: float
    source_diversity_score: float
    verification_rate: float
    data_freshness_hours: float
    overall_quality_score: float


class AlertConfigRequest(BaseModel):
    """Alert configuration request."""
    min_quality_score: float = Field(0.6, ge=0, le=1)
    max_cost_per_request: float = Field(10.0, gt=0)
    max_collection_time_seconds: int = Field(300, gt=0)
    min_sources_required: int = Field(3, ge=1)
    max_error_rate: float = Field(0.2, ge=0, le=1)
    quota_warning_percentage: int = Field(80, ge=0, le=100)


# Initialize global monitor (would be dependency injected in production)
monitor = None


def get_monitor(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> CollectionMonitor:
    """Get or create collection monitor instance."""
    global monitor
    if not monitor:
        monitor = CollectionMonitor(db, logger, redis_client)
    return monitor


@router.get("/progress/{process_id}", response_model=CollectionProgressResponse)
async def get_collection_progress(
    process_id: str,
    monitor: CollectionMonitor = Depends(get_monitor)
) -> CollectionProgressResponse:
    """
    Get real-time collection progress for a process.

    Shows current status, completion percentage, sources found, costs,
    and quality metrics.
    """
    metrics = await monitor.get_collection_status(process_id)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No collection found for process {process_id}"
        )

    return CollectionProgressResponse(
        process_id=metrics.process_id,
        request_id=metrics.request_id,
        category=metrics.category,
        status=metrics.status.value,
        completion_percentage=metrics.completion_percentage,
        sources_found=metrics.sources_found,
        unique_sources=len(metrics.unique_sources),
        total_cost=metrics.total_cost,
        quality_score=metrics.quality_score,
        data_volume_mb=metrics.data_volume_bytes / (1024 * 1024),
        apis_queried=metrics.apis_queried,
        errors=metrics.errors,
        warnings=metrics.warnings,
        start_time=metrics.start_time,
        end_time=metrics.end_time
    )


@router.get("/active")
async def get_active_collections(
    monitor: CollectionMonitor = Depends(get_monitor)
) -> List[Dict[str, Any]]:
    """
    Get all currently active collection processes.

    Returns list of all collections currently in progress with their metrics.
    """
    active = await monitor.get_active_collections()

    return [
        {
            'process_id': m.process_id,
            'request_id': m.request_id,
            'category': m.category,
            'status': m.status.value,
            'completion_percentage': m.completion_percentage,
            'sources_found': m.sources_found,
            'duration_seconds': (
                datetime.utcnow() - m.start_time
            ).total_seconds()
        }
        for m in active
    ]


@router.get("/coverage/{category}", response_model=SourceCoverageResponse)
async def get_source_coverage(
    category: str,
    lookback_hours: int = Query(24, description="Hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> SourceCoverageResponse:
    """
    Get source coverage report for a pharmaceutical category.

    Shows which source types contributed data and coverage metrics.
    """
    try:
        from ...database.repositories.raw_data_repo import RawDataRepository

        repo = RawDataRepository(db)

        # Get recent responses for category
        start_date = datetime.utcnow() - timedelta(hours=lookback_hours)
        responses = await repo.search_by_compound(
            compound="",  # All compounds
            category=category,
            start_date=start_date,
            limit=1000
        )

        # Analyze source coverage
        source_types = {}
        priority_distribution = {}
        temperature_coverage = {}
        provider_coverage = {}
        unique_sources = set()

        for response in responses:
            # Count by provider
            provider = response.provider
            provider_coverage[provider] = provider_coverage.get(provider, 0) + 1

            # Extract metadata
            if response.metadata:
                # Temperature coverage
                temp = response.temperature
                if temp:
                    temp_key = f"{temp:.1f}"
                    temperature_coverage[temp_key] = temperature_coverage.get(temp_key, 0) + 1

                # Priority distribution
                if 'hierarchical_processing' in response.metadata:
                    for priority, count in response.metadata['hierarchical_processing'].get('priority_distribution', {}).items():
                        priority_distribution[priority] = priority_distribution.get(priority, 0) + count

            # Track unique sources
            if response.correlation_id:
                unique_sources.add(response.correlation_id)

        total_sources = len(responses)
        coverage_percentage = min(100, (total_sources / 10) * 100)  # Assume 10 sources is 100% coverage

        return SourceCoverageResponse(
            category=category,
            total_sources=total_sources,
            source_types=source_types,
            priority_distribution=priority_distribution,
            temperature_coverage=temperature_coverage,
            provider_coverage=provider_coverage,
            coverage_percentage=coverage_percentage
        )

    except Exception as e:
        logger.error(f"Failed to get source coverage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate coverage report"
        )


@router.get("/quality/{process_id}", response_model=QualityIndicatorsResponse)
async def get_quality_indicators(
    process_id: str,
    db: AsyncSession = Depends(get_db)
) -> QualityIndicatorsResponse:
    """
    Get quality indicators for a collection process.

    Shows source priority distribution, temperature coverage, duplicates,
    and overall quality metrics.
    """
    try:
        from ...database.repositories.raw_data_repo import RawDataRepository

        repo = RawDataRepository(db)

        # Get responses for process
        responses = await repo.get_by_process_id(process_id)

        # Calculate quality indicators
        priority_dist = {}
        temp_coverage = {}
        duplicates = set()
        unique_contents = set()
        high_priority_count = 0
        verified_count = 0

        for response in responses:
            # Check for duplicates
            content_hash = hash(str(response.raw_response))
            if content_hash in unique_contents:
                duplicates.add(content_hash)
            unique_contents.add(content_hash)

            # Temperature coverage
            temp_key = f"{response.temperature:.1f}"
            temp_coverage[temp_key] = temp_coverage.get(temp_key, 0) + 1

            # Priority distribution
            if response.metadata and 'hierarchical_processing' in response.metadata:
                for priority in ['PAID_APIS', 'GOVERNMENT', 'PEER_REVIEWED']:
                    if priority in response.metadata['hierarchical_processing'].get('priority_distribution', {}):
                        high_priority_count += 1
                        break

            # Verification rate
            if response.is_valid:
                verified_count += 1

        total = len(responses)
        indicators = QualityIndicators(
            source_priority_distribution=priority_dist,
            temperature_coverage=temp_coverage,
            duplicate_count=len(duplicates),
            high_priority_percentage=high_priority_count / max(total, 1),
            source_diversity_score=len(unique_contents) / max(total, 1),
            verification_rate=verified_count / max(total, 1),
            data_freshness_hours=0  # Would calculate from timestamps
        )

        # Calculate overall quality score
        quality_score = (
            indicators.high_priority_percentage * 0.3 +
            indicators.source_diversity_score * 0.3 +
            indicators.verification_rate * 0.2 +
            (1 - len(duplicates) / max(total, 1)) * 0.2
        )

        return QualityIndicatorsResponse(
            source_priority_distribution=indicators.source_priority_distribution,
            temperature_coverage=indicators.temperature_coverage,
            duplicate_count=indicators.duplicate_count,
            high_priority_percentage=indicators.high_priority_percentage,
            source_diversity_score=indicators.source_diversity_score,
            verification_rate=indicators.verification_rate,
            data_freshness_hours=indicators.data_freshness_hours,
            overall_quality_score=quality_score
        )

    except Exception as e:
        logger.error(f"Failed to get quality indicators: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quality indicators"
        )


@router.post("/alerts/configure")
async def configure_alerts(
    config: AlertConfigRequest,
    monitor: CollectionMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Configure alert thresholds for collection monitoring.

    Sets thresholds for quality scores, costs, timing, and error rates.
    """
    monitor.alert_thresholds.update(config.dict())

    # Log configuration change
    await logger.log_system_event(
        event_type="alert_configuration_updated",
        process_id="system",
        component="collection_monitor",
        details=config.dict()
    )

    return {
        'status': 'success',
        'thresholds': monitor.alert_thresholds
    }


@router.get("/alerts/recent")
async def get_recent_alerts(
    hours: int = Query(24, description="Hours to look back"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    redis_client: redis.Redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """
    Get recent collection alerts.

    Returns alerts triggered in the specified time period.
    """
    if not redis_client:
        return []

    import json

    alerts = []
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Get all alert keys
    alert_keys = await redis_client.keys("alerts:*")

    for key in alert_keys:
        alert_list = await redis_client.lrange(key, 0, -1)

        for alert_data in alert_list:
            try:
                alert = json.loads(alert_data)
                alert_time = datetime.fromisoformat(alert['timestamp'])

                if alert_time >= cutoff_time:
                    if not severity or alert['severity'] == severity:
                        alerts.append(alert)

            except Exception as e:
                logger.error(f"Failed to parse alert: {e}")

    # Sort by timestamp
    alerts.sort(key=lambda x: x['timestamp'], reverse=True)

    return alerts[:100]  # Limit to 100 most recent


@router.get("/performance/historical")
async def get_historical_performance(
    category: Optional[str] = Query(None, description="Filter by category"),
    days: int = Query(7, description="Days to look back"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical collection performance metrics.

    Shows trends in collection times, costs, quality scores, and source counts.
    """
    try:
        from sqlalchemy import select, func, and_
        from ...database.models import ProcessTracking

        start_date = datetime.utcnow() - timedelta(days=days)

        # Build query
        conditions = [ProcessTracking.created_at >= start_date]

        if category:
            conditions.append(
                ProcessTracking.metadata['collection_metrics']['category'].astext == category
            )

        # Get aggregated metrics
        query = select(
            func.date(ProcessTracking.created_at).label('date'),
            func.count(ProcessTracking.id).label('collection_count'),
            func.avg(
                ProcessTracking.metadata['collection_metrics']['total_cost'].cast(Float)
            ).label('avg_cost'),
            func.avg(
                ProcessTracking.metadata['collection_metrics']['sources_found'].cast(Integer)
            ).label('avg_sources'),
            func.avg(
                ProcessTracking.metadata['collection_metrics']['quality_score'].cast(Float)
            ).label('avg_quality')
        ).where(
            and_(*conditions)
        ).group_by(
            func.date(ProcessTracking.created_at)
        ).order_by('date')

        result = await db.execute(query)
        daily_metrics = []

        for row in result:
            daily_metrics.append({
                'date': row.date.isoformat(),
                'collection_count': row.collection_count,
                'avg_cost': float(row.avg_cost) if row.avg_cost else 0,
                'avg_sources': int(row.avg_sources) if row.avg_sources else 0,
                'avg_quality': float(row.avg_quality) if row.avg_quality else 0
            })

        # Calculate trends
        if len(daily_metrics) >= 2:
            first_day = daily_metrics[0]
            last_day = daily_metrics[-1]

            trends = {
                'cost_trend': (last_day['avg_cost'] - first_day['avg_cost']) / max(first_day['avg_cost'], 0.01),
                'sources_trend': (last_day['avg_sources'] - first_day['avg_sources']) / max(first_day['avg_sources'], 1),
                'quality_trend': (last_day['avg_quality'] - first_day['avg_quality']) / max(first_day['avg_quality'], 0.01)
            }
        else:
            trends = {
                'cost_trend': 0,
                'sources_trend': 0,
                'quality_trend': 0
            }

        return {
            'period_days': days,
            'category': category,
            'daily_metrics': daily_metrics,
            'trends': trends,
            'total_collections': sum(d['collection_count'] for d in daily_metrics)
        }

    except Exception as e:
        logger.error(f"Failed to get historical performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get historical performance"
        )