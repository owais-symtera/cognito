"""
Collection status reporting and monitoring for pharmaceutical intelligence.

Provides real-time visibility into data collection progress with comprehensive
audit reporting and compliance transparency.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import structlog

from ..config.logging import PharmaceuticalLogger
from ..database.models import ProcessTracking, APIResponse

logger = structlog.get_logger(__name__)


class CollectionStatus(Enum):
    """
    Status of collection process.

    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class AlertSeverity(Enum):
    """
    Alert severity levels.

    Since:
        Version 1.0.0
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CollectionMetrics:
    """
    Metrics for collection monitoring.

    Since:
        Version 1.0.0
    """
    request_id: str
    process_id: str
    category: str
    status: CollectionStatus
    total_categories: int = 0
    completed_categories: int = 0
    apis_queried: Dict[str, int] = field(default_factory=dict)
    sources_found: int = 0
    unique_sources: Set[str] = field(default_factory=set)
    data_volume_bytes: int = 0
    total_cost: float = 0.0
    quality_score: float = 0.0
    completion_percentage: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class QualityIndicators:
    """
    Quality indicators for collection.

    Since:
        Version 1.0.0
    """
    source_priority_distribution: Dict[str, int] = field(default_factory=dict)
    temperature_coverage: Dict[float, int] = field(default_factory=dict)
    duplicate_count: int = 0
    high_priority_percentage: float = 0.0
    source_diversity_score: float = 0.0
    verification_rate: float = 0.0
    data_freshness_hours: float = 0.0


class CollectionMonitor:
    """
    Monitors and reports on data collection progress.

    Provides real-time metrics, quality indicators, and alert management
    for pharmaceutical intelligence gathering.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db_session,
        audit_logger: PharmaceuticalLogger,
        redis_client=None,
        alert_thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize collection monitor.

        Args:
            db_session: Database session
            audit_logger: Audit logger
            redis_client: Redis client for caching
            alert_thresholds: Custom alert thresholds

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.audit_logger = audit_logger
        self.redis = redis_client
        self.alert_thresholds = alert_thresholds or self._default_thresholds()
        self.active_collections: Dict[str, CollectionMetrics] = {}
        self.alert_callbacks = []

    def _default_thresholds(self) -> Dict[str, Any]:
        """
        Get default alert thresholds.

        Returns:
            Default threshold configuration

        Since:
            Version 1.0.0
        """
        return {
            'min_quality_score': 0.6,
            'max_cost_per_request': 10.0,
            'max_collection_time_seconds': 300,
            'min_sources_required': 3,
            'max_error_rate': 0.2,
            'quota_warning_percentage': 80
        }

    async def start_collection_monitoring(
        self,
        request_id: str,
        process_id: str,
        category: str,
        total_categories: int = 1
    ) -> CollectionMetrics:
        """
        Start monitoring a new collection.

        Args:
            request_id: Drug request ID
            process_id: Process tracking ID
            category: Pharmaceutical category
            total_categories: Total categories to collect

        Returns:
            Collection metrics instance

        Since:
            Version 1.0.0
        """
        metrics = CollectionMetrics(
            request_id=request_id,
            process_id=process_id,
            category=category,
            status=CollectionStatus.IN_PROGRESS,
            total_categories=total_categories
        )

        self.active_collections[process_id] = metrics

        # Log collection start
        await self.audit_logger.log_system_event(
            event_type="collection_monitoring_started",
            process_id=process_id,
            component="collection_monitor",
            details={
                'request_id': request_id,
                'category': category,
                'total_categories': total_categories
            }
        )

        # Cache in Redis if available
        if self.redis:
            await self._cache_metrics(metrics)

        return metrics

    async def update_collection_progress(
        self,
        process_id: str,
        updates: Dict[str, Any]
    ) -> Optional[CollectionMetrics]:
        """
        Update collection progress metrics.

        Args:
            process_id: Process ID
            updates: Metric updates

        Returns:
            Updated metrics or None

        Since:
            Version 1.0.0
        """
        metrics = self.active_collections.get(process_id)

        if not metrics:
            # Try to load from cache
            metrics = await self._load_from_cache(process_id)

        if not metrics:
            logger.warning(f"No metrics found for process {process_id}")
            return None

        # Update metrics
        if 'apis_queried' in updates:
            for api, count in updates['apis_queried'].items():
                metrics.apis_queried[api] = metrics.apis_queried.get(api, 0) + count

        if 'sources_found' in updates:
            metrics.sources_found += updates['sources_found']

        if 'unique_sources' in updates:
            metrics.unique_sources.update(updates['unique_sources'])

        if 'data_volume_bytes' in updates:
            metrics.data_volume_bytes += updates['data_volume_bytes']

        if 'total_cost' in updates:
            metrics.total_cost += updates['total_cost']

        if 'completed_categories' in updates:
            metrics.completed_categories = updates['completed_categories']

        if 'errors' in updates:
            metrics.errors.extend(updates['errors'])

        if 'warnings' in updates:
            metrics.warnings.extend(updates['warnings'])

        # Calculate completion percentage
        metrics.completion_percentage = (
            metrics.completed_categories / max(metrics.total_categories, 1)
        ) * 100

        # Check for alerts
        await self._check_alerts(metrics)

        # Update cache
        if self.redis:
            await self._cache_metrics(metrics)

        return metrics

    async def complete_collection(
        self,
        process_id: str,
        quality_indicators: Optional[QualityIndicators] = None
    ) -> Optional[CollectionMetrics]:
        """
        Mark collection as complete and calculate final metrics.

        Args:
            process_id: Process ID
            quality_indicators: Final quality indicators

        Returns:
            Final metrics or None

        Since:
            Version 1.0.0
        """
        metrics = self.active_collections.get(process_id)

        if not metrics:
            metrics = await self._load_from_cache(process_id)

        if not metrics:
            return None

        # Update status and timing
        metrics.status = CollectionStatus.COMPLETED
        metrics.end_time = datetime.utcnow()
        metrics.completion_percentage = 100.0

        # Calculate quality score
        if quality_indicators:
            metrics.quality_score = self._calculate_quality_score(
                metrics,
                quality_indicators
            )

        # Log completion
        duration = (metrics.end_time - metrics.start_time).total_seconds()

        await self.audit_logger.log_system_event(
            event_type="collection_completed",
            process_id=process_id,
            component="collection_monitor",
            details={
                'duration_seconds': duration,
                'sources_found': metrics.sources_found,
                'unique_sources': len(metrics.unique_sources),
                'total_cost': metrics.total_cost,
                'quality_score': metrics.quality_score,
                'data_volume_mb': metrics.data_volume_bytes / (1024 * 1024)
            }
        )

        # Send completion notification
        await self._send_completion_notification(metrics)

        # Store final metrics
        await self._store_metrics_history(metrics)

        # Clean up active collection
        self.active_collections.pop(process_id, None)

        return metrics

    async def fail_collection(
        self,
        process_id: str,
        reason: str
    ) -> Optional[CollectionMetrics]:
        """
        Mark collection as failed.

        Args:
            process_id: Process ID
            reason: Failure reason

        Returns:
            Updated metrics or None

        Since:
            Version 1.0.0
        """
        metrics = self.active_collections.get(process_id)

        if not metrics:
            metrics = await self._load_from_cache(process_id)

        if not metrics:
            return None

        metrics.status = CollectionStatus.FAILED
        metrics.end_time = datetime.utcnow()
        metrics.errors.append(reason)

        # Log failure
        await self.audit_logger.log_error(
            "Collection failed",
            process_id=process_id,
            error=reason,
            drug_names=[]
        )

        # Send alert
        await self._send_alert(
            AlertSeverity.ERROR,
            f"Collection failed: {reason}",
            metrics
        )

        # Store for analysis
        await self._store_metrics_history(metrics)

        # Clean up
        self.active_collections.pop(process_id, None)

        return metrics

    def _calculate_quality_score(
        self,
        metrics: CollectionMetrics,
        indicators: QualityIndicators
    ) -> float:
        """
        Calculate overall quality score.

        Args:
            metrics: Collection metrics
            indicators: Quality indicators

        Returns:
            Quality score (0-1)

        Since:
            Version 1.0.0
        """
        scores = []

        # Source diversity score
        if indicators.source_diversity_score:
            scores.append(indicators.source_diversity_score)

        # High priority source percentage
        if indicators.high_priority_percentage:
            scores.append(indicators.high_priority_percentage)

        # Verification rate
        if indicators.verification_rate:
            scores.append(indicators.verification_rate)

        # Data freshness (newer is better)
        if indicators.data_freshness_hours < 24:
            freshness_score = 1.0
        elif indicators.data_freshness_hours < 168:  # 1 week
            freshness_score = 0.8
        else:
            freshness_score = 0.5
        scores.append(freshness_score)

        # Duplicate penalty
        duplicate_penalty = max(0, 1 - (indicators.duplicate_count / max(metrics.sources_found, 1)))
        scores.append(duplicate_penalty)

        return sum(scores) / len(scores) if scores else 0.0

    async def _check_alerts(self, metrics: CollectionMetrics):
        """
        Check for alert conditions.

        Args:
            metrics: Collection metrics

        Since:
            Version 1.0.0
        """
        # Check quality threshold
        if metrics.quality_score > 0 and metrics.quality_score < self.alert_thresholds['min_quality_score']:
            await self._send_alert(
                AlertSeverity.WARNING,
                f"Quality score below threshold: {metrics.quality_score:.2f}",
                metrics
            )

        # Check cost threshold
        if metrics.total_cost > self.alert_thresholds['max_cost_per_request']:
            await self._send_alert(
                AlertSeverity.WARNING,
                f"Cost exceeds threshold: ${metrics.total_cost:.2f}",
                metrics
            )

        # Check collection time
        duration = (datetime.utcnow() - metrics.start_time).total_seconds()
        if duration > self.alert_thresholds['max_collection_time_seconds']:
            await self._send_alert(
                AlertSeverity.WARNING,
                f"Collection time exceeds threshold: {duration:.0f}s",
                metrics
            )

        # Check minimum sources
        if metrics.sources_found < self.alert_thresholds['min_sources_required']:
            await self._send_alert(
                AlertSeverity.WARNING,
                f"Insufficient sources found: {metrics.sources_found}",
                metrics
            )

        # Check error rate
        if metrics.errors:
            error_rate = len(metrics.errors) / max(metrics.sources_found, 1)
            if error_rate > self.alert_thresholds['max_error_rate']:
                await self._send_alert(
                    AlertSeverity.ERROR,
                    f"High error rate: {error_rate:.2%}",
                    metrics
                )

    async def _send_alert(
        self,
        severity: AlertSeverity,
        message: str,
        metrics: CollectionMetrics
    ):
        """
        Send alert notification.

        Args:
            severity: Alert severity
            message: Alert message
            metrics: Collection metrics

        Since:
            Version 1.0.0
        """
        alert_data = {
            'severity': severity.value,
            'message': message,
            'process_id': metrics.process_id,
            'request_id': metrics.request_id,
            'category': metrics.category,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Log alert
        await self.audit_logger.log_system_event(
            event_type=f"collection_alert_{severity.value}",
            process_id=metrics.process_id,
            component="collection_monitor",
            details=alert_data
        )

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        # Store in Redis for dashboard
        if self.redis:
            await self.redis.lpush(
                f"alerts:{metrics.process_id}",
                json.dumps(alert_data)
            )

    async def _send_completion_notification(self, metrics: CollectionMetrics):
        """
        Send collection completion notification.

        Args:
            metrics: Collection metrics

        Since:
            Version 1.0.0
        """
        notification = {
            'event': 'collection_completed',
            'process_id': metrics.process_id,
            'request_id': metrics.request_id,
            'category': metrics.category,
            'sources_found': metrics.sources_found,
            'quality_score': metrics.quality_score,
            'total_cost': metrics.total_cost,
            'duration_seconds': (
                metrics.end_time - metrics.start_time
            ).total_seconds() if metrics.end_time else 0
        }

        # Log notification
        await self.audit_logger.log_system_event(
            event_type="collection_notification",
            process_id=metrics.process_id,
            component="collection_monitor",
            details=notification
        )

        # Publish to message queue if available
        # TODO: Integrate with message queue service

    async def _cache_metrics(self, metrics: CollectionMetrics):
        """
        Cache metrics in Redis.

        Args:
            metrics: Collection metrics

        Since:
            Version 1.0.0
        """
        if not self.redis:
            return

        import json

        key = f"collection_metrics:{metrics.process_id}"
        data = {
            'request_id': metrics.request_id,
            'process_id': metrics.process_id,
            'category': metrics.category,
            'status': metrics.status.value,
            'total_categories': metrics.total_categories,
            'completed_categories': metrics.completed_categories,
            'apis_queried': metrics.apis_queried,
            'sources_found': metrics.sources_found,
            'unique_sources': list(metrics.unique_sources),
            'data_volume_bytes': metrics.data_volume_bytes,
            'total_cost': metrics.total_cost,
            'quality_score': metrics.quality_score,
            'completion_percentage': metrics.completion_percentage,
            'start_time': metrics.start_time.isoformat(),
            'end_time': metrics.end_time.isoformat() if metrics.end_time else None,
            'errors': metrics.errors,
            'warnings': metrics.warnings
        }

        await self.redis.setex(
            key,
            3600,  # 1 hour TTL
            json.dumps(data)
        )

    async def _load_from_cache(
        self,
        process_id: str
    ) -> Optional[CollectionMetrics]:
        """
        Load metrics from cache.

        Args:
            process_id: Process ID

        Returns:
            Cached metrics or None

        Since:
            Version 1.0.0
        """
        if not self.redis:
            return None

        import json

        key = f"collection_metrics:{process_id}"
        data = await self.redis.get(key)

        if not data:
            return None

        try:
            data = json.loads(data)
            metrics = CollectionMetrics(
                request_id=data['request_id'],
                process_id=data['process_id'],
                category=data['category'],
                status=CollectionStatus(data['status']),
                total_categories=data['total_categories'],
                completed_categories=data['completed_categories'],
                apis_queried=data['apis_queried'],
                sources_found=data['sources_found'],
                unique_sources=set(data['unique_sources']),
                data_volume_bytes=data['data_volume_bytes'],
                total_cost=data['total_cost'],
                quality_score=data['quality_score'],
                completion_percentage=data['completion_percentage'],
                start_time=datetime.fromisoformat(data['start_time']),
                end_time=datetime.fromisoformat(data['end_time']) if data['end_time'] else None,
                errors=data['errors'],
                warnings=data['warnings']
            )
            return metrics

        except Exception as e:
            logger.error(f"Failed to load metrics from cache: {e}")
            return None

    async def _store_metrics_history(self, metrics: CollectionMetrics):
        """
        Store metrics in database for historical tracking.

        Args:
            metrics: Collection metrics

        Since:
            Version 1.0.0
        """
        if not self.db:
            return

        # TODO: Create metrics history table and store
        # For now, update process tracking metadata
        from sqlalchemy import update

        stmt = update(ProcessTracking).where(
            ProcessTracking.id == metrics.process_id
        ).values(
            metadata={
                'collection_metrics': {
                    'sources_found': metrics.sources_found,
                    'unique_sources': len(metrics.unique_sources),
                    'total_cost': metrics.total_cost,
                    'quality_score': metrics.quality_score,
                    'data_volume_mb': metrics.data_volume_bytes / (1024 * 1024),
                    'apis_queried': metrics.apis_queried,
                    'completion_percentage': metrics.completion_percentage,
                    'errors': metrics.errors[:10],  # Limit error storage
                    'warnings': metrics.warnings[:10]
                }
            }
        )

        await self.db.execute(stmt)
        await self.db.commit()

    def register_alert_callback(self, callback):
        """
        Register callback for alerts.

        Args:
            callback: Async callback function

        Since:
            Version 1.0.0
        """
        self.alert_callbacks.append(callback)

    async def get_active_collections(self) -> List[CollectionMetrics]:
        """
        Get all active collection metrics.

        Returns:
            List of active collection metrics

        Since:
            Version 1.0.0
        """
        return list(self.active_collections.values())

    async def get_collection_status(
        self,
        process_id: str
    ) -> Optional[CollectionMetrics]:
        """
        Get status of specific collection.

        Args:
            process_id: Process ID

        Returns:
            Collection metrics or None

        Since:
            Version 1.0.0
        """
        metrics = self.active_collections.get(process_id)

        if not metrics:
            metrics = await self._load_from_cache(process_id)

        return metrics