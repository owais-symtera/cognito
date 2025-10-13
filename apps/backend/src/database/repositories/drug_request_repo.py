"""
Drug request repository for CognitoAI Engine pharmaceutical platform.

Comprehensive drug request management with audit trails and pharmaceutical
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
from ..models import DrugRequest, CategoryResult, ProcessTracking, RequestStatus, User

logger = structlog.get_logger(__name__)


class DrugRequestRepository(BaseRepository[DrugRequest]):
    """
    Repository for pharmaceutical drug request operations.

    Provides comprehensive drug request management with audit trails
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
        Initialize drug request repository for pharmaceutical operations.

        Args:
            db: Async database session for pharmaceutical operations
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Since:
            Version 1.0.0
        """
        super().__init__(DrugRequest, db, user_id, correlation_id)

    async def create_drug_request(
        self,
        drug_name: str,
        user_id: Optional[str] = None,
        priority_categories: Optional[List[int]] = None,
        total_categories: int = 17,
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> DrugRequest:
        """
        Create new pharmaceutical drug intelligence request.

        Creates comprehensive drug request with audit trail support
        and pharmaceutical regulatory compliance tracking.

        Args:
            drug_name: Name of pharmaceutical drug to analyze
            user_id: User creating the pharmaceutical request
            priority_categories: Prioritized category processing order
            total_categories: Total pharmaceutical categories to process
            request_metadata: Additional pharmaceutical request metadata

        Returns:
            DrugRequest: Created drug request with full audit trail

        Example:
            >>> drug_request = await repo.create_drug_request(
            ...     drug_name="Metformin",
            ...     user_id="user-123",
            ...     priority_categories=[1, 2, 3]
            ... )

        Since:
            Version 1.0.0
        """
        try:
            request_data = {
                "drug_name": drug_name.strip(),
                "user_id": user_id or self.user_id,
                "status": RequestStatus.PENDING,
                "total_categories": total_categories,
                "completed_categories": 0,
                "failed_categories": [],
                "priority_categories": priority_categories,
                "request_metadata": request_metadata or {}
            }

            drug_request = await self.create(
                request_data,
                audit_description=f"Created pharmaceutical intelligence request for {drug_name}"
            )

            logger.info(
                "Pharmaceutical drug request created",
                drug_request_id=drug_request.id,
                drug_name=drug_name,
                total_categories=total_categories,
                user_id=user_id
            )

            return drug_request

        except Exception as e:
            logger.error(
                "Failed to create pharmaceutical drug request",
                drug_name=drug_name,
                error=str(e)
            )
            raise

    async def get_drug_request_with_details(
        self,
        request_id: str
    ) -> Optional[DrugRequest]:
        """
        Get drug request with complete pharmaceutical analysis details.

        Retrieves drug request with all related category results, sources,
        and process tracking for comprehensive pharmaceutical analysis.

        Args:
            request_id: Unique pharmaceutical drug request identifier

        Returns:
            Optional[DrugRequest]: Drug request with complete pharmaceutical details

        Since:
            Version 1.0.0
        """
        try:
            query = (
                select(DrugRequest)
                .where(DrugRequest.id == request_id)
                .options(
                    selectinload(DrugRequest.category_results).selectinload(CategoryResult.source_references),
                    selectinload(DrugRequest.category_results).selectinload(CategoryResult.source_conflicts),
                    selectinload(DrugRequest.process_tracking_entries),
                    selectinload(DrugRequest.user),
                    selectinload(DrugRequest.audit_events)
                )
            )

            result = await self.db.execute(query)
            drug_request = result.scalar_one_or_none()

            if drug_request:
                logger.debug(
                    "Retrieved pharmaceutical drug request with details",
                    drug_request_id=request_id,
                    category_results=len(drug_request.category_results),
                    process_entries=len(drug_request.process_tracking_entries)
                )

            return drug_request

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical drug request with details",
                request_id=request_id,
                error=str(e)
            )
            raise

    async def update_request_status(
        self,
        request_id: str,
        status: RequestStatus,
        completed_categories: Optional[int] = None,
        failed_categories: Optional[List[str]] = None,
        actual_processing_time: Optional[int] = None
    ) -> Optional[DrugRequest]:
        """
        Update pharmaceutical drug request status with audit trail.

        Updates request processing status with comprehensive audit logging
        for pharmaceutical regulatory compliance and progress tracking.

        Args:
            request_id: Unique pharmaceutical drug request identifier
            status: New processing status for pharmaceutical request
            completed_categories: Number of successfully completed categories
            failed_categories: List of failed category names
            actual_processing_time: Actual processing time in seconds

        Returns:
            Optional[DrugRequest]: Updated pharmaceutical drug request

        Since:
            Version 1.0.0
        """
        try:
            update_data = {"status": status}

            if status in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
                update_data["completed_at"] = datetime.utcnow()

            if completed_categories is not None:
                update_data["completed_categories"] = completed_categories

            if failed_categories is not None:
                update_data["failed_categories"] = failed_categories

            if actual_processing_time is not None:
                update_data["actual_processing_time"] = actual_processing_time

            updated_request = await self.update(
                request_id,
                update_data,
                audit_description=f"Updated pharmaceutical request status to {status.value}"
            )

            if updated_request:
                logger.info(
                    "Pharmaceutical drug request status updated",
                    drug_request_id=request_id,
                    new_status=status.value,
                    completed_categories=completed_categories,
                    failed_categories=len(failed_categories) if failed_categories else 0
                )

            return updated_request

        except Exception as e:
            logger.error(
                "Failed to update pharmaceutical drug request status",
                request_id=request_id,
                status=status.value,
                error=str(e)
            )
            raise

    async def get_user_requests(
        self,
        user_id: str,
        status_filter: Optional[RequestStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DrugRequest]:
        """
        Get pharmaceutical drug requests for specific user.

        Retrieves user's pharmaceutical drug requests with optional
        status filtering for comprehensive request management.

        Args:
            user_id: User identifier for pharmaceutical request filtering
            status_filter: Optional status filter for pharmaceutical requests
            limit: Maximum number of pharmaceutical requests to return
            offset: Offset for pharmaceutical request pagination

        Returns:
            List[DrugRequest]: User's pharmaceutical drug requests

        Since:
            Version 1.0.0
        """
        try:
            filters = {"user_id": user_id}
            if status_filter:
                filters["status"] = status_filter

            requests = await self.list_all(
                limit=limit,
                offset=offset,
                filters=filters,
                order_by="created_at"
            )

            logger.debug(
                "Retrieved pharmaceutical user requests",
                user_id=user_id,
                request_count=len(requests),
                status_filter=status_filter.value if status_filter else None
            )

            return requests

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical user requests",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_requests_by_status(
        self,
        status: RequestStatus,
        limit: int = 100
    ) -> List[DrugRequest]:
        """
        Get pharmaceutical drug requests by processing status.

        Retrieves pharmaceutical requests with specific status for
        operational monitoring and processing management.

        Args:
            status: Processing status for pharmaceutical request filtering
            limit: Maximum number of pharmaceutical requests to return

        Returns:
            List[DrugRequest]: Pharmaceutical requests with specified status

        Since:
            Version 1.0.0
        """
        try:
            requests = await self.list_all(
                limit=limit,
                filters={"status": status},
                order_by="created_at"
            )

            logger.debug(
                "Retrieved pharmaceutical requests by status",
                status=status.value,
                request_count=len(requests)
            )

            return requests

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical requests by status",
                status=status.value,
                error=str(e)
            )
            raise

    async def get_processing_statistics(
        self,
        date_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get pharmaceutical drug request processing statistics.

        Returns comprehensive processing statistics for pharmaceutical
        requests including success rates, processing times, and trends.

        Args:
            date_range_days: Number of days to include in statistics

        Returns:
            Dict[str, Any]: Pharmaceutical processing statistics

        Since:
            Version 1.0.0
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=date_range_days)

            # Get requests within date range
            requests = await self.list_all(
                filters={"created_at": [">", cutoff_date]}
            )

            # Calculate statistics
            total_requests = len(requests)
            completed_requests = [r for r in requests if r.status == RequestStatus.COMPLETED]
            failed_requests = [r for r in requests if r.status == RequestStatus.FAILED]
            processing_requests = [r for r in requests if r.status == RequestStatus.PROCESSING]

            # Calculate processing times for completed requests
            processing_times = [
                r.actual_processing_time for r in completed_requests
                if r.actual_processing_time is not None
            ]

            statistics = {
                "date_range_days": date_range_days,
                "total_requests": total_requests,
                "completed_requests": len(completed_requests),
                "failed_requests": len(failed_requests),
                "processing_requests": len(processing_requests),
                "success_rate": len(completed_requests) / total_requests if total_requests > 0 else 0.0,
                "failure_rate": len(failed_requests) / total_requests if total_requests > 0 else 0.0,
            }

            if processing_times:
                statistics.update({
                    "average_processing_time_seconds": sum(processing_times) / len(processing_times),
                    "min_processing_time_seconds": min(processing_times),
                    "max_processing_time_seconds": max(processing_times),
                })

            # Drug name analysis
            drug_counts = {}
            for request in requests:
                drug_name = request.drug_name.lower()
                drug_counts[drug_name] = drug_counts.get(drug_name, 0) + 1

            statistics["top_drugs"] = sorted(
                drug_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            logger.info(
                "Generated pharmaceutical processing statistics",
                date_range_days=date_range_days,
                total_requests=total_requests,
                success_rate=statistics["success_rate"]
            )

            return statistics

        except Exception as e:
            logger.error(
                "Failed to generate pharmaceutical processing statistics",
                date_range_days=date_range_days,
                error=str(e)
            )
            raise