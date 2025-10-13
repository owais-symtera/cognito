"""
API routes for Epic 7: Administrative & Monitoring Interfaces
Provides RESTful endpoints for frontend consumption
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json

from ...core.admin import (
    AdminDashboardService,
    ProcessMonitoringService,
    FailureManagementService,
    ScoringConfigurationService
)
from ...utils.auth import get_current_user, require_role
from ...utils.database import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


# ============= Request/Response Models =============

class UserRole(BaseModel):
    id: str
    name: str
    permissions: List[str]
    description: Optional[str] = None


class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    roles: List[UserRole]
    organization_id: str
    is_active: bool = True
    theme_preference: str = "auto"  # auto, light, dark
    created_at: datetime
    last_login: Optional[datetime] = None


class CategoryConfig(BaseModel):
    id: str
    name: str
    display_name: str
    enabled: bool
    template: str
    parameters: Dict[str, Any]
    source_priority: List[str]
    validation_rules: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    updated_by: str


class APIConfig(BaseModel):
    id: str
    service_name: str
    api_key: str
    endpoint: str
    rate_limit: int
    cost_per_call: float
    monthly_quota: int
    used_this_month: int
    is_active: bool


class SystemHealth(BaseModel):
    status: str  # operational, degraded, down
    uptime_percentage: float
    active_processes: int
    queued_processes: int
    failed_processes: int
    avg_response_time_ms: float
    last_check: datetime


class ProcessStatus(BaseModel):
    request_id: str
    process_id: str
    category: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    current_stage: str
    started_at: datetime
    estimated_completion: Optional[datetime]
    error_message: Optional[str] = None


class ScoringParameter(BaseModel):
    id: str
    name: str
    display_name: str
    type: str  # numeric, categorical, boolean
    weight: float
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None


class ScoringRange(BaseModel):
    parameter_id: str
    delivery_method: str
    score: int
    min_value: Optional[float]
    max_value: Optional[float]
    label: str
    is_exclusion: bool = False


class PerformanceMetrics(BaseModel):
    period: str  # today, week, month
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_processing_time_ms: float
    success_rate: float
    peak_hour: int
    categories_processed: Dict[str, int]


class AlertConfig(BaseModel):
    id: str
    name: str
    type: str  # failure, performance, capacity
    condition: Dict[str, Any]
    severity: str  # low, medium, high, critical
    notification_channels: List[str]
    is_active: bool


class ApprovalWorkflow(BaseModel):
    id: str
    request_type: str
    requested_by: str
    requested_at: datetime
    changes: Dict[str, Any]
    status: str  # pending, approved, rejected
    approvers: List[str]
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None


# ============= Story 7.1: Administrative Configuration Interface =============

@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get administrative dashboard overview"""
    admin_service = AdminDashboardService(db)

    return {
        "system_health": await admin_service.get_system_health(),
        "active_processes": await admin_service.get_active_processes_summary(),
        "recent_activity": await admin_service.get_recent_activity(limit=10),
        "performance_summary": await admin_service.get_performance_summary(),
        "user_info": {
            "username": current_user.username,
            "roles": current_user.roles,
            "theme": current_user.theme_preference
        }
    }


@router.get("/categories", response_model=List[CategoryConfig])
async def get_categories(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all category configurations"""
    admin_service = AdminDashboardService(db)
    return await admin_service.get_categories(enabled_only)


@router.get("/categories/{category_id}", response_model=CategoryConfig)
async def get_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get specific category configuration"""
    admin_service = AdminDashboardService(db)
    category = await admin_service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/categories/{category_id}")
async def update_category(
    category_id: str,
    category: CategoryConfig,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Update category configuration (requires approval)"""
    admin_service = AdminDashboardService(db)

    # Create approval workflow
    workflow = await admin_service.create_approval_workflow(
        request_type="category_update",
        requested_by=current_user.id,
        changes={
            "category_id": category_id,
            "updates": category.dict()
        }
    )

    return {
        "message": "Update submitted for approval",
        "workflow_id": workflow.id,
        "status": workflow.status
    }


@router.get("/users", response_model=List[User])
async def get_users(
    organization_id: Optional[str] = None,
    role: Optional[str] = None,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Get users with optional filters"""
    admin_service = AdminDashboardService(db)
    return await admin_service.get_users(organization_id, role)


@router.post("/users")
async def create_user(
    user: User,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Create new user"""
    admin_service = AdminDashboardService(db)
    new_user = await admin_service.create_user(user)

    # Audit trail
    await admin_service.log_audit_trail(
        action="user_created",
        user_id=current_user.id,
        details={"new_user_id": new_user.id}
    )

    return new_user


@router.get("/apis", response_model=List[APIConfig])
async def get_api_configurations(
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Get all API configurations with usage stats"""
    admin_service = AdminDashboardService(db)
    return await admin_service.get_api_configurations()


@router.put("/apis/{api_id}")
async def update_api_configuration(
    api_id: str,
    config: APIConfig,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Update API configuration"""
    admin_service = AdminDashboardService(db)
    updated = await admin_service.update_api_configuration(api_id, config)

    # Audit trail
    await admin_service.log_audit_trail(
        action="api_config_updated",
        user_id=current_user.id,
        details={"api_id": api_id, "changes": config.dict()}
    )

    return updated


@router.post("/backup")
async def create_configuration_backup(
    description: str = Body(...),
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Create system configuration backup"""
    admin_service = AdminDashboardService(db)
    backup = await admin_service.create_backup(description, current_user.id)

    return {
        "backup_id": backup["id"],
        "created_at": backup["created_at"],
        "size_bytes": backup["size_bytes"],
        "description": description
    }


@router.post("/restore/{backup_id}")
async def restore_configuration(
    backup_id: str,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Restore system configuration from backup"""
    admin_service = AdminDashboardService(db)

    # Create approval workflow for restore
    workflow = await admin_service.create_approval_workflow(
        request_type="configuration_restore",
        requested_by=current_user.id,
        changes={"backup_id": backup_id}
    )

    return {
        "message": "Restore request submitted for approval",
        "workflow_id": workflow.id
    }


@router.get("/workflows", response_model=List[ApprovalWorkflow])
async def get_approval_workflows(
    status: Optional[str] = None,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Get approval workflows"""
    admin_service = AdminDashboardService(db)
    return await admin_service.get_workflows(status)


@router.post("/workflows/{workflow_id}/approve")
async def approve_workflow(
    workflow_id: str,
    comments: str = Body(None),
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Approve workflow request"""
    admin_service = AdminDashboardService(db)
    result = await admin_service.approve_workflow(
        workflow_id, current_user.id, comments
    )

    return result


# ============= Story 7.2: Real-time Process Monitoring Dashboard =============

@router.get("/monitoring/realtime", response_model=Dict[str, Any])
async def get_realtime_monitoring(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get real-time monitoring dashboard data"""
    monitoring_service = ProcessMonitoringService(db)

    return {
        "active_requests": await monitoring_service.get_active_requests(),
        "queue_status": await monitoring_service.get_queue_status(),
        "resource_utilization": await monitoring_service.get_resource_utilization(),
        "recent_alerts": await monitoring_service.get_recent_alerts(limit=5),
        "timestamp": datetime.utcnow()
    }


@router.get("/monitoring/processes", response_model=List[ProcessStatus])
async def get_processes(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get process list with filters"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_processes(status, category, limit)


@router.get("/monitoring/processes/{request_id}/timeline")
async def get_process_timeline(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get process timeline visualization data"""
    monitoring_service = ProcessMonitoringService(db)
    timeline = await monitoring_service.get_process_timeline(request_id)

    if not timeline:
        raise HTTPException(status_code=404, detail="Process not found")

    return timeline


@router.get("/monitoring/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period: str = Query("today", regex="^(today|week|month)$"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get performance metrics for specified period"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_performance_metrics(period)


@router.get("/monitoring/queue")
async def get_queue_monitoring(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get queue monitoring information"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_queue_details()


@router.get("/monitoring/resources")
async def get_resource_monitoring(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get resource utilization monitoring"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_resource_monitoring()


@router.get("/monitoring/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get system alerts"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_alerts(severity, limit)


@router.post("/monitoring/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    notes: str = Body(None),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Acknowledge an alert"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.acknowledge_alert(
        alert_id, current_user.id, notes
    )


@router.get("/monitoring/history")
async def get_historical_analysis(
    start_date: datetime,
    end_date: datetime,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get historical performance analysis"""
    monitoring_service = ProcessMonitoringService(db)
    return await monitoring_service.get_historical_analysis(
        start_date, end_date, category
    )


# ============= Story 7.3: Failure Management & Recovery Tools =============

@router.get("/failures", response_model=List[Dict[str, Any]])
async def get_failures(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get failure list with filters"""
    failure_service = FailureManagementService(db)
    return await failure_service.get_failures(status, severity, limit)


@router.get("/failures/{failure_id}")
async def get_failure_details(
    failure_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed failure information"""
    failure_service = FailureManagementService(db)
    details = await failure_service.get_failure_details(failure_id)

    if not details:
        raise HTTPException(status_code=404, detail="Failure record not found")

    return details


@router.post("/failures/{failure_id}/retry")
async def retry_failed_process(
    failure_id: str,
    override_params: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Retry a failed process"""
    failure_service = FailureManagementService(db)

    result = await failure_service.retry_process(
        failure_id, current_user.id, override_params
    )

    # Audit trail
    await failure_service.log_audit_trail(
        action="process_retry",
        user_id=current_user.id,
        details={
            "failure_id": failure_id,
            "new_request_id": result["new_request_id"]
        }
    )

    return result


@router.post("/failures/{failure_id}/manual-intervention")
async def request_manual_intervention(
    failure_id: str,
    intervention_type: str,
    notes: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Request manual intervention for failed process"""
    failure_service = FailureManagementService(db)

    ticket = await failure_service.create_intervention_ticket(
        failure_id, intervention_type, notes, current_user.id
    )

    return {
        "ticket_id": ticket["id"],
        "status": "created",
        "assigned_to": ticket["assigned_to"]
    }


@router.get("/dead-letter-queue", response_model=List[Dict[str, Any]])
async def get_dead_letter_queue(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Get dead letter queue items"""
    failure_service = FailureManagementService(db)
    return await failure_service.get_dead_letter_queue(limit)


@router.post("/dead-letter-queue/{item_id}/process")
async def process_dead_letter_item(
    item_id: str,
    action: str = Body(..., regex="^(retry|discard|archive)$"),
    notes: str = Body(None),
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Process dead letter queue item"""
    failure_service = FailureManagementService(db)

    result = await failure_service.process_dead_letter_item(
        item_id, action, current_user.id, notes
    )

    return result


@router.get("/recovery/templates", response_model=List[Dict[str, Any]])
async def get_recovery_templates(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get available recovery action templates"""
    failure_service = FailureManagementService(db)
    return await failure_service.get_recovery_templates()


@router.post("/recovery/execute")
async def execute_recovery_action(
    template_id: str,
    target_failures: List[str],
    parameters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Execute recovery action on multiple failures"""
    failure_service = FailureManagementService(db)

    results = await failure_service.execute_recovery_action(
        template_id, target_failures, parameters, current_user.id
    )

    return {
        "processed": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "details": results
    }


# ============= Story 7.4: Scoring Configuration Management UI =============

@router.get("/scoring/parameters", response_model=List[ScoringParameter])
async def get_scoring_parameters(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get scoring parameters"""
    scoring_service = ScoringConfigurationService(db)
    return await scoring_service.get_parameters(category)


@router.post("/scoring/parameters")
async def create_scoring_parameter(
    parameter: ScoringParameter,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Create new scoring parameter"""
    scoring_service = ScoringConfigurationService(db)

    new_param = await scoring_service.create_parameter(parameter)

    # Audit trail
    await scoring_service.log_audit_trail(
        action="scoring_parameter_created",
        user_id=current_user.id,
        details={"parameter_id": new_param.id}
    )

    return new_param


@router.put("/scoring/parameters/{parameter_id}")
async def update_scoring_parameter(
    parameter_id: str,
    parameter: ScoringParameter,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Update scoring parameter"""
    scoring_service = ScoringConfigurationService(db)

    # Create approval workflow for significant changes
    if parameter.weight != await scoring_service.get_parameter_weight(parameter_id):
        workflow = await scoring_service.create_approval_workflow(
            request_type="scoring_weight_change",
            requested_by=current_user.id,
            changes={
                "parameter_id": parameter_id,
                "new_weight": parameter.weight
            }
        )
        return {
            "message": "Weight change requires approval",
            "workflow_id": workflow.id
        }

    updated = await scoring_service.update_parameter(parameter_id, parameter)
    return updated


@router.get("/scoring/ranges", response_model=List[ScoringRange])
async def get_scoring_ranges(
    parameter_id: Optional[str] = None,
    delivery_method: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get scoring ranges"""
    scoring_service = ScoringConfigurationService(db)
    return await scoring_service.get_ranges(parameter_id, delivery_method)


@router.put("/scoring/ranges")
async def update_scoring_ranges(
    ranges: List[ScoringRange],
    current_user: User = Depends(require_role(["admin", "manager"])),
    db = Depends(get_db)
):
    """Update scoring ranges"""
    scoring_service = ScoringConfigurationService(db)

    updated = await scoring_service.update_ranges(ranges)

    # Audit trail
    await scoring_service.log_audit_trail(
        action="scoring_ranges_updated",
        user_id=current_user.id,
        details={"ranges_count": len(ranges)}
    )

    return {
        "updated": updated,
        "message": "Scoring ranges updated successfully"
    }


@router.post("/scoring/test")
async def test_scoring_calculation(
    parameters: Dict[str, float],
    delivery_method: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Test scoring calculation with given parameters"""
    scoring_service = ScoringConfigurationService(db)

    result = await scoring_service.calculate_test_score(
        parameters, delivery_method
    )

    return result


@router.post("/scoring/import")
async def import_scoring_configuration(
    file_content: str = Body(...),
    file_format: str = Body("csv", regex="^(csv|excel|json)$"),
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Import scoring configuration from file"""
    scoring_service = ScoringConfigurationService(db)

    result = await scoring_service.import_configuration(
        file_content, file_format, current_user.id
    )

    return result


@router.get("/scoring/export")
async def export_scoring_configuration(
    format: str = Query("csv", regex="^(csv|excel|json)$"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Export scoring configuration"""
    scoring_service = ScoringConfigurationService(db)

    export_data = await scoring_service.export_configuration(format)

    return {
        "format": format,
        "data": export_data,
        "timestamp": datetime.utcnow()
    }


@router.get("/scoring/history")
async def get_scoring_configuration_history(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get scoring configuration change history"""
    scoring_service = ScoringConfigurationService(db)
    return await scoring_service.get_configuration_history(limit)


@router.post("/scoring/rollback/{version_id}")
async def rollback_scoring_configuration(
    version_id: str,
    current_user: User = Depends(require_role(["admin"])),
    db = Depends(get_db)
):
    """Rollback to previous scoring configuration version"""
    scoring_service = ScoringConfigurationService(db)

    # Create approval workflow for rollback
    workflow = await scoring_service.create_approval_workflow(
        request_type="scoring_rollback",
        requested_by=current_user.id,
        changes={"version_id": version_id}
    )

    return {
        "message": "Rollback request submitted for approval",
        "workflow_id": workflow.id
    }


# ============= Common Endpoints =============

@router.get("/audit-trail")
async def get_audit_trail(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(["admin", "compliance"])),
    db = Depends(get_db)
):
    """Get audit trail records"""
    admin_service = AdminDashboardService(db)

    records = await admin_service.get_audit_trail(
        start_date, end_date, user_id, action, limit
    )

    return records


@router.post("/theme/preference")
async def update_theme_preference(
    theme: str = Body(..., regex="^(auto|light|dark)$"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update user's theme preference"""
    admin_service = AdminDashboardService(db)

    await admin_service.update_user_preference(
        current_user.id, {"theme": theme}
    )

    return {
        "message": "Theme preference updated",
        "theme": theme
    }


@router.ws("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await websocket.accept()
    monitoring_service = ProcessMonitoringService(get_db())

    try:
        while True:
            # Send updates every 5 seconds
            data = await monitoring_service.get_realtime_update()
            await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass