"""
Tests for pipeline orchestration and stage management.

Validates 4-stage pipeline execution, retry logic, message queue integration,
and audit trail completeness.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.core.pipeline_orchestration import (
    PipelineOrchestrator,
    PipelineStage,
    StageStatus,
    StageResult,
    PipelineContext
)
from src.core.pipeline_stages import (
    CollectionStageHandler,
    VerificationStageHandler,
    MergingStageHandler,
    SummaryStageHandler
)


@pytest.fixture
async def mock_audit_logger():
    """Create mock audit logger."""
    logger = AsyncMock()
    logger.log_pipeline_event = AsyncMock()
    logger.log_stage_transition = AsyncMock()
    logger.log_error = AsyncMock()
    logger.log_system_event = AsyncMock()
    return logger


@pytest.fixture
async def mock_message_queue():
    """Create mock message queue."""
    queue = AsyncMock()
    queue.publish = AsyncMock()
    queue.subscribe = AsyncMock()
    queue.acknowledge = AsyncMock()
    queue.reject = AsyncMock()
    queue.send_to_dlq = AsyncMock()
    return queue


@pytest.fixture
async def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
async def pipeline_context():
    """Create sample pipeline context."""
    return PipelineContext(
        process_id="proc-123",
        request_id="req-456",
        correlation_id="corr-789",
        pharmaceutical_compound="Aspirin",
        category="NSAID",
        query="Aspirin side effects and interactions"
    )


@pytest.fixture
async def pipeline_orchestrator(
    mock_audit_logger,
    mock_message_queue,
    mock_db_session
):
    """Create pipeline orchestrator instance."""
    orchestrator = PipelineOrchestrator(
        audit_logger=mock_audit_logger,
        message_queue=mock_message_queue,
        db_session=mock_db_session,
        max_retries=3,
        retry_delay_seconds=1  # Short delay for testing
    )
    return orchestrator


class TestPipelineOrchestrator:
    """Tests for pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_stage_handler_registration(self, pipeline_orchestrator):
        """Test registering stage handlers."""
        handler = AsyncMock()
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION,
            handler
        )

        assert PipelineStage.COLLECTION in pipeline_orchestrator.stage_handlers
        assert pipeline_orchestrator.stage_handlers[PipelineStage.COLLECTION] == handler

    @pytest.mark.asyncio
    async def test_execute_pipeline_success(
        self,
        pipeline_orchestrator,
        pipeline_context,
        mock_audit_logger
    ):
        """Test successful pipeline execution through all stages."""
        # Create mock stage handlers
        collection_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'sources_found': 10, 'apis_queried': 3}
        ))

        verification_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.VERIFICATION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'verified_sources': 8, 'rejected_sources': 2}
        ))

        merging_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.MERGING,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'merged_count': 5, 'conflicts_resolved': 2}
        ))

        summary_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.SUMMARY,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'summary': 'Comprehensive pharmaceutical intelligence report'}
        ))

        # Register handlers
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, collection_handler
        )
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.VERIFICATION, verification_handler
        )
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.MERGING, merging_handler
        )
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.SUMMARY, summary_handler
        )

        # Execute pipeline
        result = await pipeline_orchestrator.execute_pipeline(pipeline_context)

        # Verify all stages executed
        assert result.status == StageStatus.COMPLETED
        assert len(pipeline_context.stage_results) == 4

        # Verify stage transitions logged
        assert mock_audit_logger.log_stage_transition.call_count >= 4

        # Verify handlers called with correct context
        collection_handler.assert_called_once_with(pipeline_context)
        verification_handler.assert_called_once()
        merging_handler.assert_called_once()
        summary_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage_retry_on_failure(
        self,
        pipeline_orchestrator,
        pipeline_context,
        mock_audit_logger
    ):
        """Test stage retry logic on failure."""
        # Create handler that fails twice then succeeds
        attempts = 0

        async def flaky_handler(context):
            nonlocal attempts
            attempts += 1

            if attempts < 3:
                return StageResult(
                    stage=PipelineStage.COLLECTION,
                    status=StageStatus.FAILED,
                    start_time=datetime.utcnow(),
                    errors=[f"Temporary failure {attempts}"]
                )

            return StageResult(
                stage=PipelineStage.COLLECTION,
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                data={'sources_found': 5}
            )

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, flaky_handler
        )

        # Execute stage with retries
        result = await pipeline_orchestrator._execute_stage(
            PipelineStage.COLLECTION,
            pipeline_context
        )

        # Verify retries occurred
        assert attempts == 3
        assert result.status == StageStatus.COMPLETED
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_stage_max_retries_exceeded(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test stage failure after max retries exceeded."""
        # Create handler that always fails
        failing_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            errors=["Permanent failure"]
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, failing_handler
        )

        # Execute stage
        result = await pipeline_orchestrator._execute_stage(
            PipelineStage.COLLECTION,
            pipeline_context
        )

        # Verify max retries reached
        assert result.status == StageStatus.FAILED
        assert result.retry_count == pipeline_orchestrator.max_retries
        assert failing_handler.call_count == pipeline_orchestrator.max_retries + 1

    @pytest.mark.asyncio
    async def test_skip_stage_logic(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test stage skipping logic (e.g., skip merging with single source)."""
        # Add collection result with single source
        pipeline_context.stage_results[PipelineStage.COLLECTION] = StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'sources_found': 1, 'single_source': True}
        )

        # Test skip condition
        should_skip = await pipeline_orchestrator._should_skip_stage(
            PipelineStage.MERGING,
            pipeline_context
        )

        assert should_skip is True

    @pytest.mark.asyncio
    async def test_dead_letter_queue_handling(
        self,
        pipeline_orchestrator,
        pipeline_context,
        mock_message_queue
    ):
        """Test dead letter queue handling for failed pipelines."""
        # Create handler that always fails
        failing_handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            errors=["Critical failure"]
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, failing_handler
        )

        # Execute pipeline
        result = await pipeline_orchestrator.execute_pipeline(pipeline_context)

        # Verify sent to DLQ
        assert result.status == StageStatus.FAILED
        assert len(pipeline_orchestrator.dead_letter_queue) == 1
        mock_message_queue.send_to_dlq.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_queue_stage_transitions(
        self,
        pipeline_orchestrator,
        pipeline_context,
        mock_message_queue
    ):
        """Test message queue publishes for stage transitions."""
        # Create simple handler
        handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'sources_found': 5}
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, handler
        )

        # Execute stage
        await pipeline_orchestrator._execute_stage(
            PipelineStage.COLLECTION,
            pipeline_context
        )

        # Verify message published for next stage
        mock_message_queue.publish.assert_called()
        call_args = mock_message_queue.publish.call_args
        assert 'verification' in call_args[0][0]  # routing key

    @pytest.mark.asyncio
    async def test_stage_metrics_collection(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test collection of stage performance metrics."""
        # Create handler with timing
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=5)

        handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            metrics={
                'api_calls': 3,
                'total_cost': 0.15,
                'sources_found': 10
            }
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, handler
        )

        # Execute stage
        result = await pipeline_orchestrator._execute_stage(
            PipelineStage.COLLECTION,
            pipeline_context
        )

        # Verify metrics collected
        assert result.metrics['api_calls'] == 3
        assert result.metrics['total_cost'] == 0.15
        assert (result.end_time - result.start_time).total_seconds() == 5

    @pytest.mark.asyncio
    async def test_pipeline_context_preservation(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test context data preserved across stages."""
        # Add metadata to context
        pipeline_context.metadata['custom_field'] = 'test_value'

        # Create handlers that modify context
        async def collection_handler(context):
            context.metadata['collection_data'] = 'collected'
            return StageResult(
                stage=PipelineStage.COLLECTION,
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )

        async def verification_handler(context):
            # Check previous stage data exists
            assert 'collection_data' in context.metadata
            context.metadata['verification_data'] = 'verified'
            return StageResult(
                stage=PipelineStage.VERIFICATION,
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, collection_handler
        )
        pipeline_orchestrator.register_stage_handler(
            PipelineStage.VERIFICATION, verification_handler
        )

        # Execute stages
        await pipeline_orchestrator._execute_stage(
            PipelineStage.COLLECTION, pipeline_context
        )
        await pipeline_orchestrator._execute_stage(
            PipelineStage.VERIFICATION, pipeline_context
        )

        # Verify context preserved
        assert pipeline_context.metadata['custom_field'] == 'test_value'
        assert pipeline_context.metadata['collection_data'] == 'collected'
        assert pipeline_context.metadata['verification_data'] == 'verified'

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(
        self,
        pipeline_orchestrator,
        pipeline_context,
        mock_audit_logger
    ):
        """Test complete audit trail for pipeline execution."""
        # Create handler
        handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={'sources_found': 5}
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, handler
        )

        # Execute pipeline
        await pipeline_orchestrator.execute_pipeline(pipeline_context)

        # Verify audit events logged
        mock_audit_logger.log_pipeline_event.assert_called()
        mock_audit_logger.log_stage_transition.assert_called()

        # Check audit log contains required fields
        pipeline_event_call = mock_audit_logger.log_pipeline_event.call_args
        assert pipeline_event_call.kwargs['process_id'] == 'proc-123'
        assert pipeline_event_call.kwargs['request_id'] == 'req-456'
        assert 'start_time' in pipeline_event_call.kwargs
        assert 'compound' in pipeline_event_call.kwargs

    @pytest.mark.asyncio
    async def test_get_pipeline_status(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test getting pipeline execution status."""
        # Add to running pipelines
        pipeline_orchestrator._running_pipelines[
            pipeline_context.process_id
        ] = pipeline_context

        # Add some stage results
        pipeline_context.stage_results[PipelineStage.COLLECTION] = StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )

        # Get status
        status = await pipeline_orchestrator.get_pipeline_status(
            pipeline_context.process_id
        )

        assert status is not None
        assert status['process_id'] == 'proc-123'
        assert status['current_stage'] == 'COLLECTION'
        assert status['stages_completed'] == 1
        assert status['is_running'] is True

    @pytest.mark.asyncio
    async def test_retry_from_dlq(
        self,
        pipeline_orchestrator,
        pipeline_context
    ):
        """Test retrying pipeline from dead letter queue."""
        # Add to DLQ
        pipeline_orchestrator.dead_letter_queue.append({
            'context': pipeline_context,
            'failure_reason': 'Temporary network error',
            'timestamp': datetime.utcnow()
        })

        # Mock successful handler for retry
        handler = AsyncMock(return_value=StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        ))

        pipeline_orchestrator.register_stage_handler(
            PipelineStage.COLLECTION, handler
        )

        # Retry from DLQ
        success = await pipeline_orchestrator.retry_from_dlq(
            pipeline_context.process_id
        )

        assert success is True
        assert len(pipeline_orchestrator.dead_letter_queue) == 0
        handler.assert_called_once()


class TestStageHandlers:
    """Tests for individual stage handlers."""

    @pytest.mark.asyncio
    async def test_collection_stage_handler(self, pipeline_context):
        """Test collection stage handler."""
        handler = CollectionStageHandler()

        # Mock dependencies
        with patch('src.core.pipeline_stages.MultiAPIManager') as mock_api_manager:
            mock_api_manager.return_value.search_with_all_strategies = AsyncMock(
                return_value={
                    'sources_found': 15,
                    'apis_queried': ['chatgpt', 'perplexity', 'gemini'],
                    'total_cost': 0.25
                }
            )

            result = await handler.execute(pipeline_context)

        assert result.stage == PipelineStage.COLLECTION
        assert result.status == StageStatus.COMPLETED
        assert result.data['sources_found'] == 15

    @pytest.mark.asyncio
    async def test_verification_stage_handler(self, pipeline_context):
        """Test verification stage handler."""
        # Add collection results to context
        pipeline_context.stage_results[PipelineStage.COLLECTION] = StageResult(
            stage=PipelineStage.COLLECTION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={
                'sources': [
                    {'url': 'https://fda.gov/drug', 'credibility': 0.98},
                    {'url': 'https://example.com', 'credibility': 0.45}
                ]
            }
        )

        handler = VerificationStageHandler()
        result = await handler.execute(pipeline_context)

        assert result.stage == PipelineStage.VERIFICATION
        assert result.status == StageStatus.COMPLETED
        assert 'verified_sources' in result.data

    @pytest.mark.asyncio
    async def test_merging_stage_handler(self, pipeline_context):
        """Test merging stage handler."""
        # Add verified results to context
        pipeline_context.stage_results[PipelineStage.VERIFICATION] = StageResult(
            stage=PipelineStage.VERIFICATION,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={
                'verified_sources': [
                    {'content': 'Data from source 1', 'priority': 2},
                    {'content': 'Data from source 2', 'priority': 1}
                ]
            }
        )

        handler = MergingStageHandler()
        result = await handler.execute(pipeline_context)

        assert result.stage == PipelineStage.MERGING
        assert result.status == StageStatus.COMPLETED
        assert 'merged_data' in result.data

    @pytest.mark.asyncio
    async def test_summary_stage_handler(self, pipeline_context):
        """Test summary stage handler."""
        # Add merged results to context
        pipeline_context.stage_results[PipelineStage.MERGING] = StageResult(
            stage=PipelineStage.MERGING,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={
                'merged_data': {
                    'side_effects': ['nausea', 'headache'],
                    'interactions': ['warfarin', 'alcohol'],
                    'dosage': '75-325mg daily'
                }
            }
        )

        handler = SummaryStageHandler()
        result = await handler.execute(pipeline_context)

        assert result.stage == PipelineStage.SUMMARY
        assert result.status == StageStatus.COMPLETED
        assert 'summary' in result.data