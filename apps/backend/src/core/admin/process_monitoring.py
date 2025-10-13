"""
Epic 7, Story 7.2: Real-time Process Monitoring Dashboard
Provides comprehensive monitoring of pharmaceutical intelligence processing pipelines
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import time
from collections import defaultdict, deque

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ...database.session import get_session
from ...database.models import (
    ProcessingRequest, ProcessStage, ProcessLog, SystemMetric,
    Alert, QueueStatus, ResourceUsage, AuditLog, DocumentStatus,
    ChemicalAnalysis, PatentAnalysis, MarketAnalysis
)
from ...utils.notifications import NotificationService
from ...utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    """Process status definitions"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ProcessMetrics:
    """Real-time process metrics"""
    total_requests: int
    completed_requests: int
    failed_requests: int
    average_processing_time: float
    success_rate: float
    throughput_per_minute: float
    queue_depth: int
    active_workers: int
    error_rate: float
    retry_rate: float

@dataclass
class StageMetrics:
    """Metrics for individual processing stages"""
    stage_name: str
    total_processed: int
    average_time_seconds: float
    success_rate: float
    current_queue: int
    error_count: int
    last_error: Optional[str]

@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_throughput_mbps: float
    database_connections: int
    redis_memory_mb: float
    api_latency_ms: float

class ProcessMonitoringService:
    """Real-time process monitoring service"""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.metrics_collector = MetricsCollector()
        self.notification_service = NotificationService()
        self.websocket_connections: Set = set()
        self.monitoring_interval = 5  # seconds
        self.metrics_history = defaultdict(lambda: deque(maxlen=100))

    async def initialize(self):
        """Initialize monitoring service"""
        try:
            self.redis_client = await Redis.from_url(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Process monitoring service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring service: {e}")

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics"""
        async with get_session() as session:
            try:
                # Get overall process metrics
                process_metrics = await self._get_process_metrics(session)

                # Get stage-specific metrics
                stage_metrics = await self._get_stage_metrics(session)

                # Get resource utilization
                resource_metrics = await self._get_resource_metrics(session)

                # Get active alerts
                active_alerts = await self._get_active_alerts(session)

                # Get queue status
                queue_status = await self._get_queue_status(session)

                # Get recent failures
                recent_failures = await self._get_recent_failures(session)

                # Get performance trends
                performance_trends = await self._get_performance_trends(session)

                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "process_metrics": asdict(process_metrics),
                    "stage_metrics": [asdict(m) for m in stage_metrics],
                    "resource_metrics": asdict(resource_metrics),
                    "active_alerts": active_alerts,
                    "queue_status": queue_status,
                    "recent_failures": recent_failures,
                    "performance_trends": performance_trends
                }

            except Exception as e:
                logger.error(f"Failed to get dashboard metrics: {e}")
                raise

    async def _get_process_metrics(self, session: AsyncSession) -> ProcessMetrics:
        """Calculate overall process metrics"""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # Get request counts
        total = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(ProcessingRequest.created_at >= one_hour_ago)
        )

        completed = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(and_(
                ProcessingRequest.created_at >= one_hour_ago,
                ProcessingRequest.status == "completed"
            ))
        )

        failed = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(and_(
                ProcessingRequest.created_at >= one_hour_ago,
                ProcessingRequest.status == "failed"
            ))
        )

        # Get average processing time
        avg_time = await session.scalar(
            select(func.avg(ProcessingRequest.processing_time_seconds))
            .where(and_(
                ProcessingRequest.created_at >= one_hour_ago,
                ProcessingRequest.status == "completed"
            ))
        ) or 0

        # Get queue depth
        queue_depth = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(ProcessingRequest.status.in_(["queued", "processing"]))
        ) or 0

        # Get active workers from Redis
        active_workers = 0
        if self.redis_client:
            active_workers = len(await self.redis_client.keys("worker:*"))

        # Calculate rates
        success_rate = (completed / total * 100) if total > 0 else 0
        error_rate = (failed / total * 100) if total > 0 else 0
        throughput = (completed / 60) if completed > 0 else 0

        # Get retry rate
        retried = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(and_(
                ProcessingRequest.created_at >= one_hour_ago,
                ProcessingRequest.retry_count > 0
            ))
        ) or 0
        retry_rate = (retried / total * 100) if total > 0 else 0

        return ProcessMetrics(
            total_requests=total or 0,
            completed_requests=completed or 0,
            failed_requests=failed or 0,
            average_processing_time=avg_time,
            success_rate=success_rate,
            throughput_per_minute=throughput,
            queue_depth=queue_depth,
            active_workers=active_workers,
            error_rate=error_rate,
            retry_rate=retry_rate
        )

    async def _get_stage_metrics(self, session: AsyncSession) -> List[StageMetrics]:
        """Get metrics for individual processing stages"""
        stages = [
            "document_ingestion",
            "chemical_extraction",
            "patent_analysis",
            "market_intelligence",
            "decision_generation",
            "report_generation"
        ]

        metrics = []
        for stage_name in stages:
            # Get stage statistics
            result = await session.execute(
                select(
                    func.count(ProcessStage.id).label('total'),
                    func.avg(ProcessStage.duration_seconds).label('avg_time'),
                    func.sum(func.cast(ProcessStage.status == 'completed', type_=int)).label('completed'),
                    func.sum(func.cast(ProcessStage.status == 'failed', type_=int)).label('failed')
                )
                .where(ProcessStage.stage_name == stage_name)
            )
            row = result.first()

            if row and row.total > 0:
                # Get last error
                last_error = await session.scalar(
                    select(ProcessLog.error_message)
                    .where(and_(
                        ProcessLog.stage_name == stage_name,
                        ProcessLog.log_level == "ERROR"
                    ))
                    .order_by(desc(ProcessLog.created_at))
                    .limit(1)
                )

                # Get current queue from Redis
                queue_size = 0
                if self.redis_client:
                    queue_size = await self.redis_client.llen(f"queue:{stage_name}")

                metrics.append(StageMetrics(
                    stage_name=stage_name,
                    total_processed=row.total,
                    average_time_seconds=row.avg_time or 0,
                    success_rate=(row.completed / row.total * 100) if row.total > 0 else 0,
                    current_queue=queue_size,
                    error_count=row.failed or 0,
                    last_error=last_error
                ))

        return metrics

    async def _get_resource_metrics(self, session: AsyncSession) -> ResourceMetrics:
        """Get system resource metrics"""
        # Get latest resource metrics
        result = await session.execute(
            select(ResourceUsage)
            .order_by(desc(ResourceUsage.recorded_at))
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if latest:
            return ResourceMetrics(
                cpu_percent=latest.cpu_percent,
                memory_percent=latest.memory_percent,
                disk_percent=latest.disk_percent,
                network_throughput_mbps=latest.network_throughput_mbps,
                database_connections=latest.database_connections,
                redis_memory_mb=latest.redis_memory_mb,
                api_latency_ms=latest.api_latency_ms
            )
        else:
            # Return default metrics if none recorded
            return ResourceMetrics(
                cpu_percent=0,
                memory_percent=0,
                disk_percent=0,
                network_throughput_mbps=0,
                database_connections=0,
                redis_memory_mb=0,
                api_latency_ms=0
            )

    async def _get_active_alerts(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        result = await session.execute(
            select(Alert)
            .where(Alert.resolved_at.is_(None))
            .order_by(desc(Alert.created_at))
            .limit(20)
        )

        alerts = []
        for alert in result.scalars():
            alerts.append({
                "id": alert.id,
                "severity": alert.severity,
                "category": alert.category,
                "message": alert.message,
                "source": alert.source,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            })

        return alerts

    async def _get_queue_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get queue status for all stages"""
        result = await session.execute(
            select(
                QueueStatus.queue_name,
                QueueStatus.pending_count,
                QueueStatus.processing_count,
                QueueStatus.failed_count,
                QueueStatus.average_wait_time_seconds
            )
            .order_by(QueueStatus.queue_name)
        )

        queue_status = {}
        for row in result:
            queue_status[row.queue_name] = {
                "pending": row.pending_count,
                "processing": row.processing_count,
                "failed": row.failed_count,
                "avg_wait_time": row.average_wait_time_seconds
            }

        return queue_status

    async def _get_recent_failures(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get recent processing failures"""
        result = await session.execute(
            select(ProcessingRequest)
            .where(ProcessingRequest.status == "failed")
            .order_by(desc(ProcessingRequest.updated_at))
            .limit(10)
        )

        failures = []
        for req in result.scalars():
            failures.append({
                "id": req.id,
                "request_type": req.request_type,
                "error_message": req.error_message,
                "failed_at": req.updated_at.isoformat(),
                "retry_count": req.retry_count,
                "stage_failed": req.last_stage
            })

        return failures

    async def _get_performance_trends(self, session: AsyncSession) -> Dict[str, Any]:
        """Get performance trend data"""
        now = datetime.utcnow()

        # Get hourly metrics for last 24 hours
        hourly_data = []
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)

            result = await session.execute(
                select(
                    func.count(ProcessingRequest.id).label('count'),
                    func.avg(ProcessingRequest.processing_time_seconds).label('avg_time')
                )
                .where(and_(
                    ProcessingRequest.created_at >= hour_start,
                    ProcessingRequest.created_at < hour_end,
                    ProcessingRequest.status == "completed"
                ))
            )
            row = result.first()

            hourly_data.append({
                "hour": hour_start.isoformat(),
                "completed": row.count or 0,
                "avg_time": row.avg_time or 0
            })

        return {
            "hourly": hourly_data,
            "peak_hour": max(hourly_data, key=lambda x: x['completed'])['hour'] if hourly_data else None,
            "total_24h": sum(h['completed'] for h in hourly_data)
        }

    async def monitor_process(self, request_id: str) -> Dict[str, Any]:
        """Monitor specific process in real-time"""
        async with get_session() as session:
            # Get request details
            result = await session.execute(
                select(ProcessingRequest)
                .where(ProcessingRequest.id == request_id)
            )
            request = result.scalar_one_or_none()

            if not request:
                raise ValueError(f"Request {request_id} not found")

            # Get stage progress
            stages_result = await session.execute(
                select(ProcessStage)
                .where(ProcessStage.request_id == request_id)
                .order_by(ProcessStage.started_at)
            )

            stages = []
            for stage in stages_result.scalars():
                stages.append({
                    "name": stage.stage_name,
                    "status": stage.status,
                    "started_at": stage.started_at.isoformat() if stage.started_at else None,
                    "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
                    "duration": stage.duration_seconds,
                    "error": stage.error_message
                })

            # Get process logs
            logs_result = await session.execute(
                select(ProcessLog)
                .where(ProcessLog.request_id == request_id)
                .order_by(desc(ProcessLog.created_at))
                .limit(50)
            )

            logs = []
            for log in logs_result.scalars():
                logs.append({
                    "timestamp": log.created_at.isoformat(),
                    "level": log.log_level,
                    "stage": log.stage_name,
                    "message": log.message,
                    "details": log.details
                })

            return {
                "request": {
                    "id": request.id,
                    "type": request.request_type,
                    "status": request.status,
                    "created_at": request.created_at.isoformat(),
                    "updated_at": request.updated_at.isoformat(),
                    "processing_time": request.processing_time_seconds,
                    "retry_count": request.retry_count,
                    "priority": request.priority
                },
                "stages": stages,
                "logs": logs,
                "current_stage": request.last_stage,
                "completion_percentage": len([s for s in stages if s['status'] == 'completed']) / 6 * 100
            }

    async def create_alert(
        self,
        severity: AlertSeverity,
        category: str,
        message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create system alert"""
        async with get_session() as session:
            alert = Alert(
                severity=severity.value,
                category=category,
                message=message,
                source=source,
                metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            session.add(alert)
            await session.commit()

            # Send notification for critical alerts
            if severity == AlertSeverity.CRITICAL:
                await self.notification_service.send_critical_alert(
                    category=category,
                    message=message,
                    metadata=metadata
                )

            # Broadcast to WebSocket connections
            await self._broadcast_alert(alert)

            # Log audit trail
            await self._log_audit(
                action="ALERT_CREATED",
                details={
                    "alert_id": alert.id,
                    "severity": severity.value,
                    "category": category,
                    "message": message
                },
                source=source
            )

            return alert.id

    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution: str):
        """Resolve an alert"""
        async with get_session() as session:
            result = await session.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = result.scalar_one_or_none()

            if not alert:
                raise ValueError(f"Alert {alert_id} not found")

            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = resolved_by
            alert.resolution = resolution

            await session.commit()

            # Log audit trail
            await self._log_audit(
                action="ALERT_RESOLVED",
                details={
                    "alert_id": alert_id,
                    "resolved_by": resolved_by,
                    "resolution": resolution
                },
                source=resolved_by
            )

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        async with get_session() as session:
            # Check critical metrics
            process_metrics = await self._get_process_metrics(session)
            resource_metrics = await self._get_resource_metrics(session)
            active_alerts = await self._get_active_alerts(session)

            # Calculate health score (0-100)
            health_score = 100
            issues = []

            # Check process metrics
            if process_metrics.error_rate > 10:
                health_score -= 20
                issues.append("High error rate")

            if process_metrics.queue_depth > 1000:
                health_score -= 15
                issues.append("Large queue backlog")

            if process_metrics.throughput_per_minute < 1:
                health_score -= 10
                issues.append("Low throughput")

            # Check resource metrics
            if resource_metrics.cpu_percent > 80:
                health_score -= 15
                issues.append("High CPU usage")

            if resource_metrics.memory_percent > 85:
                health_score -= 15
                issues.append("High memory usage")

            if resource_metrics.api_latency_ms > 1000:
                health_score -= 10
                issues.append("High API latency")

            # Check alerts
            critical_alerts = len([a for a in active_alerts if a['severity'] == 'critical'])
            if critical_alerts > 0:
                health_score -= (critical_alerts * 10)
                issues.append(f"{critical_alerts} critical alerts")

            # Determine status
            if health_score >= 90:
                status = "healthy"
            elif health_score >= 70:
                status = "degraded"
            elif health_score >= 50:
                status = "impaired"
            else:
                status = "critical"

            return {
                "status": status,
                "health_score": max(0, health_score),
                "issues": issues,
                "metrics": {
                    "error_rate": process_metrics.error_rate,
                    "throughput": process_metrics.throughput_per_minute,
                    "cpu_usage": resource_metrics.cpu_percent,
                    "memory_usage": resource_metrics.memory_percent,
                    "active_alerts": len(active_alerts)
                },
                "last_check": datetime.utcnow().isoformat()
            }

    async def start_monitoring_loop(self):
        """Start background monitoring loop"""
        while True:
            try:
                # Collect metrics
                metrics = await self.get_dashboard_metrics()

                # Store in history
                self.metrics_history['process'].append(metrics['process_metrics'])
                self.metrics_history['resource'].append(metrics['resource_metrics'])

                # Check for anomalies
                await self._check_anomalies(metrics)

                # Broadcast to WebSocket connections
                await self._broadcast_metrics(metrics)

                # Sleep until next interval
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _check_anomalies(self, metrics: Dict[str, Any]):
        """Check for system anomalies"""
        process_metrics = metrics['process_metrics']
        resource_metrics = metrics['resource_metrics']

        # Check for sudden spike in errors
        if process_metrics['error_rate'] > 25:
            await self.create_alert(
                AlertSeverity.CRITICAL,
                "PROCESS",
                f"High error rate detected: {process_metrics['error_rate']:.1f}%",
                "monitoring_service"
            )

        # Check for resource exhaustion
        if resource_metrics['memory_percent'] > 90:
            await self.create_alert(
                AlertSeverity.WARNING,
                "RESOURCE",
                f"Memory usage critical: {resource_metrics['memory_percent']:.1f}%",
                "monitoring_service"
            )

        # Check for queue buildup
        if process_metrics['queue_depth'] > 5000:
            await self.create_alert(
                AlertSeverity.WARNING,
                "QUEUE",
                f"Large queue backlog: {process_metrics['queue_depth']} items",
                "monitoring_service"
            )

    async def _broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics to WebSocket connections"""
        if self.websocket_connections:
            message = json.dumps({
                "type": "metrics_update",
                "data": metrics
            })

            # Send to all connected clients
            disconnected = set()
            for ws in self.websocket_connections:
                try:
                    await ws.send_text(message)
                except:
                    disconnected.add(ws)

            # Remove disconnected clients
            self.websocket_connections -= disconnected

    async def _broadcast_alert(self, alert: Alert):
        """Broadcast alert to WebSocket connections"""
        if self.websocket_connections:
            message = json.dumps({
                "type": "alert",
                "data": {
                    "id": alert.id,
                    "severity": alert.severity,
                    "category": alert.category,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat()
                }
            })

            # Send to all connected clients
            for ws in self.websocket_connections:
                try:
                    await ws.send_text(message)
                except:
                    pass

    async def _log_audit(self, action: str, details: Dict[str, Any], source: str):
        """Log audit trail for monitoring actions"""
        async with get_session() as session:
            audit = AuditLog(
                action=action,
                source=source,
                details=details,
                created_at=datetime.utcnow()
            )
            session.add(audit)
            await session.commit()

    async def register_websocket(self, websocket):
        """Register WebSocket connection for real-time updates"""
        self.websocket_connections.add(websocket)

    async def unregister_websocket(self, websocket):
        """Unregister WebSocket connection"""
        self.websocket_connections.discard(websocket)