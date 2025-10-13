"""
Unit tests for pharmaceutical database models.

Comprehensive testing of SQLAlchemy models with pharmaceutical regulatory
compliance and audit trail validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.database.models import (
    User, UserRole, DrugRequest, RequestStatus, CategoryResult, CategoryStatus,
    SourceReference, APIProvider, SourceType, VerificationStatus,
    SourceConflict, ProcessTracking, AuditEvent, AuditEventType,
    PharmaceuticalCategory, APIUsageLog
)


class TestUserModel:
    """
    Test suite for User model with pharmaceutical platform validation.

    Validates user management functionality including role-based access
    control and pharmaceutical audit trail requirements.
    """

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating pharmaceutical platform user with validation."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password_123",
            role=UserRole.RESEARCHER
        )

        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.RESEARCHER
        assert user.is_active is True
        assert user.failed_login_attempts == 0
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_user_unique_constraints(self, db_session: AsyncSession):
        """Test pharmaceutical user unique constraints validation."""
        user1 = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User 1",
            hashed_password="hashed_password_123"
        )
        db_session.add(user1)
        await db_session.flush()

        # Test duplicate username
        user2 = User(
            username="testuser",  # Duplicate username
            email="test2@example.com",
            full_name="Test User 2",
            hashed_password="hashed_password_456"
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_user_role_enum_validation(self, db_session: AsyncSession):
        """Test pharmaceutical user role enumeration validation."""
        user = User(
            username="roletest",
            email="roletest@example.com",
            full_name="Role Test User",
            hashed_password="hashed_password_123",
            role=UserRole.ADMIN
        )

        db_session.add(user)
        await db_session.flush()

        assert user.role == UserRole.ADMIN

    async def test_user_check_constraints(self, db_session: AsyncSession):
        """Test pharmaceutical user check constraints validation."""
        user = User(
            username="constrainttest",
            email="constrainttest@example.com",
            full_name="Constraint Test User",
            hashed_password="hashed_password_123",
            failed_login_attempts=-1  # Invalid negative value
        )

        db_session.add(user)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestDrugRequestModel:
    """
    Test suite for DrugRequest model with pharmaceutical compliance validation.

    Validates drug request functionality including status management,
    category tracking, and pharmaceutical audit requirements.
    """

    async def test_create_drug_request(self, db_session: AsyncSession, test_user):
        """Test creating pharmaceutical drug request with validation."""
        drug_request = DrugRequest(
            drug_name="Aspirin",
            user_id=test_user.id,
            total_categories=17,
            completed_categories=0,
            failed_categories=[]
        )

        db_session.add(drug_request)
        await db_session.flush()

        assert drug_request.id is not None
        assert drug_request.drug_name == "Aspirin"
        assert drug_request.status == RequestStatus.PENDING
        assert drug_request.total_categories == 17
        assert drug_request.completed_categories == 0
        assert drug_request.failed_categories == []
        assert drug_request.created_at is not None
        assert drug_request.updated_at is not None

    async def test_drug_request_progress_percentage(self, db_session: AsyncSession, test_user):
        """Test pharmaceutical drug request progress calculation."""
        drug_request = DrugRequest(
            drug_name="Metformin",
            user_id=test_user.id,
            total_categories=17,
            completed_categories=8
        )

        db_session.add(drug_request)
        await db_session.flush()

        # Test progress percentage calculation
        expected_progress = (8 / 17) * 100.0
        assert abs(drug_request.progress_percentage - expected_progress) < 0.01

    async def test_drug_request_completion_status(self, db_session: AsyncSession, test_user):
        """Test pharmaceutical drug request completion validation."""
        drug_request = DrugRequest(
            drug_name="Ibuprofen",
            user_id=test_user.id,
            status=RequestStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )

        db_session.add(drug_request)
        await db_session.flush()

        assert drug_request.is_completed is True

    async def test_drug_request_check_constraints(self, db_session: AsyncSession, test_user):
        """Test pharmaceutical drug request constraint validation."""
        # Test completed categories cannot exceed total categories
        drug_request = DrugRequest(
            drug_name="InvalidRequest",
            user_id=test_user.id,
            total_categories=10,
            completed_categories=15  # Exceeds total
        )

        db_session.add(drug_request)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestCategoryResultModel:
    """
    Test suite for CategoryResult model with pharmaceutical processing validation.

    Validates category result functionality including source tracking,
    quality scoring, and pharmaceutical processing metrics.
    """

    async def test_create_category_result(
        self,
        db_session: AsyncSession,
        test_drug_request,
        test_pharmaceutical_category
    ):
        """Test creating pharmaceutical category result with validation."""
        category_result = CategoryResult(
            request_id=test_drug_request.id,
            category_id=test_pharmaceutical_category.id,
            category_name="Clinical Trials",
            summary="Clinical trial analysis for pharmaceutical compound",
            confidence_score=0.85,
            data_quality_score=0.92,
            processing_time_ms=5000,
            api_calls_made=3,
            token_count=1500,
            cost_estimate=0.075
        )

        db_session.add(category_result)
        await db_session.flush()

        assert category_result.id is not None
        assert category_result.category_name == "Clinical Trials"
        assert category_result.confidence_score == 0.85
        assert category_result.data_quality_score == 0.92
        assert category_result.status == CategoryStatus.PENDING
        assert category_result.processing_time_ms == 5000
        assert category_result.api_calls_made == 3
        assert category_result.token_count == 1500
        assert category_result.cost_estimate == 0.075

    async def test_category_result_score_constraints(
        self,
        db_session: AsyncSession,
        test_drug_request,
        test_pharmaceutical_category
    ):
        """Test pharmaceutical category result score constraints."""
        # Test confidence score out of range
        category_result = CategoryResult(
            request_id=test_drug_request.id,
            category_id=test_pharmaceutical_category.id,
            category_name="Invalid Score Test",
            summary="Test summary",
            confidence_score=1.5,  # Invalid - exceeds 1.0
            data_quality_score=0.8
        )

        db_session.add(category_result)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_category_result_unique_constraint(
        self,
        db_session: AsyncSession,
        test_drug_request,
        test_pharmaceutical_category
    ):
        """Test pharmaceutical category result uniqueness per request."""
        # Create first category result
        category_result1 = CategoryResult(
            request_id=test_drug_request.id,
            category_id=test_pharmaceutical_category.id,
            category_name="Unique Test",
            summary="First result"
        )
        db_session.add(category_result1)
        await db_session.flush()

        # Try to create duplicate for same request/category
        category_result2 = CategoryResult(
            request_id=test_drug_request.id,
            category_id=test_pharmaceutical_category.id,  # Same category
            category_name="Duplicate Test",
            summary="Second result"
        )
        db_session.add(category_result2)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestSourceReferenceModel:
    """
    Test suite for SourceReference model with pharmaceutical source validation.

    Validates source reference functionality including API provider tracking,
    verification status, and pharmaceutical source attribution.
    """

    async def test_create_source_reference(
        self,
        db_session: AsyncSession,
        test_category_result
    ):
        """Test creating pharmaceutical source reference with validation."""
        source_reference = SourceReference(
            category_result_id=test_category_result.id,
            api_provider=APIProvider.CHATGPT,
            source_url="https://example.com/pharmaceutical-study",
            source_title="Pharmaceutical Clinical Trial Study",
            source_type=SourceType.RESEARCH_PAPER,
            content_snippet="This pharmaceutical study demonstrates...",
            relevance_score=0.88,
            credibility_score=0.91,
            published_date=datetime(2023, 6, 15),
            authors="Dr. Smith, Dr. Johnson",
            journal_name="Journal of Pharmaceutical Sciences",
            doi="10.1000/xyz123",
            api_response_id="api-response-456"
        )

        db_session.add(source_reference)
        await db_session.flush()

        assert source_reference.id is not None
        assert source_reference.api_provider == APIProvider.CHATGPT
        assert source_reference.source_type == SourceType.RESEARCH_PAPER
        assert source_reference.relevance_score == 0.88
        assert source_reference.credibility_score == 0.91
        assert source_reference.verification_status == VerificationStatus.PENDING
        assert source_reference.extracted_at is not None

    async def test_source_reference_verification_constraint(
        self,
        db_session: AsyncSession,
        test_category_result
    ):
        """Test pharmaceutical source reference verification constraints."""
        # Test invalid verification state (verified without timestamp)
        source_reference = SourceReference(
            category_result_id=test_category_result.id,
            api_provider=APIProvider.PERPLEXITY,
            content_snippet="Test content",
            verification_status=VerificationStatus.VERIFIED,
            verified_at=None  # Invalid - verified without timestamp
        )

        db_session.add(source_reference)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestAuditEventModel:
    """
    Test suite for AuditEvent model with pharmaceutical compliance validation.

    Validates audit event functionality including immutable audit trails,
    regulatory compliance, and comprehensive change tracking.
    """

    async def test_create_audit_event(
        self,
        db_session: AsyncSession,
        test_drug_request,
        test_user
    ):
        """Test creating pharmaceutical audit event with validation."""
        audit_event = AuditEvent(
            request_id=test_drug_request.id,
            event_type=AuditEventType.CREATE,
            event_description="Created pharmaceutical intelligence request",
            entity_type="DrugRequest",
            entity_id=str(test_drug_request.id),
            new_values={"drug_name": "Aspirin", "status": "pending"},
            user_id=test_user.id,
            correlation_id="corr-123",
            session_id="session-456",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 CognitoAI/1.0"
        )

        db_session.add(audit_event)
        await db_session.flush()

        assert audit_event.id is not None
        assert audit_event.event_type == AuditEventType.CREATE
        assert audit_event.entity_type == "DrugRequest"
        assert audit_event.new_values == {"drug_name": "Aspirin", "status": "pending"}
        assert audit_event.timestamp is not None
        assert audit_event.correlation_id == "corr-123"
        assert audit_event.ip_address == "192.168.1.100"

    async def test_audit_event_jsonb_fields(
        self,
        db_session: AsyncSession,
        test_user
    ):
        """Test pharmaceutical audit event JSONB field handling."""
        complex_metadata = {
            "pharmaceutical_data": {
                "categories": ["clinical_trials", "side_effects"],
                "confidence_scores": [0.85, 0.72],
                "processing_metrics": {
                    "api_calls": 5,
                    "tokens_used": 2500,
                    "processing_time_ms": 4500
                }
            },
            "compliance_flags": ["FDA_reviewed", "audit_trail_complete"]
        }

        audit_event = AuditEvent(
            event_type=AuditEventType.PROCESS_COMPLETE,
            event_description="Completed pharmaceutical processing with metadata",
            entity_type="CategoryResult",
            entity_id="cat-result-123",
            user_id=test_user.id,
            audit_metadata=complex_metadata
        )

        db_session.add(audit_event)
        await db_session.flush()

        assert audit_event.audit_metadata == complex_metadata
        assert audit_event.metadata["pharmaceutical_data"]["categories"] == ["clinical_trials", "side_effects"]
        assert audit_event.metadata["pharmaceutical_data"]["processing_metrics"]["api_calls"] == 5


class TestProcessTrackingModel:
    """
    Test suite for ProcessTracking model with pharmaceutical correlation validation.

    Validates process tracking functionality including correlation IDs,
    hierarchical tracking, and pharmaceutical process management.
    """

    async def test_create_process_tracking(
        self,
        db_session: AsyncSession,
        test_drug_request
    ):
        """Test creating pharmaceutical process tracking with validation."""
        process_tracking = ProcessTracking(
            request_id=test_drug_request.id,
            process_type="category_processing",
            status="started",
            correlation_id="corr-proc-123",
            process_metadata={
                "category": "Clinical Trials",
                "api_provider": "chatgpt",
                "priority": "high"
            }
        )

        db_session.add(process_tracking)
        await db_session.flush()

        assert process_tracking.id is not None
        assert process_tracking.process_type == "category_processing"
        assert process_tracking.status == "started"
        assert process_tracking.correlation_id == "corr-proc-123"
        assert process_tracking.started_at is not None
        assert process_tracking.metadata["category"] == "Clinical Trials"

    async def test_process_tracking_duration_calculation(
        self,
        db_session: AsyncSession,
        test_drug_request
    ):
        """Test pharmaceutical process tracking duration calculation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=5, seconds=30)

        process_tracking = ProcessTracking(
            request_id=test_drug_request.id,
            process_type="source_verification",
            status="completed",
            started_at=start_time,
            completed_at=end_time
        )

        db_session.add(process_tracking)
        await db_session.flush()

        expected_duration = timedelta(minutes=5, seconds=30)
        assert abs((process_tracking.duration - expected_duration).total_seconds()) < 1.0

    async def test_process_tracking_completion_constraint(
        self,
        db_session: AsyncSession,
        test_drug_request
    ):
        """Test pharmaceutical process tracking completion time constraints."""
        # Test invalid completion time (before start time)
        start_time = datetime.utcnow()
        invalid_end_time = start_time - timedelta(minutes=1)

        process_tracking = ProcessTracking(
            request_id=test_drug_request.id,
            process_type="invalid_timing",
            status="completed",
            started_at=start_time,
            completed_at=invalid_end_time  # Invalid - before start time
        )

        db_session.add(process_tracking)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestAPIUsageLogModel:
    """
    Test suite for APIUsageLog model with pharmaceutical cost tracking validation.

    Validates API usage logging functionality including token counting,
    cost estimation, and pharmaceutical API monitoring.
    """

    async def test_create_api_usage_log(
        self,
        db_session: AsyncSession,
        test_drug_request,
        test_category_result
    ):
        """Test creating pharmaceutical API usage log with validation."""
        api_usage_log = APIUsageLog(
            request_id=test_drug_request.id,
            category_result_id=test_category_result.id,
            api_provider=APIProvider.GEMINI,
            endpoint="/v1/generate",
            request_payload={"prompt": "Analyze pharmaceutical data", "max_tokens": 1000},
            response_status=200,
            response_time_ms=2500,
            token_count=850,
            cost_per_token=0.0001,
            total_cost=0.085,
            rate_limit_remaining=95,
            correlation_id="api-call-789"
        )

        db_session.add(api_usage_log)
        await db_session.flush()

        assert api_usage_log.id is not None
        assert api_usage_log.api_provider == APIProvider.GEMINI
        assert api_usage_log.response_status == 200
        assert api_usage_log.response_time_ms == 2500
        assert api_usage_log.token_count == 850
        assert api_usage_log.cost_per_token == 0.0001
        assert api_usage_log.total_cost == 0.085
        assert api_usage_log.timestamp is not None

    async def test_api_usage_log_constraints(
        self,
        db_session: AsyncSession,
        test_drug_request
    ):
        """Test pharmaceutical API usage log constraint validation."""
        # Test invalid HTTP status code
        api_usage_log = APIUsageLog(
            request_id=test_drug_request.id,
            api_provider=APIProvider.TAVILY,
            endpoint="/invalid",
            response_status=99,  # Invalid HTTP status
            response_time_ms=1000,
            token_count=100,
            cost_per_token=0.001,
            total_cost=0.1
        )

        db_session.add(api_usage_log)

        with pytest.raises(IntegrityError):
            await db_session.flush()