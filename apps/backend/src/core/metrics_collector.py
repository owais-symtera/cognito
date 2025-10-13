"""
Performance metrics collection for pharmaceutical platform monitoring.

Collects and aggregates system performance metrics for operational
monitoring and pharmaceutical compliance reporting.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..database.models import AnalysisRequest, ProcessTracking
from ..schemas.health import PerformanceMetrics, WorkerStatus

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Collects and aggregates system performance metrics.

    Since:
        Version 1.0.0
    """

    def __init__(self):
        """
        Initialize metrics collector.

        Since:
            Version 1.0.0
        """
        # Response time tracking (last 1000 requests)
        self.api_response_times = deque(maxlen=1000)
        self.db_query_times = deque(maxlen=1000)

        # Request tracking
        self.request_timestamps = deque(maxlen=1000)

        # Error tracking
        self.error_timestamps = deque(maxlen=100)

        # Cache hit tracking
        self.cache_hits = 0
        self.cache_misses = 0

    def record_api_response_time(self, response_time_ms: float):
        """
        Record API endpoint response time.

        Args:
            response_time_ms: Response time in milliseconds

        Since:
            Version 1.0.0
        """
        self.api_response_times.append(response_time_ms)
        self.request_timestamps.append(datetime.utcnow())

    def record_db_query_time(self, query_time_ms: float):
        """
        Record database query execution time.

        Args:
            query_time_ms: Query time in milliseconds

        Since:
            Version 1.0.0
        """
        self.db_query_times.append(query_time_ms)

    def record_error(self):
        """
        Record an error occurrence.

        Since:
            Version 1.0.0
        """
        self.error_timestamps.append(datetime.utcnow())

    def record_cache_hit(self):
        """
        Record a cache hit.

        Since:
            Version 1.0.0
        """
        self.cache_hits += 1

    def record_cache_miss(self):
        """
        Record a cache miss.

        Since:
            Version 1.0.0
        """
        self.cache_misses += 1

    def calculate_percentile(self, data: List[float], percentile: float) -> float:
        """
        Calculate percentile value from data.

        Args:
            data: List of values
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value

        Since:
            Version 1.0.0
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1

        return sorted_data[index]

    def get_requests_per_minute(self) -> float:
        """
        Calculate current requests per minute rate.

        Returns:
            Requests per minute

        Since:
            Version 1.0.0
        """
        if not self.request_timestamps:
            return 0.0

        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        recent_requests = sum(
            1 for ts in self.request_timestamps
            if ts > one_minute_ago
        )

        return float(recent_requests)

    def get_error_rate(self) -> float:
        """
        Calculate error rate percentage.

        Returns:
            Error rate as percentage

        Since:
            Version 1.0.0
        """
        if not self.request_timestamps:
            return 0.0

        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        recent_requests = sum(
            1 for ts in self.request_timestamps
            if ts > one_hour_ago
        )

        recent_errors = sum(
            1 for ts in self.error_timestamps
            if ts > one_hour_ago
        )

        if recent_requests == 0:
            return 0.0

        return (recent_errors / recent_requests) * 100

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate percentage.

        Returns:
            Cache hit rate as percentage

        Since:
            Version 1.0.0
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0

        return (self.cache_hits / total) * 100

    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get aggregated performance metrics.

        Returns:
            Performance metrics summary

        Since:
            Version 1.0.0
        """
        api_times = list(self.api_response_times)
        db_times = list(self.db_query_times)

        return PerformanceMetrics(
            avg_api_response_time_ms=sum(api_times) / len(api_times) if api_times else 0.0,
            p95_api_response_time_ms=self.calculate_percentile(api_times, 95),
            p99_api_response_time_ms=self.calculate_percentile(api_times, 99),
            avg_db_query_time_ms=sum(db_times) / len(db_times) if db_times else 0.0,
            requests_per_minute=self.get_requests_per_minute(),
            cache_hit_rate=self.get_cache_hit_rate(),
            error_rate=self.get_error_rate()
        )

    async def get_active_requests_count(self, db: AsyncSession) -> int:
        """
        Get count of currently active analysis requests.

        Args:
            db: Database session

        Returns:
            Active request count

        Since:
            Version 1.0.0
        """
        try:
            stmt = select(func.count()).select_from(AnalysisRequest).where(
                AnalysisRequest.status.in_(["pending", "processing"])
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Failed to get active request count", error=str(e))
            return 0

    async def get_processing_queue_depth(self, db: AsyncSession) -> int:
        """
        Get depth of processing queue.

        Args:
            db: Database session

        Returns:
            Queue depth

        Since:
            Version 1.0.0
        """
        try:
            stmt = select(func.count()).select_from(ProcessTracking).where(
                ProcessTracking.current_status == "submitted"
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Failed to get queue depth", error=str(e))
            return 0

    async def get_worker_metrics(self, db: AsyncSession) -> WorkerStatus:
        """
        Get worker processing metrics.

        Args:
            db: Database session

        Returns:
            Worker status metrics

        Since:
            Version 1.0.0
        """
        try:
            # Get today's completed tasks
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            completed_stmt = select(func.count()).select_from(ProcessTracking).where(
                and_(
                    ProcessTracking.current_status == "completed",
                    ProcessTracking.completed_at >= today_start
                )
            )
            completed_result = await db.execute(completed_stmt)
            tasks_completed = completed_result.scalar() or 0

            # Get today's failed tasks
            failed_stmt = select(func.count()).select_from(ProcessTracking).where(
                and_(
                    ProcessTracking.current_status == "failed",
                    ProcessTracking.failed_at >= today_start
                )
            )
            failed_result = await db.execute(failed_stmt)
            tasks_failed = failed_result.scalar() or 0

            # Get average processing time
            avg_time_stmt = select(
                func.avg(
                    func.extract(
                        'epoch',
                        ProcessTracking.completed_at - ProcessTracking.submitted_at
                    )
                )
            ).where(
                and_(
                    ProcessTracking.current_status == "completed",
                    ProcessTracking.completed_at.is_not(None)
                )
            )
            avg_result = await db.execute(avg_time_stmt)
            avg_seconds = avg_result.scalar() or 0
            avg_processing_time_ms = avg_seconds * 1000

            # Get queue depth
            queue_depth = await self.get_processing_queue_depth(db)

            return WorkerStatus(
                active_workers=4,  # TODO: Get from Celery or actual worker system
                idle_workers=0,
                queue_depth=queue_depth,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                average_processing_time_ms=avg_processing_time_ms
            )

        except Exception as e:
            logger.error("Failed to get worker metrics", error=str(e))
            return WorkerStatus(
                active_workers=0,
                idle_workers=0,
                queue_depth=0,
                tasks_completed=0,
                tasks_failed=0,
                average_processing_time_ms=0
            )


# Global metrics collector instance
metrics_collector = MetricsCollector()