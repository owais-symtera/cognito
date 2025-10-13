"""
Pipeline orchestration and stage management for pharmaceutical intelligence.

Implements 4-stage pipeline (Collection → Verification → Merging → Summary)
with complete audit integration and failure recovery.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
import json
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import uuid4
import structlog

from ..config.logging import PharmaceuticalLogger
from ..database.models import ProcessTracking

logger = structlog.get_logger(__name__)


class PipelineStage(IntEnum):
    """
    Pipeline stages for pharmaceutical intelligence processing.

    Since:
        Version 1.0.0
    """
    COLLECTION = 1      # Multi-API data gathering
    VERIFICATION = 2    # Source authenticity validation
    MERGING = 3        # Conflict resolution and consolidation
    SUMMARY = 4        # Final intelligence synthesis
    COMPLETE = 5       # Pipeline complete


class StageStatus(Enum):
    """
    Stage execution status.

    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """
    Result from a pipeline stage execution.

    Since:
        Version 1.0.0
    """
    stage: PipelineStage
    status: StageStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """
    Context passed through pipeline stages.

    Since:
        Version 1.0.0
    """
    process_id: str
    request_id: str
    correlation_id: str
    pharmaceutical_compound: str
    category: str
    query: str
    stage_results: Dict[PipelineStage, StageResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class PipelineOrchestrator:
    """
    Orchestrates pharmaceutical intelligence pipeline execution.

    Manages stage transitions, failure recovery, and audit integration
    for regulatory compliance.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        audit_logger: PharmaceuticalLogger,
        message_queue=None,
        db_session=None,
        max_retries: int = 3,
        retry_delay_seconds: int = 30
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            audit_logger: Pharmaceutical audit logger
            message_queue: Message queue for stage transitions
            db_session: Database session for persistence
            max_retries: Maximum retries per stage
            retry_delay_seconds: Delay between retries

        Since:
            Version 1.0.0
        """
        self.audit_logger = audit_logger
        self.message_queue = message_queue
        self.db = db_session
        self.max_retries = max_retries
        self.retry_delay = timedelta(seconds=retry_delay_seconds)
        self.stage_handlers: Dict[PipelineStage, Callable] = {}
        self.dead_letter_queue = []
        self._running_pipelines = {}

    def register_stage_handler(
        self,
        stage: PipelineStage,
        handler: Callable
    ):
        """
        Register a handler for a pipeline stage.

        Args:
            stage: Pipeline stage
            handler: Async function to handle stage

        Since:
            Version 1.0.0
        """
        self.stage_handlers[stage] = handler
        logger.info(f"Registered handler for stage {stage.name}")

    async def execute_pipeline(
        self,
        context: PipelineContext
    ) -> Dict[str, Any]:
        """
        Execute the complete pipeline for a request.

        Args:
            context: Pipeline execution context

        Returns:
            Pipeline execution results

        Since:
            Version 1.0.0
        """
        pipeline_start = datetime.utcnow()

        # Track running pipeline
        self._running_pipelines[context.process_id] = context

        try:
            # Log pipeline start
            await self._log_pipeline_event(
                context,
                "pipeline_started",
                {"stages": len(PipelineStage) - 1}  # Exclude COMPLETE
            )

            # Execute stages in order
            for stage in [
                PipelineStage.COLLECTION,
                PipelineStage.VERIFICATION,
                PipelineStage.MERGING,
                PipelineStage.SUMMARY
            ]:
                # Check if stage should be skipped
                if self._should_skip_stage(stage, context):
                    await self._log_stage_skip(stage, context)
                    continue

                # Execute stage with retry logic
                stage_result = await self._execute_stage_with_retry(
                    stage,
                    context
                )

                # Store stage result
                context.stage_results[stage] = stage_result

                # Check for stage failure
                if stage_result.status == StageStatus.FAILED:
                    await self._handle_pipeline_failure(context, stage)
                    break

                # Transition to next stage via message queue
                if self.message_queue:
                    await self._queue_stage_transition(context, stage)

            # Mark pipeline complete
            pipeline_end = datetime.utcnow()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()

            # Generate pipeline summary
            summary = self._generate_pipeline_summary(context, pipeline_duration)

            # Log pipeline completion
            await self._log_pipeline_event(
                context,
                "pipeline_completed",
                summary
            )

            # Update process tracking
            if self.db:
                await self._update_process_tracking(
                    context,
                    "completed",
                    summary
                )

            return summary

        except Exception as e:
            logger.error(
                f"Pipeline execution failed",
                process_id=context.process_id,
                error=str(e)
            )
            await self._handle_pipeline_failure(context, None, str(e))
            raise

        finally:
            # Clean up running pipeline
            self._running_pipelines.pop(context.process_id, None)

    async def _execute_stage_with_retry(
        self,
        stage: PipelineStage,
        context: PipelineContext
    ) -> StageResult:
        """
        Execute a stage with retry logic.

        Args:
            stage: Pipeline stage to execute
            context: Pipeline context

        Returns:
            Stage execution result

        Since:
            Version 1.0.0
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                # Log stage start
                await self._log_stage_event(
                    stage,
                    context,
                    "stage_started",
                    {"retry_count": retry_count}
                )

                # Get stage handler
                handler = self.stage_handlers.get(stage)
                if not handler:
                    raise ValueError(f"No handler registered for stage {stage.name}")

                # Execute stage
                start_time = datetime.utcnow()

                stage_result = StageResult(
                    stage=stage,
                    status=StageStatus.IN_PROGRESS,
                    start_time=start_time,
                    retry_count=retry_count
                )

                # Execute handler
                result_data = await handler(context)

                # Update stage result
                stage_result.end_time = datetime.utcnow()
                stage_result.status = StageStatus.COMPLETED
                stage_result.data = result_data
                stage_result.metrics = self._calculate_stage_metrics(
                    stage_result
                )

                # Log stage completion
                await self._log_stage_event(
                    stage,
                    context,
                    "stage_completed",
                    stage_result.metrics
                )

                return stage_result

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                logger.warning(
                    f"Stage {stage.name} failed",
                    process_id=context.process_id,
                    retry_count=retry_count,
                    error=last_error
                )

                if retry_count <= self.max_retries:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay.total_seconds())

                    # Log retry attempt
                    await self._log_stage_event(
                        stage,
                        context,
                        "stage_retry",
                        {"retry_count": retry_count, "error": last_error}
                    )
                else:
                    # Max retries exceeded
                    stage_result = StageResult(
                        stage=stage,
                        status=StageStatus.FAILED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        errors=[last_error],
                        retry_count=retry_count
                    )

                    await self._log_stage_event(
                        stage,
                        context,
                        "stage_failed",
                        {"error": last_error, "retries": retry_count}
                    )

                    return stage_result

    def _should_skip_stage(
        self,
        stage: PipelineStage,
        context: PipelineContext
    ) -> bool:
        """
        Determine if a stage should be skipped.

        Args:
            stage: Pipeline stage
            context: Pipeline context

        Returns:
            True if stage should be skipped

        Since:
            Version 1.0.0
        """
        # Skip verification if no sources to verify
        if stage == PipelineStage.VERIFICATION:
            collection_result = context.stage_results.get(PipelineStage.COLLECTION)
            if not collection_result or not collection_result.data.get('sources'):
                return True

        # Skip merging if only one source
        if stage == PipelineStage.MERGING:
            collection_result = context.stage_results.get(PipelineStage.COLLECTION)
            if collection_result:
                source_count = len(collection_result.data.get('sources', []))
                if source_count <= 1:
                    return True

        return False

    async def _handle_pipeline_failure(
        self,
        context: PipelineContext,
        failed_stage: Optional[PipelineStage] = None,
        error: Optional[str] = None
    ):
        """
        Handle pipeline failure and send to dead letter queue.

        Args:
            context: Pipeline context
            failed_stage: Stage that failed
            error: Error message

        Since:
            Version 1.0.0
        """
        failure_data = {
            'process_id': context.process_id,
            'request_id': context.request_id,
            'failed_stage': failed_stage.name if failed_stage else 'UNKNOWN',
            'error': error,
            'timestamp': datetime.utcnow().isoformat(),
            'compound': context.pharmaceutical_compound,
            'category': context.category
        }

        # Add to dead letter queue
        self.dead_letter_queue.append(failure_data)

        # Log failure for compliance
        await self.audit_logger.log_error(
            "Pipeline failure",
            process_id=context.process_id,
            failed_stage=failed_stage.name if failed_stage else None,
            error=error,
            drug_names=[context.pharmaceutical_compound]
        )

        # Update process tracking
        if self.db:
            await self._update_process_tracking(
                context,
                "failed",
                failure_data
            )

    async def _queue_stage_transition(
        self,
        context: PipelineContext,
        completed_stage: PipelineStage
    ):
        """
        Queue transition to next stage via message queue.

        Args:
            context: Pipeline context
            completed_stage: Stage that was completed

        Since:
            Version 1.0.0
        """
        if not self.message_queue:
            return

        next_stage = PipelineStage(completed_stage + 1)

        if next_stage <= PipelineStage.SUMMARY:
            message = {
                'process_id': context.process_id,
                'next_stage': next_stage.name,
                'completed_stage': completed_stage.name,
                'timestamp': datetime.utcnow().isoformat()
            }

            await self.message_queue.publish(
                f"pipeline.stage.{next_stage.name.lower()}",
                json.dumps(message)
            )

    def _calculate_stage_metrics(
        self,
        stage_result: StageResult
    ) -> Dict[str, Any]:
        """
        Calculate metrics for a stage execution.

        Args:
            stage_result: Stage result

        Returns:
            Stage metrics

        Since:
            Version 1.0.0
        """
        if not stage_result.end_time:
            return {}

        duration = (stage_result.end_time - stage_result.start_time).total_seconds()

        metrics = {
            'duration_seconds': duration,
            'retry_count': stage_result.retry_count,
            'data_volume': len(json.dumps(stage_result.data)),
            'error_count': len(stage_result.errors)
        }

        # Add stage-specific metrics
        if stage_result.stage == PipelineStage.COLLECTION:
            metrics['sources_collected'] = len(
                stage_result.data.get('sources', [])
            )
            metrics['total_cost'] = stage_result.data.get('total_cost', 0)

        elif stage_result.stage == PipelineStage.VERIFICATION:
            metrics['sources_verified'] = stage_result.data.get('verified_count', 0)
            metrics['sources_rejected'] = stage_result.data.get('rejected_count', 0)

        elif stage_result.stage == PipelineStage.MERGING:
            metrics['conflicts_resolved'] = stage_result.data.get('conflicts_resolved', 0)
            metrics['data_points_merged'] = stage_result.data.get('data_points', 0)

        return metrics

    def _generate_pipeline_summary(
        self,
        context: PipelineContext,
        total_duration: float
    ) -> Dict[str, Any]:
        """
        Generate summary of pipeline execution.

        Args:
            context: Pipeline context
            total_duration: Total pipeline duration in seconds

        Returns:
            Pipeline summary

        Since:
            Version 1.0.0
        """
        summary = {
            'process_id': context.process_id,
            'request_id': context.request_id,
            'compound': context.pharmaceutical_compound,
            'category': context.category,
            'total_duration_seconds': total_duration,
            'stages_completed': len([
                s for s in context.stage_results.values()
                if s.status == StageStatus.COMPLETED
            ]),
            'stages_failed': len([
                s for s in context.stage_results.values()
                if s.status == StageStatus.FAILED
            ]),
            'stages_skipped': len([
                s for s in context.stage_results.values()
                if s.status == StageStatus.SKIPPED
            ])
        }

        # Add stage metrics
        stage_metrics = {}
        for stage, result in context.stage_results.items():
            stage_metrics[stage.name] = {
                'status': result.status.value,
                'duration': result.metrics.get('duration_seconds', 0),
                'retries': result.retry_count
            }

        summary['stage_metrics'] = stage_metrics

        # Calculate total cost
        total_cost = sum(
            r.data.get('total_cost', 0)
            for r in context.stage_results.values()
            if r.status == StageStatus.COMPLETED
        )
        summary['total_cost'] = total_cost

        return summary

    async def _log_pipeline_event(
        self,
        context: PipelineContext,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Log pipeline-level event for audit trail.

        Args:
            context: Pipeline context
            event: Event type
            data: Event data

        Since:
            Version 1.0.0
        """
        await self.audit_logger.log_system_event(
            event_type=f"pipeline.{event}",
            process_id=context.process_id,
            component="pipeline_orchestrator",
            details={
                **data,
                'compound': context.pharmaceutical_compound,
                'category': context.category
            }
        )

    async def _log_stage_event(
        self,
        stage: PipelineStage,
        context: PipelineContext,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Log stage-level event for audit trail.

        Args:
            stage: Pipeline stage
            context: Pipeline context
            event: Event type
            data: Event data

        Since:
            Version 1.0.0
        """
        await self.audit_logger.log_system_event(
            event_type=f"stage.{stage.name.lower()}.{event}",
            process_id=context.process_id,
            component=f"stage_{stage.name.lower()}",
            details=data
        )

    async def _log_stage_skip(
        self,
        stage: PipelineStage,
        context: PipelineContext
    ):
        """
        Log stage skip event.

        Args:
            stage: Skipped stage
            context: Pipeline context

        Since:
            Version 1.0.0
        """
        await self._log_stage_event(
            stage,
            context,
            "stage_skipped",
            {"reason": "Insufficient data for stage"}
        )

        # Create skipped result
        context.stage_results[stage] = StageResult(
            stage=stage,
            status=StageStatus.SKIPPED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )

    async def _update_process_tracking(
        self,
        context: PipelineContext,
        status: str,
        data: Dict[str, Any]
    ):
        """
        Update process tracking in database.

        Args:
            context: Pipeline context
            status: Process status
            data: Status data

        Since:
            Version 1.0.0
        """
        if not self.db:
            return

        from sqlalchemy import update

        stmt = update(ProcessTracking).where(
            ProcessTracking.id == context.process_id
        ).values(
            status=status,
            last_stage=data.get('last_completed_stage', 'unknown'),
            metadata=data,
            updated_at=datetime.utcnow()
        )

        await self.db.execute(stmt)
        await self.db.commit()

    async def get_pipeline_status(
        self,
        process_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current status of a running pipeline.

        Args:
            process_id: Process ID

        Returns:
            Pipeline status or None

        Since:
            Version 1.0.0
        """
        context = self._running_pipelines.get(process_id)

        if not context:
            return None

        current_stage = None
        for stage in context.stage_results.values():
            if stage.status == StageStatus.IN_PROGRESS:
                current_stage = stage.stage
                break

        return {
            'process_id': process_id,
            'current_stage': current_stage.name if current_stage else None,
            'stages_completed': len([
                s for s in context.stage_results.values()
                if s.status == StageStatus.COMPLETED
            ]),
            'running_time_seconds': (
                datetime.utcnow() - context.created_at
            ).total_seconds()
        }

    async def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """
        Get contents of dead letter queue.

        Returns:
            Failed pipeline requests

        Since:
            Version 1.0.0
        """
        return self.dead_letter_queue.copy()

    async def retry_dead_letter(
        self,
        process_id: str
    ) -> bool:
        """
        Retry a failed pipeline from dead letter queue.

        Args:
            process_id: Process ID to retry

        Returns:
            True if retry initiated

        Since:
            Version 1.0.0
        """
        # Find in dead letter queue
        for i, item in enumerate(self.dead_letter_queue):
            if item['process_id'] == process_id:
                # Remove from dead letter queue
                self.dead_letter_queue.pop(i)

                # Log retry attempt
                logger.info(
                    f"Retrying pipeline from dead letter queue",
                    process_id=process_id
                )

                # TODO: Reinitiate pipeline
                return True

        return False