"""
Tests for collection status reporting and monitoring.

Validates real-time metrics, quality indicators, alerts, and
historical performance tracking.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import List

from src.core.collection_monitoring import (
    CollectionMonitor,
    CollectionMetrics,
    CollectionStatus,
    QualityIndicators,
    AlertSeverity
)


@pytest.fixture
async def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
async def mock_audit_logger():
    """Create mock audit logger."""
    logger = AsyncMock()
    logger.log_system_event = AsyncMock()
    logger.log_error = AsyncMock()
    return logger


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.lpush = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    redis.lrange = AsyncMock(return_value=[])
    return redis


@pytest.fixture
async def collection_monitor(mock_db, mock_audit_logger, mock_redis):
    """Create collection monitor instance."""
    return CollectionMonitor(
        mock_db,
        mock_audit_logger,
        mock_redis
    )


class TestCollectionMonitor:
    """Tests for collection monitoring functionality."""

    @pytest.mark.asyncio
    async def test_start_monitoring(self, collection_monitor):
        """Test starting collection monitoring."""
        metrics = await collection_monitor.start_collection_monitoring(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            total_categories=3
        )

        assert metrics.request_id == "req-123"
        assert metrics.process_id == "proc-456"
        assert metrics.category == "Oncology"
        assert metrics.status == CollectionStatus.IN_PROGRESS
        assert metrics.total_categories == 3
        assert metrics.completion_percentage == 0.0

        # Verify monitoring is active
        assert "proc-456" in collection_monitor.active_collections

    @pytest.mark.asyncio
    async def test_update_progress(self, collection_monitor):
        """Test updating collection progress."""
        # Start monitoring
        await collection_monitor.start_collection_monitoring(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            total_categories=2
        )

        # Update progress
        updated = await collection_monitor.update_collection_progress(
            "proc-456",
            {
                'apis_queried': {'chatgpt': 1, 'perplexity': 1},
                'sources_found': 5,
                'unique_sources': {'source1', 'source2', 'source3'},
                'data_volume_bytes': 1024 * 100,
                'total_cost': 0.15,
                'completed_categories': 1
            }
        )

        assert updated.apis_queried == {'chatgpt': 1, 'perplexity': 1}
        assert updated.sources_found == 5
        assert len(updated.unique_sources) == 3
        assert updated.total_cost == 0.15
        assert updated.completion_percentage == 50.0  # 1 of 2 categories

    @pytest.mark.asyncio
    async def test_complete_collection(self, collection_monitor, mock_audit_logger):
        """Test completing a collection."""
        # Start and update monitoring
        await collection_monitor.start_collection_monitoring(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            total_categories=1
        )

        await collection_monitor.update_collection_progress(
            "proc-456",
            {
                'sources_found': 10,
                'unique_sources': set(f"source{i}" for i in range(10)),
                'total_cost': 0.5,
                'completed_categories': 1
            }
        )

        # Complete with quality indicators
        indicators = QualityIndicators(
            source_priority_distribution={'GOVERNMENT': 3, 'PEER_REVIEWED': 5, 'NEWS': 2},
            temperature_coverage={0.1: 3, 0.5: 4, 0.9: 3},
            duplicate_count=1,
            high_priority_percentage=0.8,
            source_diversity_score=0.85,
            verification_rate=0.9,
            data_freshness_hours=2.5
        )

        completed = await collection_monitor.complete_collection(
            "proc-456",
            indicators
        )

        assert completed.status == CollectionStatus.COMPLETED
        assert completed.end_time is not None
        assert completed.completion_percentage == 100.0
        assert completed.quality_score > 0

        # Verify removed from active
        assert "proc-456" not in collection_monitor.active_collections

        # Verify audit logging
        mock_audit_logger.log_system_event.assert_called()

    @pytest.mark.asyncio
    async def test_fail_collection(self, collection_monitor, mock_audit_logger):
        """Test marking collection as failed."""
        # Start monitoring
        await collection_monitor.start_collection_monitoring(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology"
        )

        # Fail collection
        failed = await collection_monitor.fail_collection(
            "proc-456",
            "API quota exceeded"
        )

        assert failed.status == CollectionStatus.FAILED
        assert failed.end_time is not None
        assert "API quota exceeded" in failed.errors

        # Verify removed from active
        assert "proc-456" not in collection_monitor.active_collections

        # Verify error logging
        mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, collection_monitor):
        """Test quality score calculation."""
        metrics = CollectionMetrics(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            status=CollectionStatus.IN_PROGRESS,
            sources_found=10
        )

        indicators = QualityIndicators(
            source_diversity_score=0.8,
            high_priority_percentage=0.7,
            verification_rate=0.9,
            data_freshness_hours=12,  # Recent data
            duplicate_count=1
        )

        score = collection_monitor._calculate_quality_score(metrics, indicators)

        assert 0 <= score <= 1
        assert score > 0.7  # Should be relatively high given good indicators

    @pytest.mark.asyncio
    async def test_alert_triggering(self, collection_monitor, mock_audit_logger, mock_redis):
        """Test alert triggering on threshold violations."""
        # Set strict thresholds
        collection_monitor.alert_thresholds = {
            'min_quality_score': 0.8,
            'max_cost_per_request': 1.0,
            'max_collection_time_seconds': 60,
            'min_sources_required': 5,
            'max_error_rate': 0.1
        }

        # Start monitoring
        metrics = await collection_monitor.start_collection_monitoring(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology"
        )

        # Update with violations
        metrics.quality_score = 0.5  # Below threshold
        metrics.total_cost = 2.0  # Above threshold
        metrics.sources_found = 3  # Below threshold

        await collection_monitor._check_alerts(metrics)

        # Verify alerts logged
        assert mock_audit_logger.log_system_event.call_count >= 3  # Multiple alerts

        # Verify alerts stored in Redis
        assert mock_redis.lpush.call_count >= 3

    @pytest.mark.asyncio
    async def test_cache_operations(self, collection_monitor, mock_redis):
        """Test caching and loading metrics."""
        import json

        # Create metrics
        metrics = CollectionMetrics(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            status=CollectionStatus.IN_PROGRESS,
            sources_found=5,
            unique_sources={'s1', 's2', 's3'}
        )

        # Cache metrics
        await collection_monitor._cache_metrics(metrics)

        # Verify Redis set called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "collection_metrics:proc-456"
        assert call_args[0][1] == 3600  # TTL

        # Test loading from cache
        cached_data = json.dumps({
            'request_id': 'req-123',
            'process_id': 'proc-456',
            'category': 'Oncology',
            'status': 'in_progress',
            'total_categories': 1,
            'completed_categories': 0,
            'apis_queried': {},
            'sources_found': 5,
            'unique_sources': ['s1', 's2', 's3'],
            'data_volume_bytes': 0,
            'total_cost': 0.0,
            'quality_score': 0.0,
            'completion_percentage': 0.0,
            'start_time': datetime.utcnow().isoformat(),
            'end_time': None,
            'errors': [],
            'warnings': []
        })

        mock_redis.get.return_value = cached_data

        loaded = await collection_monitor._load_from_cache("proc-456")

        assert loaded is not None
        assert loaded.process_id == "proc-456"
        assert loaded.sources_found == 5

    @pytest.mark.asyncio
    async def test_completion_notification(self, collection_monitor, mock_audit_logger):
        """Test completion notification sending."""
        metrics = CollectionMetrics(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            status=CollectionStatus.COMPLETED,
            sources_found=10,
            quality_score=0.85,
            total_cost=0.5,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            end_time=datetime.utcnow()
        )

        await collection_monitor._send_completion_notification(metrics)

        # Verify notification logged
        mock_audit_logger.log_system_event.assert_called_once()
        call_args = mock_audit_logger.log_system_event.call_args
        assert call_args.kwargs['event_type'] == "collection_notification"
        assert call_args.kwargs['process_id'] == "proc-456"

    @pytest.mark.asyncio
    async def test_alert_callbacks(self, collection_monitor):
        """Test alert callback registration and execution."""
        callback_called = False
        alert_data_received = None

        async def test_callback(alert_data):
            nonlocal callback_called, alert_data_received
            callback_called = True
            alert_data_received = alert_data

        # Register callback
        collection_monitor.register_alert_callback(test_callback)

        # Create metrics that will trigger alert
        metrics = CollectionMetrics(
            request_id="req-123",
            process_id="proc-456",
            category="Oncology",
            status=CollectionStatus.IN_PROGRESS
        )

        # Send alert
        await collection_monitor._send_alert(
            AlertSeverity.WARNING,
            "Test alert",
            metrics
        )

        # Verify callback was called
        assert callback_called
        assert alert_data_received is not None
        assert alert_data_received['message'] == "Test alert"
        assert alert_data_received['severity'] == "warning"

    @pytest.mark.asyncio
    async def test_get_active_collections(self, collection_monitor):
        """Test getting active collections."""
        # Start multiple collections
        await collection_monitor.start_collection_monitoring(
            request_id="req-1",
            process_id="proc-1",
            category="Oncology"
        )

        await collection_monitor.start_collection_monitoring(
            request_id="req-2",
            process_id="proc-2",
            category="Cardiology"
        )

        active = await collection_monitor.get_active_collections()

        assert len(active) == 2
        assert any(m.process_id == "proc-1" for m in active)
        assert any(m.process_id == "proc-2" for m in active)