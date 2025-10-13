"""
Pytest configuration and fixtures for CognitoAI Engine pharmaceutical platform.

Comprehensive test fixtures with pharmaceutical compliance data and
database setup for regulatory testing requirements.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from datetime import datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.database.models import (
    User, UserRole, DrugRequest, RequestStatus, CategoryResult, CategoryStatus,
    SourceReference, APIProvider, SourceType, VerificationStatus,
    PharmaceuticalCategory, ProcessTracking, AuditEvent, AuditEventType
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.

    Provides event loop for pharmaceutical platform async testing
    with proper cleanup and pharmaceutical test isolation.

    Since:
        Version 1.0.0
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Create test database engine for pharmaceutical platform testing.

    Creates isolated database engine with pharmaceutical test data
    and proper cleanup for regulatory compliance testing.

    Since:
        Version 1.0.0
    """
    # Use in-memory SQLite for fast pharmaceutical tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )

    # Create all pharmaceutical tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup pharmaceutical test data
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session for pharmaceutical operations.

    Provides isolated database session with pharmaceutical test data
    and transaction rollback for clean test isolation.

    Args:
        db_engine: Test database engine

    Yields:
        AsyncSession: Database session for pharmaceutical testing

    Since:
        Version 1.0.0
    """
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Begin transaction for pharmaceutical test isolation
        transaction = await session.begin()

        yield session

        # Rollback pharmaceutical test data
        await transaction.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create test user for pharmaceutical platform testing.

    Creates pharmaceutical platform user with researcher role
    for comprehensive pharmaceutical operation testing.

    Args:
        db_session: Database session for pharmaceutical operations

    Returns:
        User: Test user for pharmaceutical platform operations

    Since:
        Version 1.0.0
    """
    user = User(
        id=str(uuid4()),
        username="pharma_researcher",
        email="researcher@pharmaceutical.com",
        full_name="Pharmaceutical Researcher",
        hashed_password="hashed_password_test_123",
        role=UserRole.RESEARCHER,
        is_active=True
    )

    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """
    Create test admin user for pharmaceutical platform testing.

    Creates pharmaceutical platform admin user for administrative
    operations and regulatory compliance testing.

    Args:
        db_session: Database session for pharmaceutical operations

    Returns:
        User: Test admin user for pharmaceutical platform operations

    Since:
        Version 1.0.0
    """
    admin_user = User(
        id=str(uuid4()),
        username="pharma_admin",
        email="admin@pharmaceutical.com",
        full_name="Pharmaceutical Administrator",
        hashed_password="hashed_admin_password_123",
        role=UserRole.ADMIN,
        is_active=True
    )

    db_session.add(admin_user)
    await db_session.flush()
    return admin_user


@pytest_asyncio.fixture
async def test_pharmaceutical_category(db_session: AsyncSession) -> PharmaceuticalCategory:
    """
    Create test pharmaceutical category for testing.

    Creates pharmaceutical category with clinical trials configuration
    for comprehensive pharmaceutical intelligence testing.

    Args:
        db_session: Database session for pharmaceutical operations

    Returns:
        PharmaceuticalCategory: Test pharmaceutical category

    Since:
        Version 1.0.0
    """
    category = PharmaceuticalCategory(
        name="Clinical Trials & Studies",
        description="Phase I-IV clinical trials, efficacy data, safety profiles",
        display_order=1,
        search_parameters={
            "keywords": ["clinical trial", "phase", "efficacy", "safety"],
            "min_relevance": 0.7,
            "max_results": 50
        },
        processing_rules={
            "min_confidence": 0.8,
            "require_peer_review": True,
            "exclude_preprints": False
        },
        prompt_templates={
            "search": "Find clinical trials for pharmaceutical drug: {drug_name}",
            "analysis": "Analyze clinical trial data for pharmaceutical compliance"
        },
        verification_criteria={
            "required_fields": ["phase", "status", "enrollment"],
            "min_credibility": 0.75
        },
        conflict_resolution_strategy="confidence_weighted"
    )

    db_session.add(category)
    await db_session.flush()
    return category


@pytest_asyncio.fixture
async def test_drug_request(
    db_session: AsyncSession,
    test_user: User
) -> DrugRequest:
    """
    Create test drug request for pharmaceutical testing.

    Creates pharmaceutical drug request for comprehensive intelligence
    testing with audit trail and compliance validation.

    Args:
        db_session: Database session for pharmaceutical operations
        test_user: Test user for pharmaceutical request creation

    Returns:
        DrugRequest: Test pharmaceutical drug request

    Since:
        Version 1.0.0
    """
    drug_request = DrugRequest(
        id=str(uuid4()),
        drug_name="Test Pharmaceutical Compound",
        user_id=test_user.id,
        status=RequestStatus.PROCESSING,
        total_categories=17,
        completed_categories=5,
        failed_categories=["Patent Analysis"],
        priority_categories=[1, 2, 3, 4, 5],
        estimated_completion=datetime.utcnow(),
        request_metadata={
            "test_mode": True,
            "pharmaceutical_class": "analgesic",
            "molecular_weight": 180.16,
            "regulatory_pathway": "FDA_approval"
        }
    )

    db_session.add(drug_request)
    await db_session.flush()
    return drug_request


@pytest_asyncio.fixture
async def test_category_result(
    db_session: AsyncSession,
    test_drug_request: DrugRequest,
    test_pharmaceutical_category: PharmaceuticalCategory
) -> CategoryResult:
    """
    Create test category result for pharmaceutical testing.

    Creates pharmaceutical category result with comprehensive processing
    metrics for regulatory compliance and audit trail testing.

    Args:
        db_session: Database session for pharmaceutical operations
        test_drug_request: Test pharmaceutical drug request
        test_pharmaceutical_category: Test pharmaceutical category

    Returns:
        CategoryResult: Test pharmaceutical category result

    Since:
        Version 1.0.0
    """
    category_result = CategoryResult(
        id=str(uuid4()),
        request_id=test_drug_request.id,
        category_id=test_pharmaceutical_category.id,
        category_name=test_pharmaceutical_category.name,
        summary="Comprehensive clinical trial analysis for pharmaceutical compound showing positive efficacy in Phase III trials with acceptable safety profile.",
        confidence_score=0.87,
        data_quality_score=0.91,
        status=CategoryStatus.COMPLETED,
        processing_time_ms=4500,
        retry_count=0,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        api_calls_made=3,
        token_count=1250,
        cost_estimate=0.062
    )

    db_session.add(category_result)
    await db_session.flush()
    return category_result


@pytest_asyncio.fixture
async def test_source_reference(
    db_session: AsyncSession,
    test_category_result: CategoryResult
) -> SourceReference:
    """
    Create test source reference for pharmaceutical testing.

    Creates pharmaceutical source reference with comprehensive
    attribution and verification data for compliance testing.

    Args:
        db_session: Database session for pharmaceutical operations
        test_category_result: Test pharmaceutical category result

    Returns:
        SourceReference: Test pharmaceutical source reference

    Since:
        Version 1.0.0
    """
    source_reference = SourceReference(
        id=str(uuid4()),
        category_result_id=test_category_result.id,
        api_provider=APIProvider.CHATGPT,
        source_url="https://clinicaltrials.gov/ct2/show/NCT12345678",
        source_title="Phase III Randomized Controlled Trial of Test Pharmaceutical Compound",
        source_type=SourceType.CLINICAL_TRIAL,
        content_snippet="This Phase III randomized controlled trial evaluated the efficacy and safety of the test pharmaceutical compound in 500 patients with the target condition. Primary endpoint demonstrated statistically significant improvement (p<0.001) with acceptable safety profile.",
        relevance_score=0.94,
        credibility_score=0.96,
        published_date=datetime(2023, 8, 15),
        authors="Dr. Sarah Johnson, Dr. Michael Chen, Dr. Lisa Rodriguez",
        journal_name="New England Journal of Medicine",
        doi="10.1056/NEJMoa2023001",
        api_response_id="chatgpt-response-12345",
        verification_status=VerificationStatus.VERIFIED,
        verified_at=datetime.utcnow()
    )

    db_session.add(source_reference)
    await db_session.flush()
    return source_reference


@pytest_asyncio.fixture
async def test_process_tracking(
    db_session: AsyncSession,
    test_drug_request: DrugRequest
) -> ProcessTracking:
    """
    Create test process tracking for pharmaceutical testing.

    Creates pharmaceutical process tracking entry with comprehensive
    correlation data for audit trail and compliance testing.

    Args:
        db_session: Database session for pharmaceutical operations
        test_drug_request: Test pharmaceutical drug request

    Returns:
        ProcessTracking: Test pharmaceutical process tracking

    Since:
        Version 1.0.0
    """
    process_tracking = ProcessTracking(
        id=str(uuid4()),
        request_id=test_drug_request.id,
        process_type="category_processing",
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        correlation_id="test-correlation-12345",
        process_metadata={
            "category": "Clinical Trials & Studies",
            "api_provider": "chatgpt",
            "processing_stage": "source_analysis",
            "pharmaceutical_compliance": True,
            "audit_trail_id": "audit-trail-67890"
        }
    )

    db_session.add(process_tracking)
    await db_session.flush()
    return process_tracking


@pytest_asyncio.fixture
async def test_audit_event(
    db_session: AsyncSession,
    test_drug_request: DrugRequest,
    test_user: User
) -> AuditEvent:
    """
    Create test audit event for pharmaceutical compliance testing.

    Creates pharmaceutical audit event with comprehensive regulatory
    compliance data for immutable audit trail testing.

    Args:
        db_session: Database session for pharmaceutical operations
        test_drug_request: Test pharmaceutical drug request
        test_user: Test user for pharmaceutical audit tracking

    Returns:
        AuditEvent: Test pharmaceutical audit event

    Since:
        Version 1.0.0
    """
    audit_event = AuditEvent(
        id=str(uuid4()),
        request_id=test_drug_request.id,
        event_type=AuditEventType.CREATE,
        event_description="Created pharmaceutical intelligence request with regulatory compliance tracking",
        entity_type="DrugRequest",
        entity_id=str(test_drug_request.id),
        new_values={
            "drug_name": test_drug_request.drug_name,
            "status": test_drug_request.status.value,
            "total_categories": test_drug_request.total_categories,
            "pharmaceutical_compliance": True
        },
        user_id=test_user.id,
        timestamp=datetime.utcnow(),
        correlation_id="test-audit-correlation-123",
        session_id="test-session-456",
        ip_address="192.168.1.100",
        user_agent="CognitoAI-Test-Agent/1.0",
        audit_metadata={
            "test_mode": True,
            "regulatory_compliance": "FDA_CFR_21_Part_11",
            "audit_trail_version": "1.0.0",
            "pharmaceutical_platform": "CognitoAI-Engine"
        }
    )

    db_session.add(audit_event)
    await db_session.flush()
    return audit_event


@pytest.fixture
def pharmaceutical_test_data():
    """
    Provide pharmaceutical test data for comprehensive testing.

    Returns comprehensive pharmaceutical test data including drug names,
    categories, and regulatory compliance scenarios.

    Returns:
        dict: Pharmaceutical test data for comprehensive testing

    Since:
        Version 1.0.0
    """
    return {
        "drug_names": [
            "Aspirin",
            "Metformin",
            "Ibuprofen",
            "Acetaminophen",
            "Atorvastatin",
            "Lisinopril",
            "Levothyroxine",
            "Amlodipine",
            "Simvastatin",
            "Omeprazole"
        ],
        "pharmaceutical_categories": [
            "Clinical Trials & Studies",
            "Drug Interactions & Contraindications",
            "Side Effects & Adverse Events",
            "Pharmacokinetics & Pharmacodynamics",
            "Regulatory Status & Approvals",
            "Patent & Intellectual Property",
            "Manufacturing & Quality Control",
            "Pricing & Market Access",
            "Competitive Analysis",
            "Real-World Evidence"
        ],
        "api_providers": ["chatgpt", "perplexity", "grok", "gemini", "tavily"],
        "source_types": [
            "research_paper",
            "clinical_trial",
            "regulatory",
            "fda_document",
            "ema_document"
        ],
        "regulatory_frameworks": [
            "FDA_CFR_21_Part_11",
            "EMA_GCP_Guidelines",
            "ICH_E6_GCP",
            "ISO_13485",
            "USP_Standards"
        ],
        "compliance_scenarios": {
            "audit_trail_7_years": {
                "retention_days": 2555,
                "immutable_records": True,
                "regulatory_requirement": "FDA CFR 21 Part 11"
            },
            "source_attribution": {
                "required_fields": ["source_url", "api_provider", "extracted_at"],
                "verification_required": True,
                "conflict_resolution": "confidence_weighted"
            },
            "process_correlation": {
                "correlation_id_required": True,
                "parent_child_tracking": True,
                "audit_lineage": True
            }
        }
    }


@pytest.fixture
def pharmaceutical_search_scenarios():
    """
    Provide pharmaceutical search test scenarios.

    Returns comprehensive search scenarios for pharmaceutical intelligence
    testing including complex queries and edge cases.

    Returns:
        dict: Pharmaceutical search scenarios for testing

    Since:
        Version 1.0.0
    """
    return {
        "simple_drug_search": {
            "drug_name": "Aspirin",
            "expected_categories": 17,
            "min_confidence": 0.7,
            "regulatory_compliance": True
        },
        "complex_drug_search": {
            "drug_name": "Pembrolizumab",
            "expected_categories": 17,
            "min_confidence": 0.8,
            "specialized_sources": True,
            "regulatory_complexity": "high"
        },
        "edge_case_searches": {
            "generic_drug": "Ibuprofen",
            "brand_drug": "Advil",
            "combination_drug": "Percocet",
            "orphan_drug": "Spinraza",
            "biosimilar": "Zarxio"
        },
        "search_parameters": {
            "max_api_calls_per_category": 5,
            "timeout_seconds": 300,
            "retry_attempts": 3,
            "rate_limit_buffer": 0.8
        }
    }