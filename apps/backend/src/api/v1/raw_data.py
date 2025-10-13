"""
API endpoints for raw data retrieval and management.

Provides secure access to stored API responses with comprehensive
search, filtering, and compliance features.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...database.session import get_db
from ...database.repositories.raw_data_repo import RawDataRepository
from ...core.security.access_control import AccessControlService, require_access
from ...core.security.data_encryption import DataMaskingService
from ...config.logging import PharmaceuticalLogger

router = APIRouter(prefix="/raw-data", tags=["Raw Data"])
logger = PharmaceuticalLogger(service_name="raw_data_api")


class RawDataSearchRequest(BaseModel):
    """Raw data search parameters."""
    pharmaceutical_compound: Optional[str] = Field(None, description="Drug compound to search")
    category: Optional[str] = Field(None, description="Category filter")
    provider: Optional[str] = Field(None, description="API provider filter")
    start_date: Optional[datetime] = Field(None, description="Start of date range")
    end_date: Optional[datetime] = Field(None, description="End of date range")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request tracing")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    include_archived: bool = Field(False, description="Include archived responses")


class RawDataResponse(BaseModel):
    """Raw data response with metadata."""
    id: str
    process_id: str
    request_id: str
    correlation_id: str
    provider: str
    pharmaceutical_compound: str
    category: str
    raw_response: Optional[Dict] = None  # May be masked
    standardized_response: Optional[Dict] = None
    relevance_score: float
    quality_score: float
    confidence_score: float
    response_time_ms: int
    cost: Optional[float] = None  # May be masked
    created_at: datetime
    archived_at: Optional[datetime] = None


class CostSummaryRequest(BaseModel):
    """Cost summary request parameters."""
    start_date: datetime = Field(..., description="Start date for analysis")
    end_date: datetime = Field(..., description="End date for analysis")
    group_by: str = Field("provider", description="Group by: provider, category, or compound")


class QualityMetricsResponse(BaseModel):
    """Quality metrics summary."""
    total_responses: int
    avg_relevance_score: float
    avg_quality_score: float
    avg_confidence_score: float
    avg_response_time_ms: float
    provider: Optional[str] = None
    category: Optional[str] = None


class StorageStatisticsResponse(BaseModel):
    """Storage usage statistics."""
    total_responses: int
    active_responses: int
    archived_responses: int
    invalid_responses: int
    total_storage_bytes: int
    total_storage_gb: float
    average_size_bytes: int


@router.post("/search", response_model=List[RawDataResponse])
async def search_raw_data(
    request: RawDataSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "researcher"})  # TODO: Real auth
) -> List[RawDataResponse]:
    """
    Search historical API responses.

    Requires appropriate access level based on user role.
    Data may be masked based on authorization level.
    """
    try:
        # Initialize services
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)
        masking_service = DataMaskingService()

        # Check access
        has_access = await access_control.check_access(
            current_user["id"],
            "api_responses",
            "read"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to raw data"
            )

        # Search responses
        if request.correlation_id:
            responses = await repo.get_by_correlation_id(request.correlation_id)
        elif request.pharmaceutical_compound:
            responses = await repo.search_by_compound(
                compound=request.pharmaceutical_compound,
                category=request.category,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=request.limit
            )
        else:
            # General search
            conditions = []
            if request.provider:
                conditions.append(f"provider = '{request.provider}'")
            if request.category:
                conditions.append(f"category = '{request.category}'")

            # TODO: Implement general search in repository
            responses = []

        # Filter and mask data based on user role
        result = []
        for response in responses:
            # Convert to dict
            response_dict = {
                'id': response.id,
                'process_id': response.process_id,
                'request_id': response.request_id,
                'correlation_id': response.correlation_id,
                'provider': response.provider,
                'pharmaceutical_compound': response.pharmaceutical_compound,
                'category': response.category,
                'raw_response': response.raw_response,
                'standardized_response': response.standardized_response,
                'relevance_score': response.relevance_score,
                'quality_score': response.quality_score,
                'confidence_score': response.confidence_score,
                'response_time_ms': response.response_time_ms,
                'cost': response.cost,
                'created_at': response.created_at,
                'archived_at': response.archived_at
            }

            # Apply data filtering
            filtered = await access_control.filter_data(
                response_dict,
                current_user["id"],
                "api_responses"
            )

            # Apply masking for sensitive fields
            masked = await masking_service.mask_data(
                filtered,
                current_user.get("role", "viewer")
            )

            result.append(RawDataResponse(**masked))

        # Log search
        await logger.log_data_access(
            resource="api_responses",
            action="search",
            user_id=current_user["id"],
            success=True,
            drug_names=[request.pharmaceutical_compound] if request.pharmaceutical_compound else []
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw data search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search raw data"
        )


@router.get("/{response_id}", response_model=RawDataResponse)
async def get_raw_data(
    response_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "researcher"})
) -> RawDataResponse:
    """
    Retrieve specific API response by ID.

    Data integrity validation is performed automatically.
    """
    try:
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)

        # Check access
        has_access = await access_control.check_access(
            current_user["id"],
            "api_responses",
            "read",
            response_id
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resource"
            )

        # Get response with metadata
        response = await repo.get_with_metadata(response_id)

        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )

        # Convert and filter
        response_dict = {
            'id': response.id,
            'process_id': response.process_id,
            'request_id': response.request_id,
            'correlation_id': response.correlation_id,
            'provider': response.provider,
            'pharmaceutical_compound': response.pharmaceutical_compound,
            'category': response.category,
            'raw_response': response.raw_response,
            'standardized_response': response.standardized_response,
            'relevance_score': response.relevance_score,
            'quality_score': response.quality_score,
            'confidence_score': response.confidence_score,
            'response_time_ms': response.response_time_ms,
            'cost': response.cost,
            'created_at': response.created_at,
            'archived_at': response.archived_at
        }

        # Apply filtering
        filtered = await access_control.filter_data(
            response_dict,
            current_user["id"],
            "api_responses"
        )

        return RawDataResponse(**filtered)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve raw data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve raw data"
        )


@router.post("/cost-summary")
async def get_cost_summary(
    request: CostSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "analyst"})
) -> List[Dict[str, Any]]:
    """
    Get cost summary for API usage.

    Requires analyst or higher access level.
    """
    try:
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)

        # Check access (cost data requires higher access)
        has_access = await access_control.check_access(
            current_user["id"],
            "api_responses",
            "read_cost"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient access level for cost data"
            )

        # Get cost summary
        summary = await repo.get_cost_summary(
            start_date=request.start_date,
            end_date=request.end_date,
            group_by=request.group_by
        )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cost summary"
        )


@router.get("/metrics/quality", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    provider: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "researcher"})
) -> QualityMetricsResponse:
    """
    Get quality metrics for API responses.
    """
    try:
        repo = RawDataRepository(db)

        metrics = await repo.get_quality_metrics(
            provider=provider,
            category=category
        )

        return QualityMetricsResponse(
            **metrics,
            provider=provider,
            category=category
        )

    except Exception as e:
        logger.error(f"Quality metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quality metrics"
        )


@router.get("/statistics/storage", response_model=StorageStatisticsResponse)
async def get_storage_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "admin"})
) -> StorageStatisticsResponse:
    """
    Get storage usage statistics.

    Requires admin access level.
    """
    try:
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)

        # Check admin access
        has_access = await access_control.check_access(
            current_user["id"],
            "system_stats",
            "read"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        stats = await repo.get_storage_statistics()

        return StorageStatisticsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Storage statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage statistics"
        )


@router.post("/archive")
async def archive_old_responses(
    days_old: int = Query(365, ge=30, description="Age threshold in days"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "admin"})
) -> Dict[str, Any]:
    """
    Archive old API responses.

    Requires admin or compliance access level.
    """
    try:
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)

        # Check access
        has_access = await access_control.check_access(
            current_user["id"],
            "api_responses",
            "archive"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient access for archival operations"
            )

        # Get candidates
        candidates = await repo.get_retention_candidates(days_old)
        candidate_ids = [c.id for c in candidates]

        # Archive
        archived_count = await repo.archive_responses(candidate_ids)

        await logger.log_system_health_check(
            component="data_archival",
            status="success",
            response_time_ms=0
        )

        return {
            'candidates': len(candidates),
            'archived': archived_count,
            'days_old': days_old,
            'timestamp': datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Archival failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive responses"
        )


@router.post("/validate-integrity")
async def validate_data_integrity(
    batch_size: int = Query(100, ge=10, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(lambda: {"id": "test_user", "role": "admin"})
) -> Dict[str, Any]:
    """
    Validate data integrity for stored responses.

    Requires admin access level.
    """
    try:
        repo = RawDataRepository(db)
        access_control = AccessControlService(db, logger)

        # Check admin access
        has_access = await access_control.check_access(
            current_user["id"],
            "system_maintenance",
            "execute"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Validate integrity
        valid_count, invalid_count = await repo.validate_integrity_batch(batch_size)

        return {
            'batch_size': batch_size,
            'valid': valid_count,
            'invalid': invalid_count,
            'timestamp': datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrity validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate data integrity"
        )