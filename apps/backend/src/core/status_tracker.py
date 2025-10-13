"""
Status tracking system for pharmaceutical process monitoring.

Manages process status updates, progress calculation, and
estimated completion times for drug analysis requests.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from ..database.models import ProcessTracking, DrugRequest, CategoryResult
from ..schemas.status import (
    ProcessingStatus,
    ProcessStatusResponse,
    ProcessHistoryEntry,
    AuditSummary,
    StatusUpdateRequest
)
from ..database.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class StatusTracker:
    """
    Manages process status tracking and updates.
    
    Handles status transitions, progress calculations, and
    estimated completion time predictions.
    
    Since:
        Version 1.0.0
    """
    
    # Progress percentages for each stage
    STAGE_PROGRESS = {
        ProcessingStatus.SUBMITTED: 0,
        ProcessingStatus.COLLECTING: 20,
        ProcessingStatus.VERIFYING: 80,
        ProcessingStatus.MERGING: 90,
        ProcessingStatus.SUMMARIZING: 95,
        ProcessingStatus.COMPLETED: 100,
        ProcessingStatus.FAILED: None,
        ProcessingStatus.CANCELLED: None
    }
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        ProcessingStatus.SUBMITTED: [
            ProcessingStatus.COLLECTING,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ],
        ProcessingStatus.COLLECTING: [
            ProcessingStatus.VERIFYING,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ],
        ProcessingStatus.VERIFYING: [
            ProcessingStatus.MERGING,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ],
        ProcessingStatus.MERGING: [
            ProcessingStatus.SUMMARIZING,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ],
        ProcessingStatus.SUMMARIZING: [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ],
        ProcessingStatus.COMPLETED: [],
        ProcessingStatus.FAILED: [],
        ProcessingStatus.CANCELLED: []
    }
    
    def __init__(
        self,
        db_session: AsyncSession,
        correlation_id: Optional[str] = None
    ):
        """
        Initialize status tracker.
        
        Args:
            db_session: Database session
            correlation_id: Correlation ID for tracking
        
        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.correlation_id = correlation_id
        self.repo = BaseRepository(db_session)
    
    async def create_process_tracking(
        self,
        request_id: str,
        drug_names: List[str],
        category_count: int = 17
    ) -> str:
        """
        Create new process tracking record.
        
        Args:
            request_id: Analysis request ID
            drug_names: List of drug names
            category_count: Total categories to process
        
        Returns:
            Process ID
        
        Since:
            Version 1.0.0
        """
        import hashlib
        import time
        
        # Generate unique process ID
        process_id = f"proc_{hashlib.sha256(f'{request_id}{time.time()}'.encode()).hexdigest()[:12]}"
        
        # Create tracking record
        tracking = ProcessTracking(
            id=process_id,
            request_id=request_id,
            current_status=ProcessingStatus.SUBMITTED.value,
            progress_percentage=0,
            categories_total=category_count,
            categories_completed=0,
            drug_names=drug_names,
            submitted_at=datetime.utcnow(),
            current_stage_start=datetime.utcnow()
        )
        
        self.db.add(tracking)
        await self.db.commit()
        
        logger.info(
            "Process tracking created",
            process_id=process_id,
            request_id=request_id,
            drug_count=len(drug_names)
        )
        
        return process_id
    
    async def update_status(
        self,
        process_id: str,
        update_request: StatusUpdateRequest
    ) -> ProcessStatusResponse:
        """
        Update process status with validation.
        
        Args:
            process_id: Process identifier
            update_request: Status update details
        
        Returns:
            Updated process status
        
        Raises:
            ValueError: If status transition is invalid
        
        Since:
            Version 1.0.0
        """
        # Get current tracking record
        stmt = select(ProcessTracking).where(ProcessTracking.id == process_id)
        result = await self.db.execute(stmt)
        tracking = result.scalar_one_or_none()
        
        if not tracking:
            raise ValueError(f"Process {process_id} not found")
        
        # Validate state transition
        current_status = ProcessingStatus(tracking.current_status)
        new_status = update_request.status
        
        if new_status not in self.VALID_TRANSITIONS.get(current_status, []):
            raise ValueError(
                f"Invalid status transition from {current_status} to {new_status}"
            )
        
        # Update stage timestamps
        now = datetime.utcnow()
        stage_field_map = {
            ProcessingStatus.COLLECTING: ("collecting_started_at", "collecting_completed_at"),
            ProcessingStatus.VERIFYING: ("verifying_started_at", "verifying_completed_at"),
            ProcessingStatus.MERGING: ("merging_started_at", "merging_completed_at"),
            ProcessingStatus.SUMMARIZING: ("summarizing_started_at", "summarizing_completed_at"),
            ProcessingStatus.COMPLETED: (None, "completed_at"),
            ProcessingStatus.FAILED: (None, "failed_at")
        }
        
        # Set completion time for previous stage
        if current_status in stage_field_map:
            _, completed_field = stage_field_map[current_status]
            if completed_field:
                setattr(tracking, completed_field, now)
        
        # Set start time for new stage
        if new_status in stage_field_map:
            started_field, _ = stage_field_map[new_status]
            if started_field:
                setattr(tracking, started_field, now)
        
        # Update tracking record
        tracking.current_status = new_status.value
        tracking.progress_percentage = update_request.progress_percentage
        tracking.current_stage_start = now
        tracking.updated_at = now
        
        if update_request.error_details:
            tracking.error_details = update_request.error_details
        
        if update_request.categories_completed is not None:
            tracking.categories_completed = update_request.categories_completed
        
        if update_request.estimated_completion:
            tracking.estimated_completion = update_request.estimated_completion
        else:
            # Calculate estimated completion
            tracking.estimated_completion = await self._calculate_estimated_completion(
                tracking
            )
        
        await self.db.commit()
        
        # Log status change to audit trail
        await self._log_status_change(
            process_id,
            current_status,
            new_status,
            update_request.message
        )
        
        logger.info(
            "Process status updated",
            process_id=process_id,
            old_status=current_status.value,
            new_status=new_status.value,
            progress=update_request.progress_percentage
        )
        
        # Return updated status
        return await self.get_status(process_id)
    
    async def get_status(self, process_id: str) -> ProcessStatusResponse:
        """
        Get current process status.
        
        Args:
            process_id: Process identifier
        
        Returns:
            Current process status
        
        Since:
            Version 1.0.0
        """
        # Get tracking record
        stmt = select(ProcessTracking).where(ProcessTracking.id == process_id)
        result = await self.db.execute(stmt)
        tracking = result.scalar_one_or_none()
        
        if not tracking:
            raise ValueError(f"Process {process_id} not found")
        
        # Calculate processing duration
        duration = self._calculate_duration(
            tracking.submitted_at,
            tracking.completed_at or datetime.utcnow()
        )
        
        # Build audit summary
        audit_summary = AuditSummary(
            total_stages_completed=self._count_completed_stages(tracking),
            current_stage_start_time=tracking.current_stage_start,
            processing_duration=duration,
            categories_completed=tracking.categories_completed or 0,
            categories_total=tracking.categories_total or 17,
            last_activity=tracking.updated_at or tracking.submitted_at
        )
        
        # Build response
        return ProcessStatusResponse(
            process_id=tracking.id,
            request_id=tracking.request_id,
            current_stage=ProcessingStatus(tracking.current_status),
            progress_percentage=tracking.progress_percentage,
            estimated_completion=tracking.estimated_completion,
            error_details=tracking.error_details,
            audit_summary=audit_summary,
            drug_names=tracking.drug_names or [],
            created_at=tracking.submitted_at,
            updated_at=tracking.updated_at or tracking.submitted_at
        )
    
    async def get_process_history(
        self,
        process_id: str
    ) -> List[ProcessHistoryEntry]:
        """
        Get process status history.
        
        Args:
            process_id: Process identifier
        
        Returns:
            List of history entries
        
        Since:
            Version 1.0.0
        """
        # Get tracking record
        stmt = select(ProcessTracking).where(ProcessTracking.id == process_id)
        result = await self.db.execute(stmt)
        tracking = result.scalar_one_or_none()
        
        if not tracking:
            raise ValueError(f"Process {process_id} not found")
        
        history = []
        
        # Build history from stage timestamps
        stages = [
            (ProcessingStatus.SUBMITTED, tracking.submitted_at, None),
            (ProcessingStatus.COLLECTING, tracking.collecting_started_at,
             tracking.collecting_completed_at),
            (ProcessingStatus.VERIFYING, tracking.verifying_started_at,
             tracking.verifying_completed_at),
            (ProcessingStatus.MERGING, tracking.merging_started_at,
             tracking.merging_completed_at),
            (ProcessingStatus.SUMMARIZING, tracking.summarizing_started_at,
             tracking.summarizing_completed_at),
            (ProcessingStatus.COMPLETED, tracking.completed_at, None),
            (ProcessingStatus.FAILED, tracking.failed_at, None)
        ]
        
        for status, started_at, completed_at in stages:
            if started_at:
                # Calculate duration in stage
                duration = None
                if completed_at:
                    duration = self._calculate_duration(started_at, completed_at)
                elif tracking.current_status == status.value:
                    duration = self._calculate_duration(
                        started_at,
                        datetime.utcnow()
                    )
                
                history.append(
                    ProcessHistoryEntry(
                        timestamp=started_at,
                        status=status,
                        progress_percentage=self.STAGE_PROGRESS.get(status, 0) or 0,
                        duration_in_stage=duration,
                        message=f"Entered {status.value} stage"
                    )
                )
        
        # Sort by timestamp
        history.sort(key=lambda x: x.timestamp)
        
        return history
    
    async def get_bulk_status(
        self,
        process_ids: List[str]
    ) -> List[ProcessStatusResponse]:
        """
        Get status for multiple processes.
        
        Args:
            process_ids: List of process identifiers
        
        Returns:
            List of process statuses
        
        Since:
            Version 1.0.0
        """
        # Query all processes at once
        stmt = select(ProcessTracking).where(
            ProcessTracking.id.in_(process_ids)
        )
        result = await self.db.execute(stmt)
        trackings = result.scalars().all()
        
        # Build status responses
        statuses = []
        for tracking in trackings:
            try:
                status = await self.get_status(tracking.id)
                statuses.append(status)
            except Exception as e:
                logger.error(
                    "Failed to get status for process",
                    process_id=tracking.id,
                    error=str(e)
                )
        
        return statuses
    
    async def calculate_progress(
        self,
        process_id: str,
        categories_completed: int
    ) -> int:
        """
        Calculate progress percentage based on current stage.
        
        Args:
            process_id: Process identifier
            categories_completed: Number of categories completed
        
        Returns:
            Progress percentage (0-100)
        
        Since:
            Version 1.0.0
        """
        # Get current tracking
        stmt = select(ProcessTracking).where(ProcessTracking.id == process_id)
        result = await self.db.execute(stmt)
        tracking = result.scalar_one_or_none()
        
        if not tracking:
            return 0
        
        status = ProcessingStatus(tracking.current_status)
        base_progress = self.STAGE_PROGRESS.get(status, 0)
        
        if base_progress is None:
            return tracking.progress_percentage
        
        # Calculate stage-specific progress
        if status == ProcessingStatus.COLLECTING:
            # 20% base + up to 60% for category completion
            category_progress = (categories_completed / tracking.categories_total) * 60
            return min(80, base_progress + int(category_progress))
        
        elif status == ProcessingStatus.VERIFYING:
            # 80% base + up to 10% for verification
            verification_progress = (
                categories_completed / tracking.categories_total
            ) * 10
            return min(90, base_progress + int(verification_progress))
        
        elif status == ProcessingStatus.MERGING:
            # 90% base + up to 5% for merging
            merge_progress = (categories_completed / tracking.categories_total) * 5
            return min(95, base_progress + int(merge_progress))
        
        elif status == ProcessingStatus.SUMMARIZING:
            # 95% base + up to 4% for summarization
            summary_progress = (
                categories_completed / tracking.categories_total
            ) * 4
            return min(99, base_progress + int(summary_progress))
        
        return base_progress
    
    async def _calculate_estimated_completion(
        self,
        tracking: ProcessTracking
    ) -> Optional[datetime]:
        """
        Calculate estimated completion time.
        
        Args:
            tracking: Process tracking record
        
        Returns:
            Estimated completion timestamp
        
        Since:
            Version 1.0.0
        """
        # Average processing times per stage (in minutes)
        avg_stage_times = {
            ProcessingStatus.COLLECTING: 2.0,
            ProcessingStatus.VERIFYING: 1.0,
            ProcessingStatus.MERGING: 0.5,
            ProcessingStatus.SUMMARIZING: 0.5
        }
        
        current_status = ProcessingStatus(tracking.current_status)
        
        # If already completed or failed
        if current_status in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED
        ]:
            return None
        
        # Calculate remaining time
        remaining_minutes = 0.0
        found_current = False
        
        for status, avg_time in avg_stage_times.items():
            if status == current_status:
                found_current = True
                # Add remaining time for current stage
                if tracking.current_stage_start:
                    elapsed = (
                        datetime.utcnow() - tracking.current_stage_start
                    ).total_seconds() / 60
                    remaining_minutes += max(0, avg_time - elapsed)
            elif found_current:
                # Add full time for future stages
                remaining_minutes += avg_time
        
        # Adjust for number of drugs
        drug_multiplier = len(tracking.drug_names) if tracking.drug_names else 1
        remaining_minutes *= (1 + (drug_multiplier - 1) * 0.5)
        
        # Add buffer for system load
        remaining_minutes *= 1.2
        
        return datetime.utcnow() + timedelta(minutes=remaining_minutes)
    
    def _calculate_duration(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """
        Calculate duration in HH:MM:SS format.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
        
        Returns:
            Duration string
        
        Since:
            Version 1.0.0
        """
        duration = end_time - start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    def _count_completed_stages(self, tracking: ProcessTracking) -> int:
        """
        Count number of completed processing stages.
        
        Args:
            tracking: Process tracking record
        
        Returns:
            Number of completed stages
        
        Since:
            Version 1.0.0
        """
        count = 0
        
        if tracking.collecting_completed_at:
            count += 1
        if tracking.verifying_completed_at:
            count += 1
        if tracking.merging_completed_at:
            count += 1
        if tracking.summarizing_completed_at:
            count += 1
        if tracking.completed_at:
            count += 1
        
        return count
    
    async def _log_status_change(
        self,
        process_id: str,
        old_status: ProcessingStatus,
        new_status: ProcessingStatus,
        message: Optional[str] = None
    ) -> None:
        """
        Log status change to audit trail.
        
        Args:
            process_id: Process identifier
            old_status: Previous status
            new_status: New status
            message: Optional status change message
        
        Since:
            Version 1.0.0
        """
        # TODO: Implement audit logging
        # This will integrate with the audit system from Story 1.2
        logger.info(
            "Status change logged",
            process_id=process_id,
            old_status=old_status.value,
            new_status=new_status.value,
            message=message,
            correlation_id=self.correlation_id
        )