"""
SQLAlchemy models for CognitoAI Engine pharmaceutical intelligence platform.

Comprehensive database models with immutable audit trail support for
pharmaceutical regulatory compliance and 7-year data retention.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    text, func, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .connection import Base


class RequestStatus(str, Enum):
    """
    Enumeration of pharmaceutical drug request processing statuses.

    Defines all possible states for pharmaceutical intelligence
    requests throughout the processing pipeline.

    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CategoryStatus(str, Enum):
    """
    Enumeration of pharmaceutical category processing statuses.

    Defines processing states for individual pharmaceutical categories
    within a drug intelligence request.

    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class APIProvider(str, Enum):
    """
    Enumeration of external API providers for pharmaceutical intelligence.

    Defines all supported AI API providers for pharmaceutical
    data gathering and source attribution.

    Since:
        Version 1.0.0
    """
    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    GROK = "grok"
    GEMINI = "gemini"
    TAVILY = "tavily"


class SourceType(str, Enum):
    """
    Enumeration of pharmaceutical source types for regulatory classification.

    Defines source types for comprehensive pharmaceutical audit trails
    and regulatory compliance reporting.

    Since:
        Version 1.0.0
    """
    RESEARCH_PAPER = "research_paper"
    CLINICAL_TRIAL = "clinical_trial"
    NEWS = "news"
    REGULATORY = "regulatory"
    PATENT = "patent"
    FDA_DOCUMENT = "fda_document"
    EMA_DOCUMENT = "ema_document"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """
    Enumeration of source verification statuses for pharmaceutical compliance.

    Defines verification states for pharmaceutical source authentication
    and credibility assessment.

    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    INVALID = "invalid"
    EXPIRED = "expired"


class AuditEventType(str, Enum):
    """
    Enumeration of audit event types for pharmaceutical compliance.

    Defines all audit events tracked for regulatory compliance
    and immutable pharmaceutical audit trails.

    Since:
        Version 1.0.0
    """
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PROCESS_START = "process_start"
    PROCESS_COMPLETE = "process_complete"
    PROCESS_ERROR = "process_error"
    SOURCE_VERIFICATION = "source_verification"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DATA_EXPORT = "data_export"
    USER_ACCESS = "user_access"


class UserRole(str, Enum):
    """
    Enumeration of user roles for pharmaceutical platform access control.

    Defines role-based access control for pharmaceutical intelligence
    platform operations and audit trail access.

    Since:
        Version 1.0.0
    """
    ADMIN = "admin"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


class User(Base):
    """
    User entity for pharmaceutical intelligence platform access control.

    Manages user authentication, authorization, and audit trail tracking
    for pharmaceutical regulatory compliance requirements.

    Attributes:
        id: Unique user identifier
        username: Unique username for authentication
        email: User email address
        full_name: User's full name
        role: User role for access control
        is_active: Whether user account is active
        created_at: Account creation timestamp
        updated_at: Last account update timestamp
        last_login_at: Last successful login timestamp
        failed_login_attempts: Count of consecutive failed logins

    Since:
        Version 1.0.0
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique user identifier"
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username for authentication"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address"
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User's full name"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole),
        nullable=False,
        default=UserRole.VIEWER,
        doc="User role for access control"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether user account is active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Account creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last account update timestamp"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Last successful login timestamp"
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Count of consecutive failed logins"
    )
    roles: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="List of user roles"
    )
    permissions: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="List of user permissions"
    )

    # Relationships
    drug_requests: Mapped[List["DrugRequest"]] = relationship(
        "DrugRequest",
        back_populates="user",
        doc="Drug requests created by this user"
    )

    __table_args__ = (
        Index('ix_users_role_active', 'role', 'is_active'),
        CheckConstraint('failed_login_attempts >= 0', name='ck_users_failed_attempts_positive'),
    )


class ProcessTracking(Base):
    """
    Process tracking entity for pharmaceutical request correlation.

    Provides comprehensive process correlation and tracking across
    all pharmaceutical intelligence operations for audit compliance.

    Attributes:
        id: Unique process tracking identifier
        request_id: Associated drug request identifier
        process_type: Type of process being tracked
        status: Current process status
        started_at: Process start timestamp
        completed_at: Process completion timestamp
        error_message: Error details if process failed
        correlation_id: External correlation identifier
        parent_process_id: Parent process for hierarchical tracking
        process_metadata: Additional process metadata

    Since:
        Version 1.0.0
    """
    __tablename__ = "process_tracking"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        doc="Unique process tracking identifier"
    )
    request_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Associated analysis request identifier"
    )
    current_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Current processing status"
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Processing progress percentage (0-100)"
    )
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Estimated completion timestamp"
    )
    current_stage_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Current stage start timestamp"
    )
    error_details: Mapped[Optional[str]] = mapped_column(
        Text,
        doc="Error details if process failed"
    )

    # Drug and category tracking
    drug_names: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="List of drug names being processed"
    )
    categories_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=17,
        doc="Total number of categories to process"
    )
    categories_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of categories completed"
    )

    # Stage completion tracking
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Submission timestamp"
    )
    collecting_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Collection stage start"
    )
    collecting_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Collection stage completion"
    )
    verifying_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Verification stage start"
    )
    verifying_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Verification stage completion"
    )
    merging_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Merging stage start"
    )
    merging_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Merging stage completion"
    )
    summarizing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Summarization stage start"
    )
    summarizing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Summarization stage completion"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Process completion timestamp"
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Process failure timestamp"
    )

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp"
    )
    process_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Additional process metadata"
    )

    # Note: Relationships to analysis request can be added when needed

    __table_args__ = (
        Index('ix_process_tracking_request', 'request_id'),
        Index('ix_process_tracking_status', 'current_status'),
        Index('ix_process_tracking_timestamps', 'submitted_at', 'completed_at'),
        Index('ix_process_tracking_status_updated', 'current_status', 'updated_at'),
        CheckConstraint(
            "current_status IN ('submitted', 'collecting', 'verifying', 'merging', 'summarizing', 'completed', 'failed', 'cancelled')",
            name='ck_process_tracking_status_valid'
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name='ck_process_tracking_progress_valid'
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= submitted_at",
            name='ck_process_tracking_completion_after_start'
        ),
    )


class PharmaceuticalCategory(Base):
    """
    Pharmaceutical category configuration entity for dynamic processing.

    Defines the 17 pharmaceutical intelligence categories with
    dynamic configuration for search parameters and processing rules.

    Attributes:
        id: Unique category identifier
        name: Category name
        description: Category description
        display_order: Display order for UI
        is_active: Whether category is active for processing
        search_parameters: JSON configuration for API searches
        processing_rules: JSON rules for data processing
        prompt_templates: Templates for AI API prompts
        verification_criteria: Rules for source verification
        conflict_resolution_strategy: Strategy for resolving conflicts
        created_at: Category creation timestamp
        updated_at: Category last update timestamp

    Since:
        Version 1.0.0
    """
    __tablename__ = "pharmaceutical_categories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique category identifier"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Category name"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Category description"
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Display order for UI"
    )
    phase: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Processing phase (1 or 2)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether category is active for processing"
    )
    search_parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="JSON configuration for API searches"
    )
    processing_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="JSON rules for data processing"
    )
    prompt_templates: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Templates for AI API prompts"
    )
    verification_criteria: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Rules for source verification"
    )
    conflict_resolution_strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="confidence_weighted",
        doc="Strategy for resolving conflicts"
    )
    temperature_strategy: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Temperature variation strategy for searches"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Category creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Category last update timestamp"
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User who last updated the category"
    )

    # Relationships
    category_results: Mapped[List["CategoryResult"]] = relationship(
        "CategoryResult",
        back_populates="category",
        doc="Results for this category"
    )


class CategoryDependency(Base):
    """
    Category dependency configuration for validation.

    Tracks dependencies between pharmaceutical categories to prevent
    disabling categories required by other enabled categories.

    Attributes:
        id: Unique dependency identifier
        dependent_category_id: Category that depends on another
        required_category_id: Category that is required
        description: Description of the dependency relationship
        created_at: Dependency creation timestamp

    Since:
        Version 1.0.0
    """
    __tablename__ = "category_dependencies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique dependency identifier"
    )
    dependent_category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pharmaceutical_categories.id"),
        nullable=False,
        index=True,
        doc="Category that depends on another"
    )
    required_category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pharmaceutical_categories.id"),
        nullable=False,
        index=True,
        doc="Category that is required"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Description of the dependency relationship"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Dependency creation timestamp"
    )

    # Relationships
    dependent_category: Mapped["PharmaceuticalCategory"] = relationship(
        "PharmaceuticalCategory",
        foreign_keys=[dependent_category_id],
        doc="Category that has the dependency"
    )
    required_category: Mapped["PharmaceuticalCategory"] = relationship(
        "PharmaceuticalCategory",
        foreign_keys=[required_category_id],
        doc="Category that is required"
    )


class DrugRequest(Base):
    """
    Primary drug request entity for pharmaceutical intelligence processing.

    Central entity tracking complete pharmaceutical intelligence requests
    with comprehensive audit trail and regulatory compliance support.

    Attributes:
        id: Unique request identifier
        drug_name: Name of pharmaceutical drug
        status: Current request processing status
        created_at: Request creation timestamp
        updated_at: Last request update timestamp
        completed_at: Request completion timestamp
        user_id: User who created the request
        total_categories: Total categories to process
        completed_categories: Successfully completed categories
        failed_categories: List of failed category names
        priority_categories: Prioritized category processing order
        estimated_completion: Estimated completion time
        actual_processing_time: Actual time taken for processing
        metadata: Additional request metadata

    Since:
        Version 1.0.0
    """
    __tablename__ = "drug_requests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique request identifier"
    )
    drug_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Name of pharmaceutical drug"
    )
    status: Mapped[RequestStatus] = mapped_column(
        sa.Enum(RequestStatus),
        nullable=False,
        default=RequestStatus.PENDING,
        index=True,
        doc="Current request processing status"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Request creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last request update timestamp"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Request completion timestamp"
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        index=True,
        doc="User who created the request"
    )
    total_categories: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=17,
        doc="Total categories to process"
    )
    completed_categories: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Successfully completed categories"
    )
    failed_categories: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        doc="List of failed category names"
    )
    priority_categories: Mapped[Optional[List[int]]] = mapped_column(
        ARRAY(Integer),
        doc="Prioritized category processing order"
    )
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Estimated completion time"
    )
    actual_processing_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Actual processing time in seconds"
    )
    request_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Additional request metadata"
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="drug_requests",
        doc="User who created the request"
    )
    category_results: Mapped[List["CategoryResult"]] = relationship(
        "CategoryResult",
        back_populates="drug_request",
        cascade="all, delete-orphan",
        doc="Category processing results"
    )
    # NOTE: ProcessTracking relationship commented out - no FK exists between tables
    # process_tracking_entries: Mapped[List["ProcessTracking"]] = relationship(
    #     "ProcessTracking",
    #     back_populates="drug_request",
    #     cascade="all, delete-orphan",
    #     doc="Process tracking entries"
    # )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="drug_request",
        cascade="all, delete-orphan",
        doc="Audit trail events"
    )

    @hybrid_property
    def progress_percentage(self) -> float:
        """
        Calculate completion progress as percentage.

        Returns:
            float: Completion percentage (0.0 to 100.0)

        Since:
            Version 1.0.0
        """
        if self.total_categories == 0:
            return 0.0
        return (self.completed_categories / self.total_categories) * 100.0

    @hybrid_property
    def is_completed(self) -> bool:
        """
        Check if request processing is completed.

        Returns:
            bool: True if processing is completed

        Since:
            Version 1.0.0
        """
        return self.status in [RequestStatus.COMPLETED, RequestStatus.FAILED]

    __table_args__ = (
        Index('ix_drug_requests_status_created', 'status', 'created_at'),
        Index('ix_drug_requests_user_status', 'user_id', 'status'),
        CheckConstraint('total_categories >= 0', name='ck_drug_requests_total_positive'),
        CheckConstraint('completed_categories >= 0', name='ck_drug_requests_completed_positive'),
        CheckConstraint('completed_categories <= total_categories', name='ck_drug_requests_completed_lte_total'),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name='ck_drug_requests_completion_after_creation'
        ),
        CheckConstraint('actual_processing_time IS NULL OR actual_processing_time >= 0',
                       name='ck_drug_requests_processing_time_positive'),
    )


class CategoryResult(Base):
    """
    Category result entity for individual pharmaceutical category processing.

    Stores results from processing individual pharmaceutical categories
    with comprehensive source tracking and quality metrics.

    Attributes:
        id: Unique result identifier
        request_id: Associated drug request identifier
        category_id: Pharmaceutical category identifier
        category_name: Category name for reference
        summary: Processed category summary
        confidence_score: AI confidence in results
        data_quality_score: Data quality assessment
        status: Category processing status
        processing_time_ms: Processing time in milliseconds
        retry_count: Number of processing retries
        error_message: Error details if processing failed
        started_at: Processing start timestamp
        completed_at: Processing completion timestamp
        api_calls_made: Number of API calls for this category
        token_count: Total tokens used in processing
        cost_estimate: Estimated processing cost

    Since:
        Version 1.0.0
    """
    __tablename__ = "category_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique result identifier"
    )
    request_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("drug_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated drug request identifier"
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pharmaceutical_categories.id"),
        nullable=False,
        index=True,
        doc="Pharmaceutical category identifier"
    )
    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Category name for reference"
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Processed category summary"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="AI confidence in results"
    )
    data_quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Data quality assessment"
    )
    status: Mapped[CategoryStatus] = mapped_column(
        sa.Enum(CategoryStatus),
        nullable=False,
        default=CategoryStatus.PENDING,
        index=True,
        doc="Category processing status"
    )
    processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Processing time in milliseconds"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of processing retries"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        doc="Error details if processing failed"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Processing start timestamp"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Processing completion timestamp"
    )
    api_calls_made: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of API calls for this category"
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total tokens used in processing"
    )
    cost_estimate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Estimated processing cost"
    )

    # Relationships
    drug_request: Mapped["DrugRequest"] = relationship(
        "DrugRequest",
        back_populates="category_results",
        doc="Associated drug request"
    )
    category: Mapped["PharmaceuticalCategory"] = relationship(
        "PharmaceuticalCategory",
        back_populates="category_results",
        doc="Pharmaceutical category configuration"
    )
    source_references: Mapped[List["SourceReference"]] = relationship(
        "SourceReference",
        back_populates="category_result",
        cascade="all, delete-orphan",
        doc="Source references for this result"
    )
    source_conflicts: Mapped[List["SourceConflict"]] = relationship(
        "SourceConflict",
        back_populates="category_result",
        cascade="all, delete-orphan",
        doc="Source conflicts detected"
    )

    __table_args__ = (
        Index('ix_category_results_request_category', 'request_id', 'category_id'),
        Index('ix_category_results_status_started', 'status', 'started_at'),
        UniqueConstraint('request_id', 'category_id', name='uq_category_results_request_category'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0',
                       name='ck_category_results_confidence_range'),
        CheckConstraint('data_quality_score >= 0.0 AND data_quality_score <= 1.0',
                       name='ck_category_results_quality_range'),
        CheckConstraint('processing_time_ms >= 0', name='ck_category_results_time_positive'),
        CheckConstraint('retry_count >= 0', name='ck_category_results_retry_positive'),
        CheckConstraint('api_calls_made >= 0', name='ck_category_results_api_calls_positive'),
        CheckConstraint('token_count >= 0', name='ck_category_results_tokens_positive'),
        CheckConstraint('cost_estimate >= 0.0', name='ck_category_results_cost_positive'),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name='ck_category_results_completion_after_start'
        ),
    )


class SourceReference(Base):
    """
    Source reference entity for pharmaceutical source attribution and tracking.

    Comprehensive source tracking for regulatory compliance and
    pharmaceutical intelligence audit trails.

    Attributes:
        id: Unique source reference identifier
        category_result_id: Associated category result identifier
        api_provider: AI API provider that provided this source
        source_url: Original source URL
        source_title: Title of the source document
        source_type: Type of pharmaceutical source
        content_snippet: Relevant content excerpt
        relevance_score: Relevance to pharmaceutical query
        credibility_score: Source credibility assessment
        published_date: Original publication date
        authors: Source authors
        journal_name: Journal name for research papers
        doi: Digital Object Identifier for papers
        extracted_at: When source was extracted
        api_response_id: API response correlation ID
        verification_status: Source verification status
        verified_at: Verification timestamp
        verified_by: User who verified source

    Since:
        Version 1.0.0
    """
    __tablename__ = "source_references"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique source reference identifier"
    )
    category_result_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("category_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated category result identifier"
    )
    api_provider: Mapped[APIProvider] = mapped_column(
        sa.Enum(APIProvider),
        nullable=False,
        index=True,
        doc="AI API provider that provided this source"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        doc="Original source URL"
    )
    source_title: Mapped[Optional[str]] = mapped_column(
        String(500),
        doc="Title of the source document"
    )
    source_type: Mapped[SourceType] = mapped_column(
        sa.Enum(SourceType),
        nullable=False,
        default=SourceType.OTHER,
        index=True,
        doc="Type of pharmaceutical source"
    )
    content_snippet: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Relevant content excerpt"
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Relevance to pharmaceutical query"
    )
    credibility_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Source credibility assessment"
    )
    published_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Original publication date"
    )
    authors: Mapped[Optional[str]] = mapped_column(
        Text,
        doc="Source authors"
    )
    journal_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        doc="Journal name for research papers"
    )
    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        doc="Digital Object Identifier for papers"
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When source was extracted"
    )
    api_response_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        doc="API response correlation ID"
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        sa.Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
        index=True,
        doc="Source verification status"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Verification timestamp"
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        doc="User who verified source"
    )

    # Relationships
    category_result: Mapped["CategoryResult"] = relationship(
        "CategoryResult",
        back_populates="source_references",
        doc="Associated category result"
    )
    verifier: Mapped[Optional["User"]] = relationship(
        "User",
        doc="User who verified this source"
    )

    __table_args__ = (
        Index('ix_source_references_category_provider', 'category_result_id', 'api_provider'),
        Index('ix_source_references_type_status', 'source_type', 'verification_status'),
        Index('ix_source_references_url_hash', 'source_url'),  # For duplicate detection
        CheckConstraint('relevance_score >= 0.0 AND relevance_score <= 1.0',
                       name='ck_source_references_relevance_range'),
        CheckConstraint('credibility_score >= 0.0 AND credibility_score <= 1.0',
                       name='ck_source_references_credibility_range'),
        CheckConstraint(
            "verified_at IS NULL OR verification_status != 'pending'",
            name='ck_source_references_verified_status'
        ),
    )


class SourceConflict(Base):
    """
    Source conflict entity for pharmaceutical data conflict resolution.

    Tracks and resolves conflicts between different sources for
    pharmaceutical regulatory compliance and data quality assurance.

    Attributes:
        id: Unique conflict identifier
        category_result_id: Associated category result identifier
        conflict_type: Type of conflict detected
        description: Detailed conflict description
        conflicting_sources: List of conflicting source IDs
        resolution_strategy: Strategy used for resolution
        resolution_notes: Notes about conflict resolution
        resolved_at: Resolution timestamp
        resolved_by: User who resolved conflict
        confidence_impact: Impact on overall confidence
        is_critical: Whether conflict is critical for pharmaceutical use

    Since:
        Version 1.0.0
    """
    __tablename__ = "source_conflicts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique conflict identifier"
    )
    category_result_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("category_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated category result identifier"
    )
    conflict_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type of conflict detected"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed conflict description"
    )
    conflicting_sources: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        doc="List of conflicting source IDs"
    )
    resolution_strategy: Mapped[Optional[str]] = mapped_column(
        String(100),
        doc="Strategy used for resolution"
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        doc="Notes about conflict resolution"
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Resolution timestamp"
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        doc="User who resolved conflict"
    )
    confidence_impact: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Impact on overall confidence"
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether conflict is critical for pharmaceutical use"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Conflict detection timestamp"
    )

    # Relationships
    category_result: Mapped["CategoryResult"] = relationship(
        "CategoryResult",
        back_populates="source_conflicts",
        doc="Associated category result"
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User",
        doc="User who resolved this conflict"
    )

    @hybrid_property
    def is_resolved(self) -> bool:
        """
        Check if conflict has been resolved.

        Returns:
            bool: True if conflict is resolved

        Since:
            Version 1.0.0
        """
        return self.resolved_at is not None

    __table_args__ = (
        Index('ix_source_conflicts_category_type', 'category_result_id', 'conflict_type'),
        Index('ix_source_conflicts_critical_unresolved', 'is_critical', 'resolved_at'),
        CheckConstraint(
            "resolved_at IS NULL OR resolution_strategy IS NOT NULL",
            name='ck_source_conflicts_resolution_complete'
        ),
    )


class APIUsageLog(Base):
    """
    API usage log entity for tracking external pharmaceutical API calls.

    Comprehensive logging of all external API usage for rate limiting,
    cost tracking, and pharmaceutical audit trail compliance.

    Attributes:
        id: Unique usage log identifier
        request_id: Associated drug request identifier
        category_result_id: Associated category result identifier
        api_provider: External API provider used
        endpoint: Specific API endpoint called
        request_payload: API request payload
        response_status: HTTP response status code
        response_time_ms: Response time in milliseconds
        token_count: Tokens used in API call
        cost_per_token: Cost per token for this provider
        total_cost: Total cost for this API call
        timestamp: API call timestamp
        error_message: Error message if call failed
        rate_limit_remaining: Remaining rate limit after call
        correlation_id: Correlation ID for tracking

    Since:
        Version 1.0.0
    """
    __tablename__ = "api_usage_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique usage log identifier"
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("drug_requests.id", ondelete="CASCADE"),
        index=True,
        doc="Associated drug request identifier"
    )
    category_result_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("category_results.id", ondelete="CASCADE"),
        index=True,
        doc="Associated category result identifier"
    )
    api_provider: Mapped[APIProvider] = mapped_column(
        sa.Enum(APIProvider),
        nullable=False,
        index=True,
        doc="External API provider used"
    )
    endpoint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Specific API endpoint called"
    )
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="API request payload"
    )
    response_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="HTTP response status code"
    )
    response_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Response time in milliseconds"
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Tokens used in API call"
    )
    cost_per_token: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Cost per token for this provider"
    )
    total_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Total cost for this API call"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="API call timestamp"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        doc="Error message if call failed"
    )
    rate_limit_remaining: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Remaining rate limit after call"
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        doc="Correlation ID for tracking"
    )

    __table_args__ = (
        Index('ix_api_usage_logs_provider_timestamp', 'api_provider', 'timestamp'),
        Index('ix_api_usage_logs_request_timestamp', 'request_id', 'timestamp'),
        Index('ix_api_usage_logs_status_timestamp', 'response_status', 'timestamp'),
        CheckConstraint('response_status >= 100 AND response_status < 600',
                       name='ck_api_usage_logs_valid_status'),
        CheckConstraint('response_time_ms >= 0', name='ck_api_usage_logs_time_positive'),
        CheckConstraint('token_count >= 0', name='ck_api_usage_logs_tokens_positive'),
        CheckConstraint('cost_per_token >= 0.0', name='ck_api_usage_logs_cost_per_token_positive'),
        CheckConstraint('total_cost >= 0.0', name='ck_api_usage_logs_total_cost_positive'),
    )


class AuditEvent(Base):
    """
    Audit event entity for immutable pharmaceutical audit trail.

    Comprehensive audit logging for all database operations with
    pharmaceutical regulatory compliance and 7-year retention support.

    Attributes:
        id: Unique audit event identifier
        request_id: Associated drug request identifier (for correlation)
        event_type: Type of audit event
        event_description: Detailed event description
        entity_type: Type of entity being audited
        entity_id: ID of the entity being audited
        old_values: Entity state before change (JSON)
        new_values: Entity state after change (JSON)
        user_id: User who performed the action
        timestamp: Event timestamp (immutable)
        correlation_id: Process correlation identifier
        session_id: User session identifier
        ip_address: Client IP address
        user_agent: Client user agent
        metadata: Additional audit metadata

    Since:
        Version 1.0.0
    """
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique audit event identifier"
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("drug_requests.id", ondelete="CASCADE"),
        index=True,
        doc="Associated drug request identifier (for correlation)"
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        sa.Enum(AuditEventType),
        nullable=False,
        index=True,
        doc="Type of audit event"
    )
    event_description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        doc="Detailed event description"
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type of entity being audited"
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="ID of the entity being audited"
    )
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Entity state before change (JSON)"
    )
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Entity state after change (JSON)"
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        index=True,
        doc="User who performed the action"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Event timestamp (immutable)"
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        doc="Process correlation identifier"
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        doc="User session identifier"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 support
        doc="Client IP address"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        doc="Client user agent"
    )
    audit_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Additional audit metadata"
    )

    # Relationships
    drug_request: Mapped[Optional["DrugRequest"]] = relationship(
        "DrugRequest",
        back_populates="audit_events",
        doc="Associated drug request"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        doc="User who performed the action"
    )

    __table_args__ = (
        Index('ix_audit_events_entity_timestamp', 'entity_type', 'entity_id', 'timestamp'),
        Index('ix_audit_events_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_audit_events_request_timestamp', 'request_id', 'timestamp'),
        Index('ix_audit_events_correlation', 'correlation_id'),
        # Partitioning by timestamp for performance (requires PostgreSQL partitioning)
        Index('ix_audit_events_timestamp', 'timestamp'),
    )


# Database triggers for immutable audit logging
@event.listens_for(DrugRequest, 'after_insert')
def audit_drug_request_insert(mapper, connection, target):
    """Audit trigger for DrugRequest creation."""
    # This will be implemented as PostgreSQL triggers for performance
    pass


@event.listens_for(DrugRequest, 'after_update')
def audit_drug_request_update(mapper, connection, target):
    """Audit trigger for DrugRequest updates."""
    # This will be implemented as PostgreSQL triggers for performance
    pass


@event.listens_for(CategoryResult, 'after_insert')
def audit_category_result_insert(mapper, connection, target):
    """Audit trigger for CategoryResult creation."""
    # This will be implemented as PostgreSQL triggers for performance
    pass


@event.listens_for(CategoryResult, 'after_update')
def audit_category_result_update(mapper, connection, target):
    """Audit trigger for CategoryResult updates."""
    # This will be implemented as PostgreSQL triggers for performance
    pass


class APIKey(Base):
    """
    API key for pharmaceutical platform authentication.

    Stores hashed API keys for secure authentication
    with usage tracking and rate limiting support.

    Since:
        Version 1.0.0
    """
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Primary key identifier"
    )
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        doc="SHA256 hash of the API key"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="API key name/description"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        doc="Associated user ID"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether API key is active"
    )
    permissions: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="List of granted permissions"
    )
    rate_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Custom rate limit (requests per minute)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="API key creation timestamp"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="API key expiration timestamp"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Last usage timestamp"
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total request count"
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        doc="User who owns this API key"
    )

    __table_args__ = (
        Index('ix_api_keys_user_active', 'user_id', 'is_active'),
        Index('ix_api_keys_expires', 'expires_at'),
    )


class AnalysisRequest(Base):
    """
    Drug analysis request tracking.

    Tracks pharmaceutical analysis requests submitted through
    the API with status, results, and processing metrics.

    Since:
        Version 1.0.0
    """
    __tablename__ = "analysis_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Primary key identifier"
    )
    request_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique request identifier"
    )
    correlation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Correlation ID for request tracking"
    )
    drug_names: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        doc="List of drug names to analyze"
    )
    categories: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="Specific categories requested"
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        doc="Request priority level"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Current processing status"
    )
    api_key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA256 hash of API key used"
    )
    callback_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        doc="Webhook URL for async delivery"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Request creation timestamp"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Processing start timestamp"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Processing completion timestamp"
    )
    estimated_completion_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Estimated processing time in milliseconds"
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Actual processing time in milliseconds"
    )
    progress_percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Processing progress percentage (0-100)"
    )
    results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        doc="Analysis results per drug"
    )
    errors: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="Processing errors if any"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp"
    )

    __table_args__ = (
        Index('ix_analysis_requests_status_created', 'status', 'created_at'),
        Index('ix_analysis_requests_api_key_created', 'api_key_hash', 'created_at'),
        Index('ix_analysis_requests_priority_status', 'priority', 'status'),
    )


class APIProviderConfig(Base):
    """
    Configuration for external API providers.

    Stores API provider settings including rate limits, costs, and
    encrypted credentials for pharmaceutical intelligence gathering.

    Since:
        Version 1.0.0
    """
    __tablename__ = "api_provider_configs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        doc="Unique provider config identifier"
    )
    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        doc="Provider name (chatgpt, perplexity, etc.)"
    )
    enabled_globally: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether provider is enabled globally"
    )

    # Rate limiting configuration
    requests_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        doc="Maximum requests per minute"
    )
    requests_per_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        doc="Maximum requests per hour"
    )
    daily_quota: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Daily request quota if applicable"
    )

    # Cost configuration
    cost_per_request: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Cost per API request in USD"
    )
    cost_per_token: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Cost per token if applicable"
    )

    # API-specific configuration
    config_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Provider-specific configuration"
    )

    # Security
    encrypted_api_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Encrypted API key"
    )
    key_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="API key version for rotation"
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Configuration creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp"
    )

    __table_args__ = (
        CheckConstraint('requests_per_minute > 0', name='check_rpm_positive'),
        CheckConstraint('requests_per_hour > 0', name='check_rph_positive'),
        CheckConstraint('cost_per_request >= 0', name='check_cost_non_negative'),
    )


class CategoryAPIConfig(Base):
    """
    Category-specific API provider configuration.

    Allows enabling/disabling specific API providers for individual
    pharmaceutical categories with custom settings.

    Since:
        Version 1.0.0
    """
    __tablename__ = "category_api_configs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        doc="Unique category-API config identifier"
    )
    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Pharmaceutical category name"
    )
    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="API provider name"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether provider is enabled for this category"
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Provider priority for this category (higher = preferred)"
    )
    custom_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        doc="Category-specific provider configuration overrides"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Configuration creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp"
    )

    __table_args__ = (
        UniqueConstraint('category_name', 'provider_name', name='uq_category_provider'),
        Index('ix_category_api_enabled', 'category_name', 'enabled'),
    )


class APIResponse(Base):
    """
    Raw API response storage for pharmaceutical data persistence.

    Stores complete API responses with metadata for audit trail,
    re-analysis, and regulatory compliance with 7-year retention.

    Since:
        Version 1.0.0
    """
    __tablename__ = "api_responses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique response identifier (UUID)"
    )
    process_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("process_tracking.id"),
        nullable=False,
        index=True,
        doc="Link to process tracking for lineage"
    )
    request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drug_requests.id"),
        nullable=False,
        index=True,
        doc="Original drug request identifier"
    )
    correlation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="Correlation ID for request tracing"
    )

    # API details
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="API provider name (chatgpt, perplexity, etc.)"
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Original search query sent to API"
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Temperature parameter used in API call"
    )
    query_parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Complete query parameters sent to API"
    )

    # Response data (encrypted in production)
    raw_response: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Complete raw API response (encrypted)"
    )
    standardized_response: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Standardized response format"
    )

    # Metadata
    response_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="API response time in milliseconds"
    )
    cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Cost of API call in USD"
    )
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="Token count if applicable"
    )
    result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of results returned"
    )

    # Pharmaceutical context
    pharmaceutical_compound: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Pharmaceutical compound being researched"
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Pharmaceutical category"
    )

    # Quality metrics
    relevance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Relevance score of response (0.0-1.0)"
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Quality score of response (0.0-1.0)"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Confidence in response accuracy (0.0-1.0)"
    )

    # Data integrity
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 checksum of raw response"
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Data integrity validation status"
    )

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Response storage timestamp"
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        doc="Archival timestamp for retention"
    )
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=365*7),
        doc="7-year retention expiry"
    )

    # Relationships
    # NOTE: Relationships commented out - no corresponding back_populates exist in referenced models
    # process_tracking: Mapped["ProcessTracking"] = relationship(
    #     back_populates="api_responses",
    #     doc="Link to process tracking"
    # )
    # drug_request: Mapped["DrugRequest"] = relationship(
    #     back_populates="api_responses",
    #     doc="Link to original drug request"
    # )
    # source_references: Mapped[List["SourceReference"]] = relationship(
    #     back_populates="api_response",
    #     cascade="all, delete-orphan",
    #     doc="Extracted source references"
    # )
    response_metadata: Mapped[Optional["APIResponseMetadata"]] = relationship(
        back_populates="api_response",
        cascade="all, delete-orphan",
        uselist=False,
        doc="Extended metadata"
    )

    __table_args__ = (
        Index('ix_api_responses_compound_category', 'pharmaceutical_compound', 'category'),
        Index('ix_api_responses_created_at', 'created_at'),
        Index('ix_api_responses_provider_created', 'provider', 'created_at'),
        CheckConstraint('relevance_score >= 0 AND relevance_score <= 1', name='check_relevance_range'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 1', name='check_quality_range'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_range'),
    )


class APIResponseMetadata(Base):
    """
    Extended metadata for API responses.

    Stores additional structured metadata for pharmaceutical
    compliance and advanced analytics.

    Since:
        Version 1.0.0
    """
    __tablename__ = "api_response_metadata"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        doc="Metadata record identifier"
    )
    api_response_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("api_responses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        doc="Link to API response"
    )

    # Source tracking
    source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of sources found"
    )
    unique_domains: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        doc="List of unique source domains"
    )
    source_types: Mapped[Dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Count by source type"
    )

    # Content analysis
    key_findings: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text),
        doc="Key findings extracted"
    )
    entity_mentions: Mapped[Optional[Dict[str, List[str]]]] = mapped_column(
        JSONB,
        doc="Pharmaceutical entities mentioned"
    )
    confidence_factors: Mapped[Optional[Dict[str, float]]] = mapped_column(
        JSONB,
        doc="Confidence breakdown by factor"
    )

    # Performance metrics
    parse_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Time to parse response"
    )
    storage_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Storage size of raw response"
    )

    # Compliance tracking
    contains_pii: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Contains personally identifiable information"
    )
    contains_proprietary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Contains proprietary information"
    )
    regulatory_flags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        doc="Regulatory compliance flags"
    )

    # Relationships
    api_response: Mapped["APIResponse"] = relationship(
        back_populates="response_metadata",
        doc="Link to API response"
    )