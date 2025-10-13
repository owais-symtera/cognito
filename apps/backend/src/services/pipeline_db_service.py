"""
Pipeline service with PostgreSQL database storage.

This service replaces the in-memory pipeline storage with proper PostgreSQL persistence
using the process_tracking table.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import text
import structlog

from ..database.connection import get_engine, get_db_session
from .audit_service import AuditService

logger = structlog.get_logger(__name__)


class PipelineDatabaseService:
    """Service for managing drug analysis pipelines with PostgreSQL storage."""

    def __init__(self):
        """Initialize pipeline database service."""
        self.engine = None

    def _ensure_engine(self):
        """Ensure database engine is initialized."""
        if self.engine is None:
            self.engine = get_engine()

    async def create_pipeline(
        self,
        request_id: str,
        drug_name: str,
        total_categories: int = 17
    ) -> Dict[str, Any]:
        """
        Create a new processing pipeline in PostgreSQL.

        Args:
            request_id: Request ID to associate with pipeline
            drug_name: Name of the drug being processed
            total_categories: Total number of categories to process

        Returns:
            Created pipeline data
        """
        self._ensure_engine()

        pipeline_id = f"pipe-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        pipeline_data = {
            "id": pipeline_id,
            "requestId": request_id,
            "drugName": drug_name,
            "status": "submitted",
            "progressPercentage": 0,
            "totalCategories": total_categories,
            "completedCategories": 0,
            "submittedAt": now.isoformat(),
            "currentStage": "submitted"
        }

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO process_tracking (
                        id, request_id, current_status, progress_percentage,
                        drug_names, categories_total, categories_completed,
                        submitted_at, current_stage_start, process_metadata
                    )
                    VALUES (
                        :id, :request_id, :status, :progress,
                        :drugs, :total, :completed,
                        :submitted, :stage_start, :metadata
                    )
                """), {
                    "id": pipeline_id,
                    "request_id": request_id,
                    "status": "submitted",
                    "progress": 0,
                    "drugs": [drug_name],
                    "total": total_categories,
                    "completed": 0,
                    "submitted": now,
                    "stage_start": now,
                    "metadata": json.dumps({
                        "drug_name": drug_name,
                        "pipeline_version": "2.0"
                    })
                })

                await session.commit()
                logger.info(
                    "Pipeline created in database",
                    pipeline_id=pipeline_id,
                    request_id=request_id,
                    drug_name=drug_name
                )

                break

            # Log audit event
            await AuditService.log_event(
                event_type="pipeline_created",
                entity_type="process_tracking",
                entity_id=pipeline_id,
                request_id=request_id,
                audit_metadata={
                    "drug_name": drug_name,
                    "total_categories": total_categories
                }
            )

            return pipeline_data

        except Exception as e:
            logger.error(
                "Failed to create pipeline in database",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            raise

    async def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pipeline by ID."""
        self._ensure_engine()

        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        id, request_id, current_status, progress_percentage,
                        drug_names, categories_total, categories_completed,
                        submitted_at, collecting_started_at, collecting_completed_at,
                        verifying_started_at, verifying_completed_at,
                        merging_started_at, merging_completed_at,
                        summarizing_started_at, summarizing_completed_at,
                        completed_at, failed_at, error_details, process_metadata
                    FROM process_tracking
                    WHERE id = :id
                """), {"id": pipeline_id})

                row = result.fetchone()
                break

            if not row:
                return None

            metadata = json.loads(row[19]) if row[19] else {}

            return {
                "id": row[0],
                "requestId": row[1],
                "status": row[2],
                "progressPercentage": row[3],
                "drugName": row[4][0] if row[4] else None,
                "totalCategories": row[5],
                "completedCategories": row[6],
                "submittedAt": row[7].isoformat() if row[7] else None,
                "stages": {
                    "collecting": {
                        "startedAt": row[8].isoformat() if row[8] else None,
                        "completedAt": row[9].isoformat() if row[9] else None,
                        "status": "completed" if row[9] else ("running" if row[8] else "pending")
                    },
                    "verifying": {
                        "startedAt": row[10].isoformat() if row[10] else None,
                        "completedAt": row[11].isoformat() if row[11] else None,
                        "status": "completed" if row[11] else ("running" if row[10] else "pending")
                    },
                    "merging": {
                        "startedAt": row[12].isoformat() if row[12] else None,
                        "completedAt": row[13].isoformat() if row[13] else None,
                        "status": "completed" if row[13] else ("running" if row[12] else "pending")
                    },
                    "summarizing": {
                        "startedAt": row[14].isoformat() if row[14] else None,
                        "completedAt": row[15].isoformat() if row[15] else None,
                        "status": "completed" if row[15] else ("running" if row[14] else "pending")
                    }
                },
                "completedAt": row[16].isoformat() if row[16] else None,
                "failedAt": row[17].isoformat() if row[17] else None,
                "errorDetails": row[18],
                "metadata": metadata
            }

        except Exception as e:
            logger.error(
                "Failed to get pipeline from database",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            return None

    async def update_pipeline_stage(
        self,
        pipeline_id: str,
        stage: str,
        status: str,
        progress_percentage: Optional[int] = None
    ) -> bool:
        """
        Update pipeline stage.

        Args:
            pipeline_id: Pipeline ID
            stage: Stage name ('collecting', 'verifying', 'merging', 'summarizing')
            status: Stage status ('started', 'completed', 'failed')
            progress_percentage: Optional overall progress percentage

        Returns:
            True if successful
        """
        self._ensure_engine()

        try:
            now = datetime.utcnow()
            update_fields = []
            params = {"id": pipeline_id, "now": now}

            # Update stage timestamps
            if status == "started":
                update_fields.append(f"{stage}_started_at = :now")
                update_fields.append(f"current_status = :{stage}")
                params[stage] = stage
            elif status == "completed":
                update_fields.append(f"{stage}_completed_at = :now")

            # Update progress
            if progress_percentage is not None:
                update_fields.append("progress_percentage = :progress")
                params["progress"] = progress_percentage

            update_fields.append("updated_at = :now")

            if not update_fields:
                return True

            async for session in get_db_session():
                query = f"""
                    UPDATE process_tracking
                    SET {', '.join(update_fields)}
                    WHERE id = :id
                """

                await session.execute(text(query), params)
                await session.commit()

                logger.info(
                    "Pipeline stage updated",
                    pipeline_id=pipeline_id,
                    stage=stage,
                    status=status
                )

                break

            # Log audit event
            await AuditService.log_event(
                event_type=f"pipeline_stage_{status}",
                entity_type="process_tracking",
                entity_id=pipeline_id,
                audit_metadata={
                    "stage": stage,
                    "status": status,
                    "progress": progress_percentage
                }
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to update pipeline stage",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            return False

    async def update_category_progress(
        self,
        pipeline_id: str,
        completed_count: int
    ) -> bool:
        """
        Update category completion progress.

        Args:
            pipeline_id: Pipeline ID
            completed_count: Number of categories completed

        Returns:
            True if successful
        """
        self._ensure_engine()

        try:
            async for session in get_db_session():
                # Get total categories first
                result = await session.execute(text("""
                    SELECT categories_total FROM process_tracking WHERE id = :id
                """), {"id": pipeline_id})

                row = result.fetchone()
                if not row:
                    return False

                total = row[0]
                progress = int((completed_count / total) * 100) if total > 0 else 0

                # Update completed count and progress
                await session.execute(text("""
                    UPDATE process_tracking
                    SET categories_completed = :completed,
                        progress_percentage = :progress,
                        updated_at = :now
                    WHERE id = :id
                """), {
                    "id": pipeline_id,
                    "completed": completed_count,
                    "progress": progress,
                    "now": datetime.utcnow()
                })

                await session.commit()

                logger.info(
                    "Pipeline category progress updated",
                    pipeline_id=pipeline_id,
                    completed=completed_count,
                    total=total,
                    progress=progress
                )

                break

            return True

        except Exception as e:
            logger.error(
                "Failed to update category progress",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            return False

    async def complete_pipeline(
        self,
        pipeline_id: str
    ) -> bool:
        """Mark pipeline as completed."""
        self._ensure_engine()

        try:
            now = datetime.utcnow()

            async for session in get_db_session():
                await session.execute(text("""
                    UPDATE process_tracking
                    SET current_status = 'completed',
                        progress_percentage = 100,
                        completed_at = :now,
                        updated_at = :now
                    WHERE id = :id
                """), {
                    "id": pipeline_id,
                    "now": now
                })

                await session.commit()

                logger.info("Pipeline completed", pipeline_id=pipeline_id)
                break

            # Log audit event
            await AuditService.log_event(
                event_type="pipeline_completed",
                entity_type="process_tracking",
                entity_id=pipeline_id,
                audit_metadata={"completed_at": now.isoformat()}
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to complete pipeline",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            return False

    async def fail_pipeline(
        self,
        pipeline_id: str,
        error_message: str
    ) -> bool:
        """Mark pipeline as failed."""
        self._ensure_engine()

        try:
            now = datetime.utcnow()

            async for session in get_db_session():
                await session.execute(text("""
                    UPDATE process_tracking
                    SET current_status = 'failed',
                        failed_at = :now,
                        error_details = :error,
                        updated_at = :now
                    WHERE id = :id
                """), {
                    "id": pipeline_id,
                    "now": now,
                    "error": error_message
                })

                await session.commit()

                logger.error(
                    "Pipeline failed",
                    pipeline_id=pipeline_id,
                    error=error_message
                )

                break

            # Log audit event
            await AuditService.log_event(
                event_type="pipeline_failed",
                entity_type="process_tracking",
                entity_id=pipeline_id,
                audit_metadata={
                    "error_message": error_message,
                    "failed_at": now.isoformat()
                }
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to mark pipeline as failed",
                pipeline_id=pipeline_id,
                error=str(e)
            )
            return False

    async def get_all_pipelines(self) -> List[Dict[str, Any]]:
        """Get all pipelines."""
        self._ensure_engine()

        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        id, request_id, current_status, progress_percentage,
                        drug_names, categories_total, categories_completed,
                        submitted_at, completed_at
                    FROM process_tracking
                    ORDER BY submitted_at DESC
                """))

                rows = result.fetchall()
                break

            pipelines = []
            for row in rows:
                pipelines.append({
                    "id": row[0],
                    "requestId": row[1],
                    "status": row[2],
                    "progressPercentage": row[3],
                    "drugName": row[4][0] if row[4] else None,
                    "totalCategories": row[5],
                    "completedCategories": row[6],
                    "submittedAt": row[7].isoformat() if row[7] else None,
                    "completedAt": row[8].isoformat() if row[8] else None
                })

            return pipelines

        except Exception as e:
            logger.error("Failed to get all pipelines", error=str(e))
            return []

    async def get_pipeline_by_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline by request ID."""
        self._ensure_engine()

        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT id FROM process_tracking WHERE request_id = :request_id
                    ORDER BY submitted_at DESC LIMIT 1
                """), {"request_id": request_id})

                row = result.fetchone()
                break

            if not row:
                return None

            return await self.get_pipeline(row[0])

        except Exception as e:
            logger.error(
                "Failed to get pipeline by request",
                request_id=request_id,
                error=str(e)
            )
            return None