"""
Status tracking API endpoints for pharmaceutical process monitoring.

Provides RESTful endpoints for querying and tracking the status of
pharmaceutical analysis requests with comprehensive audit trails.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ...database.connection import get_db_session
from ...schemas.status import (
    ProcessingStatus,
    ProcessStatusResponse,
    ProcessHistoryEntry,
    ProcessHistoryResponse,
    BulkStatusRequest,
    BulkStatusResponse,
    StatusUpdateRequest,
    ProcessingMetrics
)
from ...core.status_tracker import StatusTracker
from ...auth.dependencies import require_api_key, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/status",
    tags=["status"],
    responses={404: {"description": "Process not found"}}
)


async def get_correlation_id() -> str:
    """
    Get correlation ID for request tracking.
    
    Returns:
        Request correlation ID
    
    Since:
        Version 1.0.0
    """
    import uuid
    return str(uuid.uuid4())


@router.get(
    "/{process_id}",
    response_model=ProcessStatusResponse,
    summary="Get process status",
    description="Query the current status of a pharmaceutical analysis process"
)
async def get_process_status(
    process_id: str,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key),
    correlation_id: str = Depends(get_correlation_id)
) -> ProcessStatusResponse:
    """
    Get current status of a pharmaceutical analysis process.
    
    Provides comprehensive status information including progress,
    estimated completion, and audit summary.
    
    Args:
        process_id: Process identifier
        db: Database session
        api_key: API key for authentication
        correlation_id: Request correlation ID
    
    Returns:
        Process status information
    
    Raises:
        HTTPException: If process not found or unauthorized
    
    Since:
        Version 1.0.0
    """
    try:
        tracker = StatusTracker(db, correlation_id)
        status_response = await tracker.get_status(process_id)
        
        logger.info(
            "Process status retrieved",
            process_id=process_id,
            status=status_response.current_stage.value,
            progress=status_response.progress_percentage
        )
        
        return status_response
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process {process_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve process status",
            process_id=process_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status: {str(e)}"
        )


@router.get(
    "/{process_id}/history",
    response_model=ProcessHistoryResponse,
    summary="Get process history",
    description="Retrieve complete status history for a process"
)
async def get_process_history(
    process_id: str,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key),
    correlation_id: str = Depends(get_correlation_id)
) -> ProcessHistoryResponse:
    """
    Get complete status history for a pharmaceutical analysis process.
    
    Returns chronological history of all status transitions with
    timestamps and duration information.
    
    Args:
        process_id: Process identifier
        db: Database session
        api_key: API key for authentication
        correlation_id: Request correlation ID
    
    Returns:
        Process history information
    
    Raises:
        HTTPException: If process not found
    
    Since:
        Version 1.0.0
    """
    try:
        tracker = StatusTracker(db, correlation_id)
        history = await tracker.get_process_history(process_id)
        
        # Get current status for final status
        current_status = await tracker.get_status(process_id)
        
        # Calculate total duration
        if history:
            first_timestamp = history[0].timestamp
            last_timestamp = history[-1].timestamp
            duration = last_timestamp - first_timestamp
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            total_duration = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            total_duration = "00:00:00"
        
        response = ProcessHistoryResponse(
            process_id=process_id,
            request_id=current_status.request_id,
            history=history,
            total_duration=total_duration,
            final_status=current_status.current_stage
        )
        
        logger.info(
            "Process history retrieved",
            process_id=process_id,
            entry_count=len(history)
        )
        
        return response
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process {process_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve process history",
            process_id=process_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.post(
    "/bulk",
    response_model=BulkStatusResponse,
    summary="Bulk status query",
    description="Query status for multiple processes in a single request"
)
async def get_bulk_status(
    request: BulkStatusRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key),
    correlation_id: str = Depends(get_correlation_id)
) -> BulkStatusResponse:
    """
    Query status for multiple pharmaceutical analysis processes.
    
    Efficiently retrieves status for up to 100 processes in a single
    request with error handling for invalid IDs.
    
    Args:
        request: Bulk status request with process IDs
        db: Database session
        api_key: API key for authentication
        correlation_id: Request correlation ID
    
    Returns:
        Bulk status response with found and not found processes
    
    Since:
        Version 1.0.0
    """
    try:
        tracker = StatusTracker(db, correlation_id)
        
        # Get status for all requested processes
        statuses = await tracker.get_bulk_status(request.process_ids)
        
        # Identify found process IDs
        found_ids = {s.process_id for s in statuses}
        
        # Identify not found IDs
        not_found = [
            pid for pid in request.process_ids
            if pid not in found_ids
        ]
        
        # TODO: Implement authorization check
        unauthorized = []
        
        response = BulkStatusResponse(
            total_queried=len(request.process_ids),
            found=len(statuses),
            not_found=not_found,
            unauthorized=unauthorized,
            statuses=statuses,
            query_timestamp=datetime.utcnow()
        )
        
        logger.info(
            "Bulk status query completed",
            total_queried=response.total_queried,
            found=response.found,
            not_found_count=len(not_found)
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to perform bulk status query",
            process_count=len(request.process_ids),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk query: {str(e)}"
        )


@router.put(
    "/{process_id}/update",
    response_model=ProcessStatusResponse,
    summary="Update process status",
    description="Internal endpoint for updating process status",
    include_in_schema=False  # Hide from public API docs
)
async def update_process_status(
    process_id: str,
    update_request: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key),
    correlation_id: str = Depends(get_correlation_id)
) -> ProcessStatusResponse:
    """
    Update process status (internal use only).
    
    Used by background processors to update process status
    with validation and audit logging.
    
    Args:
        process_id: Process identifier
        update_request: Status update details
        db: Database session
        api_key: API key for authentication
        correlation_id: Request correlation ID
    
    Returns:
        Updated process status
    
    Raises:
        HTTPException: If update fails
    
    Since:
        Version 1.0.0
    """
    try:
        # TODO: Verify API key has permission to update status
        
        tracker = StatusTracker(db, correlation_id)
        updated_status = await tracker.update_status(
            process_id,
            update_request
        )
        
        logger.info(
            "Process status updated",
            process_id=process_id,
            new_status=update_request.status.value,
            progress=update_request.progress_percentage
        )
        
        return updated_status
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to update process status",
            process_id=process_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )


@router.get(
    "/metrics/processing",
    response_model=ProcessingMetrics,
    summary="Get processing metrics",
    description="Retrieve current processing metrics and system load"
)
async def get_processing_metrics(
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> ProcessingMetrics:
    """
    Get current processing metrics.
    
    Provides system-wide metrics for monitoring processing
    performance and system load.
    
    Args:
        db: Database session
        api_key: API key for authentication
    
    Returns:
        Processing metrics
    
    Since:
        Version 1.0.0
    """
    try:
        from sqlalchemy import select, and_, func
        from ...database.models import ProcessTracking
        
        # Count active processes
        active_stmt = select(func.count()).select_from(ProcessTracking).where(
            ProcessTracking.current_status.in_([
                ProcessingStatus.COLLECTING.value,
                ProcessingStatus.VERIFYING.value,
                ProcessingStatus.MERGING.value,
                ProcessingStatus.SUMMARIZING.value
            ])
        )
        active_result = await db.execute(active_stmt)
        active_count = active_result.scalar() or 0
        
        # Count queued processes
        queued_stmt = select(func.count()).select_from(ProcessTracking).where(
            ProcessTracking.current_status == ProcessingStatus.SUBMITTED.value
        )
        queued_result = await db.execute(queued_stmt)
        queued_count = queued_result.scalar() or 0
        
        # Count completed today
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        completed_stmt = select(func.count()).select_from(ProcessTracking).where(
            and_(
                ProcessTracking.current_status == ProcessingStatus.COMPLETED.value,
                ProcessTracking.completed_at >= today_start
            )
        )
        completed_result = await db.execute(completed_stmt)
        completed_today = completed_result.scalar() or 0
        
        # Count failed today
        failed_stmt = select(func.count()).select_from(ProcessTracking).where(
            and_(
                ProcessTracking.current_status == ProcessingStatus.FAILED.value,
                ProcessTracking.failed_at >= today_start
            )
        )
        failed_result = await db.execute(failed_stmt)
        failed_today = failed_result.scalar() or 0
        
        # Calculate average processing time
        avg_time_stmt = select(
            func.avg(
                func.extract(
                    'epoch',
                    ProcessTracking.completed_at - ProcessTracking.submitted_at
                )
            )
        ).where(
            and_(
                ProcessTracking.current_status == ProcessingStatus.COMPLETED.value,
                ProcessTracking.completed_at.is_not(None)
            )
        )
        avg_result = await db.execute(avg_time_stmt)
        avg_seconds = avg_result.scalar() or 0
        
        # Format average time
        hours, remainder = divmod(avg_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        avg_time = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        # Calculate system load (simplified)
        max_concurrent = 10  # TODO: Get from config
        system_load = min(1.0, active_count / max_concurrent)
        
        metrics = ProcessingMetrics(
            average_processing_time=avg_time,
            active_processes=active_count,
            queued_processes=queued_count,
            completed_today=completed_today,
            failed_today=failed_today,
            system_load=system_load
        )
        
        logger.info(
            "Processing metrics retrieved",
            active=active_count,
            queued=queued_count,
            load=system_load
        )
        
        return metrics
        
    except Exception as e:
        logger.error(
            "Failed to retrieve processing metrics",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )