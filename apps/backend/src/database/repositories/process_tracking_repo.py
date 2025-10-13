"""
Process tracking repository for CognitoAI Engine pharmaceutical platform.

Comprehensive process correlation and tracking repository with audit trails
for pharmaceutical regulatory compliance and operational monitoring.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from ..models import ProcessTracking, DrugRequest, CategoryResult, RequestStatus

logger = structlog.get_logger(__name__)


class ProcessTrackingRepository(BaseRepository[ProcessTracking]):
    """
    Repository for pharmaceutical process tracking and correlation operations.

    Provides comprehensive process tracking with correlation capabilities
    for pharmaceutical intelligence platform operations and audit compliance.

    Enables complete process lineage tracking across all pharmaceutical
    intelligence operations for regulatory compliance and operational monitoring.

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
        Initialize process tracking repository for pharmaceutical operations.

        Args:
            db: Async database session for pharmaceutical process tracking
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Since:
            Version 1.0.0
        """
        super().__init__(ProcessTracking, db, user_id, correlation_id)

    async def create_process(
        self,
        request_id: str,
        process_type: str,
        correlation_id: Optional[str] = None,
        parent_process_id: Optional[str] = None,
        process_metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessTracking:
        """
        Create new pharmaceutical process tracking entry.

        Creates comprehensive process tracking for pharmaceutical intelligence
        operations with correlation support for audit trail compliance.

        Args:
            request_id: Associated pharmaceutical drug request identifier
            process_type: Type of pharmaceutical process being tracked
            correlation_id: Process correlation ID for audit lineage
            parent_process_id: Parent process for hierarchical tracking
            process_metadata: Additional pharmaceutical process metadata

        Returns:
            ProcessTracking: Created process tracking entry with full audit trail

        Raises:
            ValueError: If required pharmaceutical process data is missing
            SQLAlchemyError: If database operation fails

        Example:
            >>> process = await repo.create_process(
            ...     request_id="req-123",
            ...     process_type="category_processing",
            ...     process_metadata={"category": "Clinical Trials", "api_provider": "chatgpt"}
            ... )

        Since:
            Version 1.0.0
        """
        try:
            process_data = {
                "request_id": request_id,
                "process_type": process_type,
                "status": "started",
                "correlation_id": correlation_id or self.correlation_id,
                "parent_process_id": parent_process_id,
                "process_metadata": process_metadata or {},
                "started_at": datetime.utcnow()
            }

            process = await self.create(
                process_data,
                audit_description=f"Started pharmaceutical process: {process_type}"
            )

            logger.info(
                "Pharmaceutical process tracking created",
                process_id=process.id,
                request_id=request_id,
                process_type=process_type,
                correlation_id=correlation_id or self.correlation_id
            )

            return process

        except Exception as e:
            logger.error(
                "Failed to create pharmaceutical process tracking",
                request_id=request_id,
                process_type=process_type,
                error=str(e)
            )
            raise

    async def complete_process(
        self,
        process_id: str,
        status: str = "completed",
        error_message: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> Optional[ProcessTracking]:
        """
        Complete pharmaceutical process tracking with comprehensive audit.

        Marks pharmaceutical process as completed with duration tracking
        and comprehensive audit trail for regulatory compliance.

        Args:
            process_id: Unique process tracking identifier
            status: Final process status (completed, failed, etc.)
            error_message: Error details if process failed
            metadata_update: Additional metadata to merge with existing

        Returns:
            Optional[ProcessTracking]: Updated process tracking entry

        Example:
            >>> completed = await repo.complete_process(
            ...     "proc-123",
            ...     status="completed",
            ...     metadata_update={"sources_found": 15, "conflicts_detected": 2}
            ... )

        Since:
            Version 1.0.0
        """
        try:
            # Get current process for metadata merging
            current_process = await self.get_by_id(process_id)
            if not current_process:
                logger.warning(
                    "Process not found for pharmaceutical completion",
                    process_id=process_id
                )
                return None

            # Merge metadata for comprehensive pharmaceutical tracking
            updated_metadata = current_process.metadata or {}
            if metadata_update:
                updated_metadata.update(metadata_update)

            # Calculate process duration for pharmaceutical performance tracking
            completion_time = datetime.utcnow()
            if current_process.started_at:
                duration = completion_time - current_process.started_at
                updated_metadata["duration_seconds"] = duration.total_seconds()

            update_data = {
                "status": status,
                "completed_at": completion_time,
                "process_metadata": updated_metadata
            }

            if error_message:
                update_data["error_message"] = error_message

            completed_process = await self.update(
                process_id,
                update_data,
                audit_description=f"Completed pharmaceutical process with status: {status}"
            )

            logger.info(
                "Pharmaceutical process tracking completed",
                process_id=process_id,
                status=status,
                duration_seconds=updated_metadata.get("duration_seconds"),
                error_message=error_message
            )

            return completed_process

        except Exception as e:
            logger.error(
                "Failed to complete pharmaceutical process tracking",
                process_id=process_id,
                error=str(e)
            )
            raise

    async def get_process_hierarchy(
        self,
        root_process_id: str
    ) -> List[ProcessTracking]:
        """
        Get complete process hierarchy for pharmaceutical audit trails.

        Retrieves entire process hierarchy starting from root process
        for comprehensive pharmaceutical audit trail analysis.

        Args:
            root_process_id: Root process identifier for hierarchy traversal

        Returns:
            List[ProcessTracking]: Complete process hierarchy with audit trails

        Example:
            >>> hierarchy = await repo.get_process_hierarchy("proc-root-123")
            >>> for process in hierarchy:
            ...     print(f"Process: {process.process_type}, Status: {process.status}")

        Since:
            Version 1.0.0
        """
        try:
            # Use recursive CTE to get complete hierarchy
            query = select(ProcessTracking).where(
                or_(
                    ProcessTracking.id == root_process_id,
                    ProcessTracking.parent_process_id == root_process_id
                )
            ).order_by(ProcessTracking.started_at)

            result = await self.db.execute(query)
            processes = result.scalars().all()

            # Get children recursively for pharmaceutical process lineage
            all_processes = list(processes)
            parent_ids = [p.id for p in processes if p.id != root_process_id]

            while parent_ids:
                child_query = select(ProcessTracking).where(
                    ProcessTracking.parent_process_id.in_(parent_ids)
                ).order_by(ProcessTracking.started_at)

                child_result = await self.db.execute(child_query)
                children = list(child_result.scalars().all())

                if not children:
                    break

                all_processes.extend(children)
                parent_ids = [p.id for p in children]

            logger.debug(
                "Retrieved pharmaceutical process hierarchy",
                root_process_id=root_process_id,
                total_processes=len(all_processes)
            )

            return all_processes

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical process hierarchy",
                root_process_id=root_process_id,
                error=str(e)
            )
            raise

    async def get_request_processes(
        self,
        request_id: str,
        include_completed: bool = True,
        process_type_filter: Optional[str] = None
    ) -> List[ProcessTracking]:
        """
        Get all processes for pharmaceutical drug request.

        Retrieves all process tracking entries associated with a specific
        pharmaceutical drug request for comprehensive audit analysis.

        Args:
            request_id: Pharmaceutical drug request identifier
            include_completed: Whether to include completed processes
            process_type_filter: Filter by specific process type

        Returns:
            List[ProcessTracking]: All processes for pharmaceutical request

        Example:
            >>> processes = await repo.get_request_processes(
            ...     "req-123",
            ...     process_type_filter="category_processing"
            ... )

        Since:
            Version 1.0.0
        """
        try:
            query = select(ProcessTracking).where(
                ProcessTracking.request_id == request_id
            )

            # Apply pharmaceutical process filters
            if not include_completed:
                query = query.where(ProcessTracking.completed_at.is_(None))

            if process_type_filter:
                query = query.where(ProcessTracking.process_type == process_type_filter)

            query = query.order_by(ProcessTracking.started_at)

            result = await self.db.execute(query)
            processes = list(result.scalars().all())

            logger.debug(
                "Retrieved pharmaceutical request processes",
                request_id=request_id,
                process_count=len(processes),
                process_type_filter=process_type_filter,
                include_completed=include_completed
            )

            return processes

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical request processes",
                request_id=request_id,
                error=str(e)
            )
            raise

    async def get_correlation_processes(
        self,
        correlation_id: str
    ) -> List[ProcessTracking]:
        """
        Get all processes by correlation ID for pharmaceutical audit lineage.

        Retrieves all process tracking entries with the same correlation ID
        for comprehensive pharmaceutical audit trail analysis.

        Args:
            correlation_id: Process correlation identifier for audit lineage

        Returns:
            List[ProcessTracking]: All processes with matching correlation ID

        Example:
            >>> correlated = await repo.get_correlation_processes("corr-abc-123")
            >>> print(f"Found {len(correlated)} correlated pharmaceutical processes")

        Since:
            Version 1.0.0
        """
        try:
            query = select(ProcessTracking).where(
                ProcessTracking.correlation_id == correlation_id
            ).order_by(ProcessTracking.started_at)

            result = await self.db.execute(query)
            processes = list(result.scalars().all())

            logger.debug(
                "Retrieved correlated pharmaceutical processes",
                correlation_id=correlation_id,
                process_count=len(processes)
            )

            return processes

        except Exception as e:
            logger.error(
                "Failed to retrieve correlated pharmaceutical processes",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise

    async def get_active_processes(
        self,
        process_type: Optional[str] = None,
        older_than_minutes: Optional[int] = None
    ) -> List[ProcessTracking]:
        """
        Get active pharmaceutical processes for monitoring and cleanup.

        Retrieves currently running pharmaceutical processes with optional
        filtering for operational monitoring and stuck process cleanup.

        Args:
            process_type: Filter by specific pharmaceutical process type
            older_than_minutes: Filter processes older than specified minutes

        Returns:
            List[ProcessTracking]: Active pharmaceutical processes

        Example:
            >>> stuck_processes = await repo.get_active_processes(
            ...     process_type="category_processing",
            ...     older_than_minutes=60
            ... )

        Since:
            Version 1.0.0
        """
        try:
            query = select(ProcessTracking).where(
                ProcessTracking.completed_at.is_(None)
            )

            # Filter by pharmaceutical process type
            if process_type:
                query = query.where(ProcessTracking.process_type == process_type)

            # Filter by age for stuck process detection
            if older_than_minutes:
                cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
                query = query.where(ProcessTracking.started_at <= cutoff_time)

            query = query.order_by(ProcessTracking.started_at)

            result = await self.db.execute(query)
            processes = list(result.scalars().all())

            logger.debug(
                "Retrieved active pharmaceutical processes",
                process_count=len(processes),
                process_type=process_type,
                older_than_minutes=older_than_minutes
            )

            return processes

        except Exception as e:
            logger.error(
                "Failed to retrieve active pharmaceutical processes",
                process_type=process_type,
                error=str(e)
            )
            raise

    async def get_process_statistics(
        self,
        request_id: Optional[str] = None,
        process_type: Optional[str] = None,
        date_range_days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Get pharmaceutical process performance statistics.

        Retrieves comprehensive performance statistics for pharmaceutical
        processes including success rates, durations, and error analysis.

        Args:
            request_id: Filter by specific pharmaceutical request
            process_type: Filter by specific pharmaceutical process type
            date_range_days: Number of days to include in statistics

        Returns:
            Dict[str, Any]: Comprehensive pharmaceutical process statistics

        Example:
            >>> stats = await repo.get_process_statistics(
            ...     process_type="category_processing",
            ...     date_range_days=7
            ... )
            >>> print(f"Success rate: {stats['success_rate']:.1%}")

        Since:
            Version 1.0.0
        """
        try:
            # Build base query for pharmaceutical process statistics
            base_query = select(ProcessTracking)

            if date_range_days:
                cutoff_date = datetime.utcnow() - timedelta(days=date_range_days)
                base_query = base_query.where(ProcessTracking.started_at >= cutoff_date)

            if request_id:
                base_query = base_query.where(ProcessTracking.request_id == request_id)

            if process_type:
                base_query = base_query.where(ProcessTracking.process_type == process_type)

            # Execute query and calculate statistics
            result = await self.db.execute(base_query)
            processes = list(result.scalars().all())

            total_processes = len(processes)
            completed_processes = [p for p in processes if p.completed_at]
            successful_processes = [p for p in completed_processes if p.status == "completed"]
            failed_processes = [p for p in completed_processes if p.status == "failed"]

            # Calculate pharmaceutical process performance metrics
            statistics = {
                "total_processes": total_processes,
                "completed_processes": len(completed_processes),
                "successful_processes": len(successful_processes),
                "failed_processes": len(failed_processes),
                "active_processes": total_processes - len(completed_processes),
                "success_rate": len(successful_processes) / len(completed_processes) if completed_processes else 0.0,
                "failure_rate": len(failed_processes) / len(completed_processes) if completed_processes else 0.0,
            }

            # Calculate duration statistics for pharmaceutical performance analysis
            completed_durations = []
            for process in completed_processes:
                if process.started_at and process.completed_at:
                    duration = (process.completed_at - process.started_at).total_seconds()
                    completed_durations.append(duration)

            if completed_durations:
                statistics.update({
                    "average_duration_seconds": sum(completed_durations) / len(completed_durations),
                    "min_duration_seconds": min(completed_durations),
                    "max_duration_seconds": max(completed_durations),
                })

            # Process type breakdown for pharmaceutical analysis
            process_type_counts = {}
            for process in processes:
                process_type_counts[process.process_type] = process_type_counts.get(process.process_type, 0) + 1

            statistics["process_type_breakdown"] = process_type_counts

            logger.debug(
                "Generated pharmaceutical process statistics",
                request_id=request_id,
                process_type=process_type,
                date_range_days=date_range_days,
                total_processes=total_processes,
                success_rate=statistics["success_rate"]
            )

            return statistics

        except Exception as e:
            logger.error(
                "Failed to generate pharmaceutical process statistics",
                request_id=request_id,
                process_type=process_type,
                error=str(e)
            )
            raise