"""
Health monitoring schemas for pharmaceutical system diagnostics.

Defines request/response schemas for health checks, diagnostics,
and system monitoring with pharmaceutical compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class HealthStatus(str, Enum):
    """
    Health status values for components.

    Since:
        Version 1.0.0
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthResponse(BaseModel):
    """
    Basic health check response.

    Since:
        Version 1.0.0
    """
    status: HealthStatus = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    service: str = Field(default="cognito-ai-engine", description="Service name")


class DependencyHealth(BaseModel):
    """
    Individual dependency health status.

    Since:
        Version 1.0.0
    """
    name: str = Field(..., description="Dependency name")
    status: HealthStatus = Field(..., description="Dependency status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Last health check timestamp")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class DetailedHealthResponse(BaseModel):
    """
    Comprehensive health check response.

    Since:
        Version 1.0.0
    """
    status: HealthStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    dependencies: List[DependencyHealth] = Field(..., description="Dependency health checks")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    checks_passed: int = Field(..., description="Number of health checks passed")
    checks_failed: int = Field(..., description="Number of health checks failed")


class ConnectionPoolStatus(BaseModel):
    """
    Database connection pool status.

    Since:
        Version 1.0.0
    """
    active: int = Field(..., description="Active connections")
    idle: int = Field(..., description="Idle connections")
    total_capacity: int = Field(..., description="Total pool capacity")
    utilization_percentage: float = Field(..., description="Pool utilization percentage")
    wait_queue: int = Field(0, description="Connections waiting in queue")


class RedisStatus(BaseModel):
    """
    Redis cache status.

    Since:
        Version 1.0.0
    """
    connected: bool = Field(..., description="Redis connection status")
    used_memory_mb: float = Field(..., description="Used memory in MB")
    max_memory_mb: float = Field(..., description="Max memory in MB")
    keys_count: int = Field(..., description="Total number of keys")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    response_time_ms: float = Field(..., description="Average response time")


class WorkerStatus(BaseModel):
    """
    Background worker status.

    Since:
        Version 1.0.0
    """
    active_workers: int = Field(..., description="Active worker count")
    idle_workers: int = Field(..., description="Idle worker count")
    queue_depth: int = Field(..., description="Tasks in queue")
    tasks_completed: int = Field(..., description="Tasks completed today")
    tasks_failed: int = Field(..., description="Tasks failed today")
    average_processing_time_ms: float = Field(..., description="Average task processing time")


class MemoryUsage(BaseModel):
    """
    System memory usage.

    Since:
        Version 1.0.0
    """
    used_mb: float = Field(..., description="Used memory in MB")
    available_mb: float = Field(..., description="Available memory in MB")
    total_mb: float = Field(..., description="Total memory in MB")
    percentage_used: float = Field(..., description="Memory usage percentage")
    process_mb: float = Field(..., description="Process memory usage in MB")


class PerformanceMetrics(BaseModel):
    """
    System performance metrics.

    Since:
        Version 1.0.0
    """
    avg_api_response_time_ms: float = Field(..., description="Average API response time")
    p95_api_response_time_ms: float = Field(..., description="95th percentile API response time")
    p99_api_response_time_ms: float = Field(..., description="99th percentile API response time")
    avg_db_query_time_ms: float = Field(..., description="Average database query time")
    requests_per_minute: float = Field(..., description="Current requests per minute")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    error_rate: float = Field(..., description="Error rate percentage")


class SystemDiagnosticsResponse(BaseModel):
    """
    Comprehensive system diagnostics response.

    Since:
        Version 1.0.0
    """
    timestamp: datetime = Field(..., description="Diagnostics timestamp")
    active_requests: int = Field(..., description="Currently active requests")
    processing_queue_depth: int = Field(..., description="Processing queue depth")
    database_connections: ConnectionPoolStatus = Field(..., description="Database connection pool status")
    redis_status: RedisStatus = Field(..., description="Redis cache status")
    worker_status: WorkerStatus = Field(..., description="Background worker status")
    memory_usage: MemoryUsage = Field(..., description="Memory usage statistics")
    performance_metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    system_alerts: List[str] = Field(default_factory=list, description="Active system alerts")


class APIProviderHealth(BaseModel):
    """
    External API provider health status.

    Since:
        Version 1.0.0
    """
    provider: str = Field(..., description="API provider name")
    status: HealthStatus = Field(..., description="Provider health status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    last_successful_call: Optional[datetime] = Field(None, description="Last successful API call")
    error_count: int = Field(0, description="Error count in last hour")
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining rate limit")


class AlertConfiguration(BaseModel):
    """
    Alert configuration for monitoring.

    Since:
        Version 1.0.0
    """
    alert_type: str = Field(..., description="Type of alert")
    threshold: float = Field(..., description="Alert threshold value")
    duration_seconds: int = Field(..., description="Duration before triggering")
    enabled: bool = Field(True, description="Whether alert is enabled")
    notification_channels: List[str] = Field(..., description="Notification channels")


class SystemAlert(BaseModel):
    """
    Active system alert.

    Since:
        Version 1.0.0
    """
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(..., description="When alert was triggered")
    component: str = Field(..., description="Affected component")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional alert metadata")