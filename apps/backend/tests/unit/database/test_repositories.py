"""
Unit tests for pharmaceutical repository operations.

Comprehensive testing of repository pattern with pharmaceutical regulatory
compliance, audit trails, and data integrity validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import (
    DrugRequestRepository, CategoryResultRepository, SourceReferenceRepository,
    ProcessTrackingRepository, AuditRepository
)
from src.database.models import (
    RequestStatus, CategoryStatus, APIProvider, SourceType, VerificationStatus,
    AuditEventType
)


class TestDrugRequestRepository:
    """
    Test suite for DrugRequestRepository with pharmaceutical compliance.

    Validates drug request repository operations including creation,
    status management, and pharmaceutical audit trail compliance.
    """

    @pytest.fixture
    async def drug_request_repo(self, db_session: AsyncSession, test_user):
        """Create drug request repository with pharmaceutical audit context."""
        return DrugRequestRepository(
            db=db_session,
            user_id=test_user.id,
            correlation_id="test-correlation-123"
        )

    async def test_create_drug_request(self, drug_request_repo, test_user):
        """Test creating pharmaceutical drug request with comprehensive validation."""
        drug_request = await drug_request_repo.create_drug_request(
            drug_name="Metformin HCl",
            user_id=test_user.id,
            priority_categories=[1, 2, 3],
            total_categories=17,
            request_metadata={
                "therapeutic_class": "antidiabetic",
                "molecular_formula": "C4H11N5",
                "regulatory_pathway": "NDA"
            }
        )

        assert drug_request.id is not None
        assert drug_request.drug_name == "Metformin HCl"
        assert drug_request.user_id == test_user.id
        assert drug_request.status == RequestStatus.PENDING
        assert drug_request.total_categories == 17
        assert drug_request.completed_categories == 0
        assert drug_request.priority_categories == [1, 2, 3]
        assert drug_request.metadata["therapeutic_class"] == "antidiabetic"
        assert drug_request.created_at is not None

    async def test_get_drug_request_with_details(
        self,
        drug_request_repo,
        test_drug_request
    ):
        """Test retrieving pharmaceutical drug request with complete details."""
        detailed_request = await drug_request_repo.get_drug_request_with_details(
            test_drug_request.id
        )

        assert detailed_request is not None
        assert detailed_request.id == test_drug_request.id
        assert detailed_request.drug_name == test_drug_request.drug_name
        # Verify relationships are loaded
        assert hasattr(detailed_request, 'category_results')
        assert hasattr(detailed_request, 'process_tracking_entries')
        assert hasattr(detailed_request, 'user')

    async def test_update_request_status(
        self,
        drug_request_repo,
        test_drug_request
    ):
        """Test updating pharmaceutical drug request status with audit trail."""
        updated_request = await drug_request_repo.update_request_status(
            request_id=test_drug_request.id,
            status=RequestStatus.COMPLETED,
            completed_categories=15,
            failed_categories=["Patent Analysis", "Competitive Landscape"],
            actual_processing_time=3600  # 1 hour in seconds
        )

        assert updated_request is not None
        assert updated_request.status == RequestStatus.COMPLETED
        assert updated_request.completed_categories == 15
        assert updated_request.failed_categories == ["Patent Analysis", "Competitive Landscape"]
        assert updated_request.actual_processing_time == 3600
        assert updated_request.completed_at is not None

    async def test_get_user_requests(
        self,
        drug_request_repo,
        test_user,
        test_drug_request
    ):
        """Test retrieving pharmaceutical drug requests for specific user."""
        user_requests = await drug_request_repo.get_user_requests(
            user_id=test_user.id,
            status_filter=RequestStatus.PROCESSING,
            limit=10
        )

        assert len(user_requests) > 0
        for request in user_requests:
            assert request.user_id == test_user.id
            assert request.status == RequestStatus.PROCESSING

    async def test_get_processing_statistics(self, drug_request_repo):
        """Test generating pharmaceutical processing statistics."""
        statistics = await drug_request_repo.get_processing_statistics(
            date_range_days=30
        )

        assert "total_requests" in statistics
        assert "completed_requests" in statistics
        assert "failed_requests" in statistics
        assert "success_rate" in statistics
        assert "failure_rate" in statistics
        assert "top_drugs" in statistics
        assert isinstance(statistics["success_rate"], float)
        assert 0.0 <= statistics["success_rate"] <= 1.0


class TestCategoryResultRepository:
    """
    Test suite for CategoryResultRepository with pharmaceutical processing.

    Validates category result repository operations including creation,
    status updates, and pharmaceutical source tracking compliance.
    """

    @pytest.fixture
    async def category_result_repo(self, db_session: AsyncSession, test_user):
        """Create category result repository with pharmaceutical audit context."""
        return CategoryResultRepository(
            db=db_session,
            user_id=test_user.id,
            correlation_id="test-category-correlation-456"
        )

    async def test_create_category_result(
        self,
        category_result_repo,
        test_drug_request,
        test_pharmaceutical_category
    ):
        """Test creating pharmaceutical category result with validation."""
        category_result = await category_result_repo.create_category_result(
            request_id=test_drug_request.id,
            category_id=test_pharmaceutical_category.id,
            category_name="Clinical Trials & Studies",
            summary="Comprehensive clinical trial analysis showing Phase III efficacy data with 89% response rate and acceptable safety profile for pharmaceutical compound.",
            confidence_score=0.91,
            data_quality_score=0.87
        )

        assert category_result.id is not None
        assert category_result.request_id == test_drug_request.id
        assert category_result.category_id == test_pharmaceutical_category.id
        assert category_result.category_name == "Clinical Trials & Studies"
        assert category_result.confidence_score == 0.91
        assert category_result.data_quality_score == 0.87
        assert category_result.status == CategoryStatus.PENDING
        assert category_result.started_at is not None

    async def test_update_processing_status(
        self,
        category_result_repo,
        test_category_result
    ):
        """Test updating pharmaceutical category processing status with metrics."""
        updated_result = await category_result_repo.update_processing_status(
            result_id=test_category_result.id,
            status=CategoryStatus.COMPLETED,
            processing_time_ms=4500,
            api_calls_made=3,
            token_count=1250,
            cost_estimate=0.062
        )

        assert updated_result is not None
        assert updated_result.status == CategoryStatus.COMPLETED
        assert updated_result.processing_time_ms == 4500
        assert updated_result.api_calls_made == 3
        assert updated_result.token_count == 1250
        assert updated_result.cost_estimate == 0.062
        assert updated_result.completed_at is not None

    async def test_get_result_with_sources(
        self,
        category_result_repo,
        test_category_result
    ):
        """Test retrieving pharmaceutical category result with source tracking."""
        result_with_sources = await category_result_repo.get_result_with_sources(
            test_category_result.id
        )

        assert result_with_sources is not None
        assert result_with_sources.id == test_category_result.id
        # Verify source relationships are loaded
        assert hasattr(result_with_sources, 'source_references')
        assert hasattr(result_with_sources, 'source_conflicts')
        assert hasattr(result_with_sources, 'category')
        assert hasattr(result_with_sources, 'drug_request')

    async def test_get_request_results(
        self,
        category_result_repo,
        test_drug_request,
        test_category_result
    ):
        """Test retrieving all pharmaceutical category results for request."""
        request_results = await category_result_repo.get_request_results(
            request_id=test_drug_request.id,
            status_filter=CategoryStatus.COMPLETED
        )

        assert len(request_results) > 0
        for result in request_results:
            assert result.request_id == test_drug_request.id
            assert result.status == CategoryStatus.COMPLETED


class TestSourceReferenceRepository:
    """
    Test suite for SourceReferenceRepository with pharmaceutical compliance.

    Validates source reference repository operations including creation,
    verification, and pharmaceutical regulatory compliance tracking.
    """

    @pytest.fixture
    async def source_reference_repo(self, db_session: AsyncSession, test_user):
        """Create source reference repository with pharmaceutical audit context."""
        return SourceReferenceRepository(
            db=db_session,
            user_id=test_user.id,
            correlation_id="test-source-correlation-789"
        )

    async def test_create_source_reference(
        self,
        source_reference_repo,
        test_category_result
    ):
        """Test creating pharmaceutical source reference with comprehensive tracking."""
        source_reference = await source_reference_repo.create_source_reference(
            category_result_id=test_category_result.id,
            api_provider=APIProvider.PERPLEXITY,
            content_snippet="Phase III randomized controlled trial of pharmaceutical compound demonstrated statistically significant improvement in primary endpoint (p<0.001) with 500 patients enrolled.",
            source_url="https://clinicaltrials.gov/ct2/show/NCT87654321",
            source_title="Efficacy and Safety of Novel Pharmaceutical Compound in Phase III Trial",
            source_type=SourceType.CLINICAL_TRIAL,
            relevance_score=0.93,
            credibility_score=0.89,
            api_response_id="perplexity-response-12345"
        )

        assert source_reference.id is not None
        assert source_reference.category_result_id == test_category_result.id
        assert source_reference.api_provider == APIProvider.PERPLEXITY
        assert source_reference.source_type == SourceType.CLINICAL_TRIAL
        assert source_reference.relevance_score == 0.93
        assert source_reference.credibility_score == 0.89
        assert source_reference.verification_status == VerificationStatus.PENDING
        assert source_reference.extracted_at is not None

    async def test_verify_source(
        self,
        source_reference_repo,
        test_source_reference,
        test_user
    ):
        """Test verifying pharmaceutical source for regulatory compliance."""
        verified_source = await source_reference_repo.verify_source(
            source_id=test_source_reference.id,
            verification_status=VerificationStatus.VERIFIED,
            verified_by=test_user.id,
            verification_notes="Verified pharmaceutical source meets regulatory standards"
        )

        assert verified_source is not None
        assert verified_source.verification_status == VerificationStatus.VERIFIED
        assert verified_source.verified_by == test_user.id
        assert verified_source.verified_at is not None

    async def test_get_category_sources(
        self,
        source_reference_repo,
        test_category_result,
        test_source_reference
    ):
        """Test retrieving pharmaceutical sources for category result."""
        category_sources = await source_reference_repo.get_category_sources(
            category_result_id=test_category_result.id,
            verification_status=VerificationStatus.VERIFIED,
            api_provider=APIProvider.CHATGPT
        )

        assert len(category_sources) > 0
        for source in category_sources:
            assert source.category_result_id == test_category_result.id
            assert source.verification_status == VerificationStatus.VERIFIED
            assert source.api_provider == APIProvider.CHATGPT


class TestProcessTrackingRepository:
    """
    Test suite for ProcessTrackingRepository with pharmaceutical correlation.

    Validates process tracking repository operations including creation,
    completion, and pharmaceutical audit trail correlation.
    """

    @pytest.fixture
    async def process_tracking_repo(self, db_session: AsyncSession, test_user):
        """Create process tracking repository with pharmaceutical audit context."""
        return ProcessTrackingRepository(
            db=db_session,
            user_id=test_user.id,
            correlation_id="test-process-correlation-abc"
        )

    async def test_create_process(
        self,
        process_tracking_repo,
        test_drug_request
    ):
        """Test creating pharmaceutical process tracking with correlation."""
        process = await process_tracking_repo.create_process(
            request_id=test_drug_request.id,
            process_type="category_processing",
            correlation_id="pharma-process-12345",
            process_metadata={
                "category": "Clinical Trials & Studies",
                "api_provider": "chatgpt",
                "priority": "high",
                "regulatory_compliance": True
            }
        )

        assert process.id is not None
        assert process.request_id == test_drug_request.id
        assert process.process_type == "category_processing"
        assert process.correlation_id == "pharma-process-12345"
        assert process.status == "started"
        assert process.metadata["category"] == "Clinical Trials & Studies"
        assert process.metadata["regulatory_compliance"] is True
        assert process.started_at is not None

    async def test_complete_process(
        self,
        process_tracking_repo,
        test_process_tracking
    ):
        """Test completing pharmaceutical process with comprehensive metrics."""
        completed_process = await process_tracking_repo.complete_process(
            process_id=test_process_tracking.id,
            status="completed",
            metadata_update={
                "sources_found": 15,
                "conflicts_detected": 2,
                "verification_rate": 0.89,
                "regulatory_compliance_verified": True
            }
        )

        assert completed_process is not None
        assert completed_process.status == "completed"
        assert completed_process.completed_at is not None
        assert completed_process.metadata["sources_found"] == 15
        assert completed_process.metadata["conflicts_detected"] == 2
        assert completed_process.metadata["regulatory_compliance_verified"] is True

    async def test_get_process_hierarchy(
        self,
        process_tracking_repo,
        test_process_tracking
    ):
        """Test retrieving pharmaceutical process hierarchy for audit trails."""
        hierarchy = await process_tracking_repo.get_process_hierarchy(
            test_process_tracking.id
        )

        assert len(hierarchy) > 0
        # Verify root process is included
        root_process = next((p for p in hierarchy if p.id == test_process_tracking.id), None)
        assert root_process is not None

    async def test_get_request_processes(
        self,
        process_tracking_repo,
        test_drug_request,
        test_process_tracking
    ):
        """Test retrieving pharmaceutical processes for drug request."""
        request_processes = await process_tracking_repo.get_request_processes(
            request_id=test_drug_request.id,
            process_type_filter="category_processing"
        )

        assert len(request_processes) > 0
        for process in request_processes:
            assert process.request_id == test_drug_request.id
            assert process.process_type == "category_processing"

    async def test_get_process_statistics(
        self,
        process_tracking_repo,
        test_drug_request
    ):
        """Test generating pharmaceutical process statistics."""
        statistics = await process_tracking_repo.get_process_statistics(
            request_id=test_drug_request.id,
            process_type="category_processing",
            date_range_days=7
        )

        assert "total_processes" in statistics
        assert "completed_processes" in statistics
        assert "successful_processes" in statistics
        assert "failed_processes" in statistics
        assert "success_rate" in statistics
        assert "process_type_breakdown" in statistics
        assert isinstance(statistics["success_rate"], float)
        assert 0.0 <= statistics["success_rate"] <= 1.0


class TestAuditRepository:
    """
    Test suite for AuditRepository with pharmaceutical compliance.

    Validates audit repository operations including event logging,
    trail retrieval, and pharmaceutical regulatory compliance reporting.
    """

    @pytest.fixture
    async def audit_repo(self, db_session: AsyncSession, test_user):
        """Create audit repository with pharmaceutical compliance context."""
        return AuditRepository(
            db=db_session,
            user_id=test_user.id,
            correlation_id="test-audit-correlation-def"
        )

    async def test_log_entity_creation(
        self,
        audit_repo,
        test_drug_request,
        test_user
    ):
        """Test logging pharmaceutical entity creation for compliance."""
        audit_event = await audit_repo.log_entity_creation(
            entity_type="DrugRequest",
            entity_id=str(test_drug_request.id),
            new_values={
                "drug_name": test_drug_request.drug_name,
                "status": test_drug_request.status.value,
                "total_categories": test_drug_request.total_categories
            },
            description="Created pharmaceutical intelligence request",
            request_id=test_drug_request.id,
            session_id="test-session-123",
            ip_address="192.168.1.100",
            user_agent="CognitoAI-Test/1.0"
        )

        assert audit_event.id is not None
        assert audit_event.event_type == AuditEventType.CREATE
        assert audit_event.entity_type == "DrugRequest"
        assert audit_event.entity_id == str(test_drug_request.id)
        assert audit_event.new_values["drug_name"] == test_drug_request.drug_name
        assert audit_event.user_id == test_user.id
        assert audit_event.timestamp is not None
        assert audit_event.ip_address == "192.168.1.100"

    async def test_log_entity_update(
        self,
        audit_repo,
        test_drug_request
    ):
        """Test logging pharmaceutical entity update for compliance."""
        audit_event = await audit_repo.log_entity_update(
            entity_type="DrugRequest",
            entity_id=str(test_drug_request.id),
            old_values={"status": "processing", "completed_categories": 5},
            new_values={"status": "completed", "completed_categories": 15},
            description="Updated pharmaceutical request status to completed"
        )

        assert audit_event.event_type == AuditEventType.UPDATE
        assert audit_event.old_values["status"] == "processing"
        assert audit_event.new_values["status"] == "completed"
        assert audit_event.old_values["completed_categories"] == 5
        assert audit_event.new_values["completed_categories"] == 15

    async def test_get_entity_audit_trail(
        self,
        audit_repo,
        test_drug_request,
        test_audit_event
    ):
        """Test retrieving pharmaceutical entity audit trail."""
        audit_trail = await audit_repo.get_entity_audit_trail(
            entity_type="DrugRequest",
            entity_id=str(test_drug_request.id),
            include_related=True
        )

        assert len(audit_trail) > 0
        for event in audit_trail:
            assert event.entity_type == "DrugRequest" or event.request_id == test_drug_request.id

    async def test_get_compliance_report(
        self,
        audit_repo
    ):
        """Test generating pharmaceutical regulatory compliance report."""
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        report = await audit_repo.get_compliance_report(
            start_date=start_date,
            end_date=end_date,
            entity_types=["DrugRequest", "CategoryResult"]
        )

        assert "reporting_period" in report
        assert "total_audit_events" in report
        assert "compliance_metrics" in report
        assert "event_type_breakdown" in report
        assert "entity_type_breakdown" in report
        assert "user_activity_summary" in report
        assert "data_integrity_status" in report
        assert "retention_compliance" in report
        assert report["data_integrity_status"] == "verified"
        assert report["retention_compliance"] == "7_year_policy_active"