"""
Tests for raw data persistence and retrieval.

Validates data storage, retention policies, integrity validation,
and pharmaceutical compliance features.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.core.data_persistence import DataPersistenceManager
from src.database.repositories.raw_data_repo import RawDataRepository
from src.database.models import APIResponse, APIResponseMetadata
from src.integrations.providers.base import (
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution
)


@pytest.fixture
async def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
async def mock_audit_logger():
    """Create mock audit logger."""
    logger = AsyncMock()
    logger.log_data_access = AsyncMock()
    logger.log_system_health_check = AsyncMock()
    return logger


@pytest.fixture
async def sample_api_response():
    """Create sample standardized API response."""
    return StandardizedAPIResponse(
        provider="chatgpt",
        query="What are the side effects of aspirin?",
        temperature=0.7,
        results=[
            SearchResult(
                title="Aspirin Side Effects",
                content="Common side effects include stomach upset...",
                relevance_score=0.95,
                source_type="medical_database",
                metadata={
                    "publication": "Mayo Clinic",
                    "last_updated": "2024-01-15"
                }
            ),
            SearchResult(
                title="Aspirin Interactions",
                content="Aspirin may interact with blood thinners...",
                relevance_score=0.88,
                source_type="clinical_trial",
                metadata={
                    "trial_id": "NCT12345",
                    "phase": "Phase III"
                }
            )
        ],
        sources=[
            SourceAttribution(
                title="Mayo Clinic - Aspirin",
                url="https://mayoclinic.org/drugs/aspirin",
                domain="mayoclinic.org",
                source_type="medical_database",
                credibility_score=0.98
            )
        ],
        total_results=2,
        response_time_ms=1250,
        cost=0.042,
        relevance_score=0.91,
        confidence_score=0.89,
        timestamp=datetime.utcnow()
    )


class TestDataPersistenceManager:
    """Tests for DataPersistenceManager."""

    @pytest.mark.asyncio
    async def test_store_api_response(
        self,
        mock_db,
        mock_audit_logger,
        sample_api_response
    ):
        """Test storing API response with metadata."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger,
            encryption_enabled=False  # Disable for testing
        )

        # Store response
        response_id = await manager.store_api_response(
            response=sample_api_response,
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-789",
            pharmaceutical_compound="Aspirin",
            category="NSAID"
        )

        # Verify response ID generated
        assert response_id is not None
        assert len(response_id) == 36  # UUID format

        # Verify database operations
        assert mock_db.add.call_count == 2  # Response + metadata
        mock_db.commit.assert_called_once()

        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called_once()
        call_args = mock_audit_logger.log_data_access.call_args
        assert call_args.kwargs['resource'] == "api_responses"
        assert call_args.kwargs['action'] == "create"
        assert call_args.kwargs['drug_names'] == ["Aspirin"]

    @pytest.mark.asyncio
    async def test_checksum_calculation(
        self,
        mock_db,
        mock_audit_logger,
        sample_api_response
    ):
        """Test data integrity checksum calculation."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger,
            encryption_enabled=False
        )

        # Calculate checksum
        data = json.dumps(sample_api_response.dict(), sort_keys=True)
        checksum = manager._calculate_checksum(data)

        # Verify checksum format
        assert len(checksum) == 64  # SHA-256 hex digest
        assert all(c in '0123456789abcdef' for c in checksum)

        # Verify checksum consistency
        checksum2 = manager._calculate_checksum(data)
        assert checksum == checksum2

    @pytest.mark.asyncio
    async def test_retention_policy(
        self,
        mock_db,
        mock_audit_logger,
        sample_api_response
    ):
        """Test 7-year retention policy setting."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger,
            encryption_enabled=False
        )

        # Capture added response
        captured_response = None

        def capture_add(obj):
            nonlocal captured_response
            if isinstance(obj, APIResponse):
                captured_response = obj

        mock_db.add.side_effect = capture_add

        # Store response
        await manager.store_api_response(
            response=sample_api_response,
            process_id="process-123",
            request_id="request-456",
            correlation_id="corr-789",
            pharmaceutical_compound="Aspirin",
            category="NSAID"
        )

        # Verify retention period
        assert captured_response is not None
        retention_date = captured_response.retention_expires_at
        expected_date = datetime.utcnow() + timedelta(days=365*7)

        # Allow 1 minute tolerance for test execution
        diff = abs((retention_date - expected_date).total_seconds())
        assert diff < 60

    @pytest.mark.asyncio
    async def test_metadata_creation(
        self,
        mock_db,
        mock_audit_logger,
        sample_api_response
    ):
        """Test metadata record creation."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger,
            encryption_enabled=False
        )

        # Create metadata
        metadata = await manager._create_metadata(
            sample_api_response,
            "response-id-123"
        )

        # Verify metadata fields
        assert metadata.api_response_id == "response-id-123"
        assert metadata.source_count == 1
        assert metadata.unique_domains == ["mayoclinic.org"]
        assert "medical_database" in metadata.source_types
        assert len(metadata.key_findings) > 0
        assert metadata.storage_size_bytes > 0

    @pytest.mark.asyncio
    async def test_retrieve_response_with_validation(
        self,
        mock_db,
        mock_audit_logger
    ):
        """Test retrieving response with checksum validation."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger
        )

        # Create mock response
        mock_response = MagicMock(spec=APIResponse)
        mock_response.id = "test-123"
        mock_response.pharmaceutical_compound = "Aspirin"
        mock_response.raw_response = {"test": "data"}
        mock_response.checksum = hashlib.sha256(
            json.dumps({"test": "data"}, sort_keys=True).encode()
        ).hexdigest()

        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_response
        mock_db.execute.return_value = mock_result

        # Retrieve with validation
        response = await manager.retrieve_response(
            "test-123",
            validate_checksum=True
        )

        # Verify response returned
        assert response == mock_response

        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_responses(
        self,
        mock_db,
        mock_audit_logger
    ):
        """Test searching historical responses."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger
        )

        # Setup mock results
        mock_responses = [
            MagicMock(spec=APIResponse) for _ in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_responses
        mock_db.execute.return_value = mock_result

        # Search
        results = await manager.search_responses(
            pharmaceutical_compound="Aspirin",
            category="NSAID",
            provider="chatgpt",
            limit=10
        )

        # Verify results
        assert len(results) == 3
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_archive_old_responses(
        self,
        mock_db,
        mock_audit_logger
    ):
        """Test archiving old responses."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger
        )

        # Setup mock update result
        mock_result = MagicMock()
        mock_result.rowcount = 25
        mock_db.execute.return_value = mock_result

        # Archive
        count = await manager.archive_old_responses(days_old=365)

        # Verify
        assert count == 25
        mock_db.commit.assert_called_once()
        mock_audit_logger.log_system_health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_data_integrity(
        self,
        mock_db,
        mock_audit_logger
    ):
        """Test data integrity validation."""
        manager = DataPersistenceManager(
            mock_db,
            mock_audit_logger
        )

        # Create mock responses with valid and invalid checksums
        valid_response = MagicMock(spec=APIResponse)
        valid_response.id = "valid-123"
        valid_response.raw_response = {"data": "valid"}
        valid_response.checksum = hashlib.sha256(
            json.dumps({"data": "valid"}, sort_keys=True).encode()
        ).hexdigest()
        valid_response.is_valid = True

        invalid_response = MagicMock(spec=APIResponse)
        invalid_response.id = "invalid-456"
        invalid_response.raw_response = {"data": "tampered"}
        invalid_response.checksum = "wrong-checksum"
        invalid_response.is_valid = True

        # Setup mock query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            valid_response,
            invalid_response
        ]
        mock_db.execute.return_value = mock_result

        # Validate
        results = await manager.validate_data_integrity(batch_size=2)

        # Verify
        assert results['valid'] == 1
        assert results['invalid'] == 1
        assert results['total'] == 2
        assert invalid_response.is_valid is False


class TestRawDataRepository:
    """Tests for RawDataRepository."""

    @pytest.mark.asyncio
    async def test_get_with_metadata(self, mock_db):
        """Test getting response with eagerly loaded metadata."""
        repo = RawDataRepository(mock_db)

        # Setup mock response
        mock_response = MagicMock(spec=APIResponse)
        mock_response.id = "test-123"
        mock_response.metadata = MagicMock(spec=APIResponseMetadata)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_response
        mock_db.execute.return_value = mock_result

        # Get with metadata
        response = await repo.get_with_metadata("test-123")

        # Verify
        assert response == mock_response
        assert response.metadata is not None

    @pytest.mark.asyncio
    async def test_get_cost_summary(self, mock_db):
        """Test cost summary aggregation."""
        repo = RawDataRepository(mock_db)

        # Setup mock aggregation results
        mock_row = MagicMock()
        mock_row.group_name = "chatgpt"
        mock_row.request_count = 100
        mock_row.total_cost = 42.50
        mock_row.avg_cost = 0.425
        mock_row.total_time_ms = 125000

        mock_result = MagicMock()
        mock_result.__iter__ = lambda x: iter([mock_row])
        mock_db.execute.return_value = mock_result

        # Get summary
        summary = await repo.get_cost_summary(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            group_by="provider"
        )

        # Verify
        assert len(summary) == 1
        assert summary[0]['group_name'] == "chatgpt"
        assert summary[0]['total_cost'] == 42.50
        assert summary[0]['request_count'] == 100

    @pytest.mark.asyncio
    async def test_get_quality_metrics(self, mock_db):
        """Test quality metrics calculation."""
        repo = RawDataRepository(mock_db)

        # Setup mock metrics
        mock_row = MagicMock()
        mock_row.total_responses = 500
        mock_row.avg_relevance = 0.88
        mock_row.avg_quality = 0.85
        mock_row.avg_confidence = 0.90
        mock_row.avg_response_time = 1500

        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Get metrics
        metrics = await repo.get_quality_metrics(
            provider="chatgpt",
            category="NSAID"
        )

        # Verify
        assert metrics['total_responses'] == 500
        assert metrics['avg_relevance_score'] == 0.88
        assert metrics['avg_quality_score'] == 0.85
        assert metrics['avg_confidence_score'] == 0.90
        assert metrics['avg_response_time_ms'] == 1500

    @pytest.mark.asyncio
    async def test_get_duplicate_responses(self, mock_db):
        """Test finding duplicate responses."""
        repo = RawDataRepository(mock_db)

        # Setup mock duplicates
        mock_row1 = MagicMock()
        mock_row1.checksum = "checksum123"
        mock_row1.count = 3

        mock_row2 = MagicMock()
        mock_row2.checksum = "checksum456"
        mock_row2.count = 2

        mock_result = MagicMock()
        mock_result.__iter__ = lambda x: iter([mock_row1, mock_row2])
        mock_db.execute.return_value = mock_result

        # Find duplicates
        duplicates = await repo.get_duplicate_responses(
            compound="Aspirin",
            category="NSAID",
            provider="chatgpt"
        )

        # Verify
        assert len(duplicates) == 2
        assert duplicates[0] == ("checksum123", 3)
        assert duplicates[1] == ("checksum456", 2)

    @pytest.mark.asyncio
    async def test_archive_responses(self, mock_db):
        """Test batch archival of responses."""
        repo = RawDataRepository(mock_db)

        # Setup mock update
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db.execute.return_value = mock_result

        # Archive
        response_ids = [f"id-{i}" for i in range(10)]
        count = await repo.archive_responses(response_ids)

        # Verify
        assert count == 10
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_expired_responses(self, mock_db):
        """Test deletion of expired responses."""
        repo = RawDataRepository(mock_db)

        # Setup mock delete
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db.execute.return_value = mock_result

        # Delete expired
        count = await repo.delete_expired_responses()

        # Verify
        assert count == 5
        mock_db.commit.assert_called_once()