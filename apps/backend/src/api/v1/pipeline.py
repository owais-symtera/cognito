"""
API endpoints for pipeline orchestration and management.

Provides endpoints for executing and monitoring the 4-stage pharmaceutical
intelligence processing pipeline.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ...database.session import get_db, get_redis
from ...core.pipeline_orchestration import (
    PipelineOrchestrator,
    PipelineContext,
    PipelineStage
)
from ...core.pipeline_stages import (
    CollectionStageHandler,
    VerificationStageHandler,
    MergingStageHandler,
    SummaryStageHandler
)
from ...core.message_queue import MessageQueueService
from ...integrations.api_manager import MultiAPIManager
from ...core.source_priority import SourceClassifier, SourceReliabilityScorer
from ...config.logging import PharmaceuticalLogger

router = APIRouter(prefix="/pipeline", tags=["Pipeline Orchestration"])
logger = PharmaceuticalLogger(service_name="pipeline_api")


class PipelineExecutionRequest(BaseModel):
    """Request to execute pipeline."""
    process_id: str = Field(..., description="Process tracking ID")
    request_id: str = Field(..., description="Drug request ID")
    correlation_id: str = Field(..., description="Correlation ID")
    pharmaceutical_compound: str = Field(..., description="Drug compound")
    category: str = Field(..., description="Pharmaceutical category")
    query: str = Field(..., description="Search query")
    async_execution: bool = Field(False, description="Execute asynchronously")


class StageRetryRequest(BaseModel):
    """Request to retry a stage."""
    process_id: str = Field(..., description="Process ID")
    stage: str = Field(..., description="Stage name to retry")


@router.post("/execute")
async def execute_pipeline(
    request: PipelineExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Execute the complete 4-stage pharmaceutical intelligence pipeline.

    Stages:
    1. Collection - Multi-API data gathering
    2. Verification - Source authenticity validation
    3. Merging - Conflict resolution and consolidation
    4. Summary - Final intelligence synthesis
    """
    try:
        # Initialize components
        api_manager = MultiAPIManager(db, redis_client, logger)
        orchestrator = PipelineOrchestrator(logger, db_session=db)

        # Register stage handlers
        orchestrator.register_stage_handler(
            PipelineStage.COLLECTION,
            CollectionStageHandler(api_manager, logger).execute
        )

        orchestrator.register_stage_handler(
            PipelineStage.VERIFICATION,
            VerificationStageHandler(
                SourceClassifier(),
                SourceReliabilityScorer(),
                logger
            ).execute
        )

        orchestrator.register_stage_handler(
            PipelineStage.MERGING,
            MergingStageHandler(logger).execute
        )

        orchestrator.register_stage_handler(
            PipelineStage.SUMMARY,
            SummaryStageHandler(logger).execute
        )

        # Create pipeline context
        context = PipelineContext(
            process_id=request.process_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            pharmaceutical_compound=request.pharmaceutical_compound,
            category=request.category,
            query=request.query
        )

        if request.async_execution:
            # Execute asynchronously
            background_tasks.add_task(
                orchestrator.execute_pipeline,
                context
            )

            return {
                'status': 'started',
                'process_id': request.process_id,
                'message': 'Pipeline execution started in background'
            }
        else:
            # Execute synchronously
            result = await orchestrator.execute_pipeline(context)

            return {
                'status': 'completed',
                'process_id': request.process_id,
                'result': result
            }

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.get("/status/{process_id}")
async def get_pipeline_status(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get current status of a pipeline execution."""
    try:
        orchestrator = PipelineOrchestrator(logger, db_session=db)
        status_info = await orchestrator.get_pipeline_status(process_id)

        if not status_info:
            # Check database for completed pipeline
            from ...database.models import ProcessTracking
            from sqlalchemy import select

            query = select(ProcessTracking).where(
                ProcessTracking.id == process_id
            )
            result = await db.execute(query)
            process = result.scalar_one_or_none()

            if process:
                return {
                    'process_id': process_id,
                    'status': process.status,
                    'last_stage': process.last_stage,
                    'metadata': process.metadata
                }

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline {process_id} not found"
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pipeline status"
        )


@router.get("/dead-letter-queue")
async def get_dead_letter_queue(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get failed pipeline requests from dead letter queue."""
    try:
        orchestrator = PipelineOrchestrator(logger, db_session=db)
        dlq = await orchestrator.get_dead_letter_queue()

        return dlq

    except Exception as e:
        logger.error(f"Failed to get DLQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dead letter queue"
        )


@router.post("/retry-dlq/{process_id}")
async def retry_from_dead_letter(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Retry a failed pipeline from dead letter queue."""
    try:
        orchestrator = PipelineOrchestrator(logger, db_session=db)
        success = await orchestrator.retry_dead_letter(process_id)

        if success:
            return {
                'status': 'success',
                'message': f'Pipeline {process_id} requeued for retry'
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline {process_id} not found in DLQ"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry from DLQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry from DLQ"
        )


@router.get("/metrics/performance")
async def get_pipeline_performance_metrics(
    lookback_hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get pipeline performance metrics."""
    try:
        from datetime import timedelta
        from sqlalchemy import select, func, and_

        from ...database.models import ProcessTracking

        start_time = datetime.utcnow() - timedelta(hours=lookback_hours)

        # Query for pipeline metrics
        query = select(
            func.count(ProcessTracking.id).label('total_pipelines'),
            func.avg(
                func.extract(
                    'epoch',
                    ProcessTracking.updated_at - ProcessTracking.created_at
                )
            ).label('avg_duration_seconds')
        ).where(
            ProcessTracking.created_at >= start_time
        )

        result = await db.execute(query)
        metrics = result.one()

        # Count by status
        status_query = select(
            ProcessTracking.status,
            func.count(ProcessTracking.id)
        ).where(
            ProcessTracking.created_at >= start_time
        ).group_by(ProcessTracking.status)

        status_result = await db.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result}

        return {
            'period_hours': lookback_hours,
            'total_pipelines': metrics.total_pipelines or 0,
            'avg_duration_seconds': float(metrics.avg_duration_seconds or 0),
            'status_distribution': status_counts,
            'success_rate': status_counts.get('completed', 0) / max(metrics.total_pipelines, 1)
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance metrics"
        )