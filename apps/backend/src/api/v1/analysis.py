"""
Drug analysis API endpoints for CognitoAI Engine pharmaceutical platform.

Provides RESTful endpoints for submitting and tracking pharmaceutical
intelligence analysis requests with comprehensive validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import hashlib
import time

from ...database.connection import get_db_session
from ...database.models import AnalysisRequest as AnalysisRequestModel
from ...schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResultsResponse,
    AnalysisErrorResponse,
    AnalysisStatus
)
from ...core.analysis_processor import AnalysisProcessor
from ...core.rate_limiter import RateLimiter
from ...auth.dependencies import get_current_user, require_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/analyze",
    tags=["analysis"],
    responses={
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service temporarily unavailable"}
    }
)

# Initialize rate limiter
rate_limiter = RateLimiter(
    max_requests=100,  # 100 requests per minute per API key
    time_window=60
)


def generate_request_id() -> str:
    """
    Generate unique request ID for tracking.
    
    Returns:
        Unique request identifier
    
    Since:
        Version 1.0.0
    """
    timestamp = str(time.time_ns())
    hash_obj = hashlib.sha256(timestamp.encode())
    return f"req_{hash_obj.hexdigest()[:12]}"


def estimate_processing_time(drug_count: int, category_count: int) -> int:
    """
    Estimate processing time based on request size.
    
    Args:
        drug_count: Number of drugs to analyze
        category_count: Number of categories to process
    
    Returns:
        Estimated time in milliseconds
    
    Since:
        Version 1.0.0
    """
    # Base time + per drug/category estimates
    base_time_ms = 500
    per_drug_ms = 200
    per_category_ms = 50
    
    total_ms = base_time_ms + (drug_count * per_drug_ms) + \
               (drug_count * category_count * per_category_ms)
    
    # Cap at 2000ms per requirements
    return min(total_ms, 2000)


@router.post(
    "/",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit drug analysis request",
    description="Submit pharmaceutical drugs for comprehensive intelligence analysis"
)
async def analyze_drugs(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key),
    x_correlation_id: Optional[str] = Header(None),
    x_priority: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Submit drugs for pharmaceutical intelligence analysis.
    
    Accepts drug names and initiates comprehensive analysis across
    configured pharmaceutical categories. Returns immediately with
    request ID for tracking.
    
    Args:
        request: Analysis request with drug names and options
        background_tasks: FastAPI background task handler
        db: Database session
        api_key: API key for authentication
        x_correlation_id: Optional correlation ID header
        x_priority: Optional priority override header
    
    Returns:
        Analysis response with request ID and status
    
    Raises:
        HTTPException: On validation errors or rate limiting
    
    Since:
        Version 1.0.0
    """
    # Check rate limiting
    if not await rate_limiter.check_rate_limit(api_key):
        logger.warning(
            "Rate limit exceeded",
            api_key=api_key[:8] + "...",
            drug_count=len(request.drug_names)
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry after 60 seconds."
        )
    
    # Use header correlation ID if provided
    correlation_id = x_correlation_id or request.correlation_id
    priority = x_priority or request.priority
    
    # Validate priority
    if priority not in ["low", "normal", "high", "urgent"]:
        priority = "normal"
    
    try:
        # Generate request ID
        request_id = generate_request_id()
        
        # Get active categories if not specified
        if not request.categories:
            from ...core.category_manager import CategoryManager
            manager = CategoryManager(db, api_key, correlation_id)
            active_categories = await manager.get_active_categories()
            category_count = len(active_categories)
        else:
            category_count = len(request.categories)
        
        # Estimate processing time
        estimated_time_ms = estimate_processing_time(
            len(request.drug_names),
            category_count
        )
        
        # Create analysis request in database
        analysis_request = AnalysisRequestModel(
            request_id=request_id,
            correlation_id=correlation_id,
            drug_names=request.drug_names,
            categories=[cat.value for cat in request.categories] if request.categories else None,
            priority=priority,
            status=AnalysisStatus.PENDING.value,
            api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
            callback_url=request.callback_url,
            created_at=datetime.utcnow(),
            estimated_completion_time_ms=estimated_time_ms
        )
        
        db.add(analysis_request)
        await db.commit()
        
        # Queue for background processing
        processor = AnalysisProcessor(db, request_id, correlation_id)
        background_tasks.add_task(
            processor.process_analysis,
            request.drug_names,
            request.categories,
            priority
        )
        
        logger.info(
            "Analysis request submitted",
            request_id=request_id,
            correlation_id=correlation_id,
            drug_count=len(request.drug_names),
            category_count=category_count,
            priority=priority
        )
        
        # Build response
        return {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status": AnalysisStatus.PROCESSING,
            "message": f"Analysis initiated for {len(request.drug_names)} drug(s) across {category_count} categories",
            "drug_count": len(request.drug_names),
            "category_count": category_count,
            "estimated_completion_time_ms": estimated_time_ms,
            "results_url": f"/api/v1/analyze/results/{request_id}"
        }
        
    except Exception as e:
        logger.error(
            "Failed to submit analysis request",
            error=str(e),
            correlation_id=correlation_id,
            drug_names=request.drug_names
        )
        
        # Return error response
        error_response = AnalysisErrorResponse(
            error="submission_failed",
            message=f"Failed to submit analysis request: {str(e)}",
            correlation_id=correlation_id,
            details={"drug_count": len(request.drug_names)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict()
        )


@router.get(
    "/results/{request_id}",
    response_model=AnalysisResultsResponse,
    summary="Get analysis results",
    description="Retrieve results for a submitted analysis request"
)
async def get_analysis_results(
    request_id: str,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Retrieve analysis results by request ID.
    
    Args:
        request_id: Analysis request identifier
        db: Database session
        api_key: API key for authentication
    
    Returns:
        Complete analysis results if ready
    
    Raises:
        HTTPException: If request not found or not ready
    
    Since:
        Version 1.0.0
    """
    try:
        # Get request from database
        from sqlalchemy import select
        stmt = select(AnalysisRequestModel).where(
            AnalysisRequestModel.request_id == request_id
        )
        result = await db.execute(stmt)
        analysis_request = result.scalar_one_or_none()
        
        if not analysis_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis request {request_id} not found"
            )
        
        # Verify API key matches
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if analysis_request.api_key_hash != key_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this analysis request"
            )
        
        # Check if results are ready
        if analysis_request.status == AnalysisStatus.PROCESSING.value:
            # Return 202 with status update
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "request_id": request_id,
                    "status": analysis_request.status,
                    "message": "Analysis still processing",
                    "progress_percentage": analysis_request.progress_percentage or 0
                }
            )
        
        # Build results response
        return {
            "request_id": request_id,
            "correlation_id": analysis_request.correlation_id,
            "status": analysis_request.status,
            "drugs": analysis_request.results or [],
            "total_processing_time_ms": analysis_request.processing_time_ms or 0,
            "started_at": analysis_request.created_at,
            "completed_at": analysis_request.completed_at,
            "errors": analysis_request.errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve analysis results",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve results: {str(e)}"
        )


@router.get(
    "/status/{request_id}",
    summary="Check analysis status",
    description="Check the current status of an analysis request"
)
async def check_analysis_status(
    request_id: str,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Check status of analysis request.
    
    Args:
        request_id: Analysis request identifier
        db: Database session
        api_key: API key for authentication
    
    Returns:
        Current status information
    
    Since:
        Version 1.0.0
    """
    try:
        # Get request from database
        from sqlalchemy import select
        stmt = select(AnalysisRequestModel).where(
            AnalysisRequestModel.request_id == request_id
        )
        result = await db.execute(stmt)
        analysis_request = result.scalar_one_or_none()
        
        if not analysis_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis request {request_id} not found"
            )
        
        # Verify API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if analysis_request.api_key_hash != key_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Calculate elapsed time
        elapsed_time_ms = 0
        if analysis_request.created_at:
            elapsed = datetime.utcnow() - analysis_request.created_at
            elapsed_time_ms = int(elapsed.total_seconds() * 1000)
        
        return {
            "request_id": request_id,
            "status": analysis_request.status,
            "progress_percentage": analysis_request.progress_percentage or 0,
            "elapsed_time_ms": elapsed_time_ms,
            "estimated_remaining_ms": max(
                0,
                (analysis_request.estimated_completion_time_ms or 0) - elapsed_time_ms
            ),
            "message": f"Processing {len(analysis_request.drug_names)} drugs"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to check analysis status",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check status: {str(e)}"
        )


@router.delete(
    "/{request_id}",
    summary="Cancel analysis request",
    description="Cancel a pending or processing analysis request"
)
async def cancel_analysis(
    request_id: str,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Cancel an analysis request.
    
    Args:
        request_id: Analysis request identifier
        db: Database session
        api_key: API key for authentication
    
    Returns:
        Cancellation confirmation
    
    Since:
        Version 1.0.0
    """
    try:
        # Get request from database
        from sqlalchemy import select
        stmt = select(AnalysisRequestModel).where(
            AnalysisRequestModel.request_id == request_id
        )
        result = await db.execute(stmt)
        analysis_request = result.scalar_one_or_none()
        
        if not analysis_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis request {request_id} not found"
            )
        
        # Verify API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if analysis_request.api_key_hash != key_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if cancellable
        if analysis_request.status in [AnalysisStatus.COMPLETED.value, AnalysisStatus.FAILED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel request with status: {analysis_request.status}"
            )
        
        # Update status
        analysis_request.status = AnalysisStatus.FAILED.value
        analysis_request.errors = ["Cancelled by user"]
        analysis_request.completed_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(
            "Analysis request cancelled",
            request_id=request_id
        )
        
        return {
            "request_id": request_id,
            "status": "cancelled",
            "message": "Analysis request successfully cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cancel analysis",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel request: {str(e)}"
        )