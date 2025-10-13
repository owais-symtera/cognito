"""
Category result repository for CognitoAI Engine pharmaceutical platform.

Comprehensive category result management with source tracking and pharmaceutical
regulatory compliance for the intelligence platform.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from ..models import CategoryResult, CategoryStatus, SourceReference, SourceConflict

logger = structlog.get_logger(__name__)


class CategoryResultRepository(BaseRepository[CategoryResult]):
    """
    Repository for pharmaceutical category result operations.

    Provides comprehensive category result management with source tracking
    and pharmaceutical regulatory compliance for the intelligence platform.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize category result repository for pharmaceutical operations.

        Args:
            db: Async database session for pharmaceutical operations
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Since:
            Version 1.0.0
        """
        super().__init__(CategoryResult, db, user_id, correlation_id)

    async def create_category_result(
        self,
        request_id: str,
        category_id: int,
        category_name: str,
        summary: str,
        confidence_score: float = 0.0,
        data_quality_score: float = 0.0
    ) -> CategoryResult:
        """
        Create new pharmaceutical category processing result.

        Creates comprehensive category result with audit trail support
        and pharmaceutical regulatory compliance tracking.

        Args:
            request_id: Associated pharmaceutical drug request identifier
            category_id: Pharmaceutical category identifier
            category_name: Category name for reference
            summary: Processed pharmaceutical category summary
            confidence_score: AI confidence in results (0.0 to 1.0)
            data_quality_score: Data quality assessment (0.0 to 1.0)

        Returns:
            CategoryResult: Created category result with full audit trail

        Since:
            Version 1.0.0
        """
        try:
            result_data = {
                "request_id": request_id,
                "category_id": category_id,
                "category_name": category_name,
                "summary": summary,
                "confidence_score": confidence_score,
                "data_quality_score": data_quality_score,
                "status": CategoryStatus.PENDING,
                "started_at": datetime.utcnow()
            }

            category_result = await self.create(
                result_data,
                audit_description=f"Created pharmaceutical category result for {category_name}"
            )

            logger.info(
                "Pharmaceutical category result created",
                category_result_id=category_result.id,
                request_id=request_id,
                category_name=category_name,
                confidence_score=confidence_score
            )

            return category_result

        except Exception as e:
            logger.error(
                "Failed to create pharmaceutical category result",
                request_id=request_id,
                category_name=category_name,
                error=str(e)
            )
            raise

    async def update_processing_status(
        self,
        result_id: str,
        status: CategoryStatus,
        processing_time_ms: Optional[int] = None,
        api_calls_made: Optional[int] = None,
        token_count: Optional[int] = None,
        cost_estimate: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> Optional[CategoryResult]:
        """
        Update pharmaceutical category processing status with metrics.

        Updates category processing status with comprehensive metrics
        for pharmaceutical regulatory compliance and cost tracking.

        Args:
            result_id: Unique category result identifier
            status: New processing status for pharmaceutical category
            processing_time_ms: Processing time in milliseconds
            api_calls_made: Number of API calls made for this category
            token_count: Total tokens used in processing
            cost_estimate: Estimated processing cost
            error_message: Error details if processing failed

        Returns:
            Optional[CategoryResult]: Updated pharmaceutical category result

        Since:
            Version 1.0.0
        """
        try:
            update_data = {"status": status}

            if status in [CategoryStatus.COMPLETED, CategoryStatus.FAILED]:
                update_data["completed_at"] = datetime.utcnow()

            if processing_time_ms is not None:
                update_data["processing_time_ms"] = processing_time_ms

            if api_calls_made is not None:
                update_data["api_calls_made"] = api_calls_made

            if token_count is not None:
                update_data["token_count"] = token_count

            if cost_estimate is not None:
                update_data["cost_estimate"] = cost_estimate

            if error_message is not None:
                update_data["error_message"] = error_message

            updated_result = await self.update(
                result_id,
                update_data,
                audit_description=f"Updated pharmaceutical category status to {status.value}"
            )

            if updated_result:
                logger.info(
                    "Pharmaceutical category result status updated",
                    category_result_id=result_id,
                    new_status=status.value,
                    processing_time_ms=processing_time_ms,
                    api_calls_made=api_calls_made,
                    token_count=token_count
                )

            return updated_result

        except Exception as e:
            logger.error(
                "Failed to update pharmaceutical category result status",
                result_id=result_id,
                status=status.value,
                error=str(e)
            )
            raise

    async def get_result_with_sources(
        self,
        result_id: str
    ) -> Optional[CategoryResult]:
        """
        Get category result with complete pharmaceutical source tracking.

        Retrieves category result with all source references and conflicts
        for comprehensive pharmaceutical regulatory compliance analysis.

        Args:
            result_id: Unique category result identifier

        Returns:
            Optional[CategoryResult]: Category result with complete source data

        Since:
            Version 1.0.0
        """
        try:
            query = (
                select(CategoryResult)
                .where(CategoryResult.id == result_id)
                .options(
                    selectinload(CategoryResult.source_references),
                    selectinload(CategoryResult.source_conflicts),
                    selectinload(CategoryResult.category),
                    selectinload(CategoryResult.drug_request)
                )
            )

            result = await self.db.execute(query)
            category_result = result.scalar_one_or_none()

            if category_result:
                logger.debug(
                    "Retrieved pharmaceutical category result with sources",
                    category_result_id=result_id,
                    source_references=len(category_result.source_references),
                    source_conflicts=len(category_result.source_conflicts)
                )

            return category_result

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical category result with sources",
                result_id=result_id,
                error=str(e)
            )
            raise

    async def get_request_results(
        self,
        request_id: str,
        status_filter: Optional[CategoryStatus] = None
    ) -> List[CategoryResult]:
        """
        Get all category results for pharmaceutical drug request.

        Retrieves all category processing results for specific drug request
        with optional status filtering for comprehensive analysis.

        Args:
            request_id: Pharmaceutical drug request identifier
            status_filter: Optional status filter for category results

        Returns:
            List[CategoryResult]: Category results for pharmaceutical request

        Since:
            Version 1.0.0
        """
        try:
            filters = {"request_id": request_id}
            if status_filter:
                filters["status"] = status_filter

            results = await self.list_all(
                filters=filters,
                order_by="category_id"
            )

            logger.debug(
                "Retrieved pharmaceutical request category results",
                request_id=request_id,
                result_count=len(results),
                status_filter=status_filter.value if status_filter else None
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical request category results",
                request_id=request_id,
                error=str(e)
            )
            raise