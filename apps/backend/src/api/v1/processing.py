"""
Processing status API endpoints.
Provides real-time processing status and metrics from database.
Uses actual drug_requests data from the database.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, cast, String, text
import structlog

from ...database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/processing", tags=["processing"])


class ProcessingJob(BaseModel):
    id: str
    requestId: str
    drugName: str
    analysisType: str
    status: str
    priority: str
    progress: int
    currentStep: str
    totalSteps: int
    completedSteps: int
    startedAt: str
    estimatedCompletion: str
    actualCompletion: Optional[str] = None
    assignedWorker: str
    cpuUsage: int
    memoryUsage: int
    requesterName: str
    department: str
    errorMessage: Optional[str] = None
    warnings: List[str] = []
    artifacts: List[dict] = []


class SystemMetrics(BaseModel):
    totalJobs: int
    activeJobs: int
    queuedJobs: int
    completedToday: int
    failedToday: int
    avgProcessingTime: float
    systemLoad: int
    availableWorkers: int
    busyWorkers: int
    throughputPerHour: int


# Status mapping from database to API
STATUS_MAP = {
    'pending': 'queued',
    'processing': 'processing',
    'completed': 'completed',
    'failed': 'failed',
    'cancelled': 'cancelled'
}

# Step names based on progress
def get_current_step(progress: int, status: str) -> str:
    """Get current processing step based on progress."""
    if status == 'completed':
        return 'Completed'
    elif status == 'failed':
        return 'Failed'
    elif status == 'cancelled':
        return 'Cancelled'
    elif progress == 0:
        return 'Initializing'
    elif progress < 25:
        return 'Data Collection'
    elif progress < 50:
        return 'Source Verification'
    elif progress < 75:
        return 'Data Merging'
    elif progress < 100:
        return 'Summary Generation'
    else:
        return 'Finalizing'


def calculate_priority(status: str, progress: int, started_at: datetime) -> str:
    """Calculate job priority based on status and age."""
    if status == 'failed':
        return 'urgent'

    time_running = datetime.now(timezone.utc) - started_at
    if progress < 30 and time_running > timedelta(hours=1):
        return 'high'
    elif time_running > timedelta(hours=2):
        return 'high'
    elif progress > 70:
        return 'medium'
    else:
        return 'low'


def generate_worker_id(request_id: str) -> str:
    """Generate consistent worker ID from request ID."""
    worker_num = (hash(request_id) % 8) + 1
    return f"worker-{worker_num:02d}"


def calculate_resource_usage(status: str, progress: int) -> tuple[int, int]:
    """Calculate CPU and memory usage based on status and progress."""
    if status in ['completed', 'failed', 'cancelled']:
        return 20, 30
    elif status == 'pending':
        return 10, 20
    else:
        # Active processing
        base_cpu = 60 + (progress % 30)
        base_mem = 50 + (progress % 35)
        return min(95, base_cpu), min(85, base_mem)


def calculate_progress(total_categories: int, completed_categories: int, status: str) -> int:
    """Calculate progress percentage."""
    if status == 'completed':
        return 100
    elif status == 'pending':
        return 0
    elif total_categories > 0:
        return int((completed_categories / total_categories) * 100)
    else:
        return 0


async def map_to_processing_job(row, user_name: Optional[str] = None) -> ProcessingJob:
    """Map database row to ProcessingJob model."""
    # Extract fields from drug_requests table
    request_id = str(row.id)
    drug_name = row.drug_name or "Unknown Drug"
    status = str(row.status) if row.status else 'pending'
    started_at = row.created_at or datetime.now(timezone.utc)
    # Ensure timezone awareness
    if started_at and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    estimated_completion = row.estimated_completion
    actual_completion = row.completed_at
    total_categories = row.total_categories or 0
    completed_categories = row.completed_categories or 0

    # Map status
    mapped_status = STATUS_MAP.get(status, 'queued')

    # Calculate derived fields
    progress = calculate_progress(total_categories, completed_categories, status)
    current_step = get_current_step(progress, status)
    priority = calculate_priority(status, progress, started_at)
    assigned_worker = generate_worker_id(request_id)
    cpu_usage, memory_usage = calculate_resource_usage(status, progress)

    # Get requester info
    requester_name = user_name or "Unknown User"
    department = "Research"  # Default department

    # Analysis type (can be extended from metadata)
    analysis_type = "full_analysis"
    if hasattr(row, 'request_metadata') and row.request_metadata:
        analysis_type = row.request_metadata.get('analysis_type', 'full_analysis')

    # Warnings
    warnings = []
    if progress < 20 and (datetime.now(timezone.utc) - started_at) > timedelta(minutes=30):
        warnings.append("Processing is slower than expected")
    if status == 'failed':
        warnings.append("Processing failed - check error message")

    # Artifacts (can be populated from actual generated files)
    artifacts = []
    if status == 'completed':
        artifacts.append({
            "name": f"{drug_name}_analysis_report.pdf",
            "type": "pdf",
            "size": 2048,
            "generatedAt": actual_completion.isoformat() if actual_completion else datetime.now(timezone.utc).isoformat()
        })

    # Error message
    error_message = None
    if status == 'failed' and hasattr(row, 'error_message'):
        error_message = row.error_message

    return ProcessingJob(
        id=request_id,
        requestId=request_id,
        drugName=drug_name,
        analysisType=analysis_type,
        status=mapped_status,
        priority=priority,
        progress=progress,
        currentStep=current_step,
        totalSteps=total_categories or 4,
        completedSteps=completed_categories or 0,
        startedAt=started_at.isoformat(),
        estimatedCompletion=estimated_completion.isoformat() if estimated_completion else (started_at + timedelta(minutes=30)).isoformat(),
        actualCompletion=actual_completion.isoformat() if actual_completion else None,
        assignedWorker=assigned_worker,
        cpuUsage=cpu_usage,
        memoryUsage=memory_usage,
        requesterName=requester_name,
        department=department,
        errorMessage=error_message,
        warnings=warnings,
        artifacts=artifacts
    )


@router.get("/jobs", response_model=List[ProcessingJob])
async def get_processing_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all processing jobs with optional filters from database."""
    try:
        # Use raw SQL to avoid model relationship errors
        query_text = """
            SELECT
                dr.id,
                dr.drug_name,
                dr.status::text as status,
                dr.created_at,
                dr.completed_at,
                dr.estimated_completion,
                dr.total_categories,
                dr.completed_categories,
                dr.request_metadata,
                dr.user_id,
                u.full_name as user_name
            FROM drug_requests dr
            LEFT JOIN users u ON dr.user_id = u.id
            {}
            ORDER BY dr.created_at DESC
            LIMIT 50
        """

        # Apply status filter if provided
        where_clause = ""
        params = {}
        if status:
            # Reverse map from API status to DB status
            db_status = next((k for k, v in STATUS_MAP.items() if v == status), status)
            where_clause = "WHERE dr.status::text = :status"
            params['status'] = db_status

        final_query = query_text.format(where_clause)
        result = await db.execute(text(final_query), params)
        rows = result.all()

        # Convert to ProcessingJob models
        jobs = []
        for row in rows:
            job = await map_to_processing_job(row, row.user_name)

            # Apply priority filter if provided
            if priority and job.priority != priority:
                continue

            jobs.append(job)

        logger.info(f"Retrieved {len(jobs)} processing jobs from database")
        return jobs

    except Exception as e:
        logger.error(f"Error fetching processing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch processing jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
async def get_processing_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get specific processing job details from database."""
    try:
        # Use raw SQL to avoid model relationship errors
        query_text = """
            SELECT
                dr.id,
                dr.drug_name,
                dr.status::text as status,
                dr.created_at,
                dr.completed_at,
                dr.estimated_completion,
                dr.total_categories,
                dr.completed_categories,
                dr.request_metadata,
                dr.user_id,
                u.full_name as user_name
            FROM drug_requests dr
            LEFT JOIN users u ON dr.user_id = u.id
            WHERE dr.id = :job_id
        """

        result = await db.execute(text(query_text), {'job_id': job_id})
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")

        job = await map_to_processing_job(row, row.user_name)
        logger.info(f"Retrieved processing job {job_id} from database")
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching processing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch processing job: {str(e)}")


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db_session)
):
    """Get current system processing metrics from database."""
    try:
        # Use raw SQL to avoid model relationship errors
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Count total jobs
        total_result = await db.execute(text("SELECT COUNT(*) FROM drug_requests"))
        total_jobs = total_result.scalar() or 0

        # Count active jobs (processing)
        active_result = await db.execute(text("SELECT COUNT(*) FROM drug_requests WHERE status::text = 'processing'"))
        active_jobs = active_result.scalar() or 0

        # Count queued jobs (pending)
        queued_result = await db.execute(text("SELECT COUNT(*) FROM drug_requests WHERE status::text = 'pending'"))
        queued_jobs = queued_result.scalar() or 0

        # Count completed today
        completed_result = await db.execute(text(
            "SELECT COUNT(*) FROM drug_requests WHERE status::text = 'completed' AND completed_at >= :today"
        ), {'today': today_start})
        completed_today = completed_result.scalar() or 0

        # Count failed today
        failed_result = await db.execute(text(
            "SELECT COUNT(*) FROM drug_requests WHERE status::text = 'failed' AND created_at >= :today"
        ), {'today': today_start})
        failed_today = failed_result.scalar() or 0

        # Calculate average processing time (in minutes)
        avg_result = await db.execute(text(
            "SELECT AVG(actual_processing_time) FROM drug_requests WHERE status::text = 'completed' AND actual_processing_time IS NOT NULL"
        ))
        avg_time = avg_result.scalar() or 0.0
        # Convert seconds to minutes if needed
        avg_time_minutes = avg_time / 60 if avg_time > 0 else 0.0

        # Calculate system load
        max_concurrent = 10
        system_load = min(100, int((active_jobs / max_concurrent) * 100)) if max_concurrent > 0 else 0

        # Calculate throughput (completed in last hour)
        throughput_result = await db.execute(text(
            "SELECT COUNT(*) FROM drug_requests WHERE status::text = 'completed' AND completed_at >= :one_hour_ago"
        ), {'one_hour_ago': one_hour_ago})
        throughput = throughput_result.scalar() or 0

        metrics = SystemMetrics(
            totalJobs=total_jobs,
            activeJobs=active_jobs,
            queuedJobs=queued_jobs,
            completedToday=completed_today,
            failedToday=failed_today,
            avgProcessingTime=round(avg_time_minutes, 2),
            systemLoad=system_load,
            availableWorkers=max(0, max_concurrent - active_jobs),
            busyWorkers=active_jobs,
            throughputPerHour=throughput
        )

        logger.info(f"Retrieved system metrics from database")
        return metrics

    except Exception as e:
        logger.error(f"Error fetching system metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch system metrics: {str(e)}")


@router.post("/jobs/{job_id}/{action}")
async def control_job(
    job_id: str,
    action: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Control a processing job (pause, resume, cancel) - updates database."""
    try:
        # Use raw SQL to avoid model relationship errors
        # First check if job exists
        check_result = await db.execute(text(
            "SELECT status::text FROM drug_requests WHERE id = :job_id"
        ), {'job_id': job_id})
        row = check_result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")

        current_status = row[0]

        # Validate and apply action
        if action == "cancel":
            await db.execute(text(
                "UPDATE drug_requests SET status = 'cancelled' WHERE id = :job_id"
            ), {'job_id': job_id})
            await db.commit()
            new_status = "cancelled"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action '{action}' for current status '{current_status}'")

        logger.info(f"Job {job_id} {action} successful, new status: {new_status}")

        return {
            "message": f"Job {job_id} {action} successful",
            "status": STATUS_MAP.get(new_status, new_status)
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error controlling job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to control job: {str(e)}")
