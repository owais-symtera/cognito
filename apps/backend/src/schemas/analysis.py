"""
Pydantic schemas for pharmaceutical drug analysis API.

Defines request/response schemas for drug intelligence analysis
with comprehensive validation and categorization.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class AnalysisStatus(str, Enum):
    """
    Status values for analysis requests.
    
    Since:
        Version 1.0.0
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CategoryIdentifier(str, Enum):
    """
    Pharmaceutical category identifiers for analysis.
    
    Since:
        Version 1.0.0
    """
    CLINICAL_TRIALS = "clinical_trials"
    DRUG_INTERACTIONS = "drug_interactions"
    SIDE_EFFECTS = "side_effects"
    PHARMACOKINETICS = "pharmacokinetics"
    REGULATORY_STATUS = "regulatory_status"
    PATENT_INFO = "patent_info"
    MANUFACTURING = "manufacturing"
    PRICING_MARKET = "pricing_market"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    REAL_WORLD_EVIDENCE = "real_world_evidence"
    SAFETY_SURVEILLANCE = "safety_surveillance"
    THERAPEUTIC_GUIDELINES = "therapeutic_guidelines"
    RESEARCH_PIPELINE = "research_pipeline"
    BIOMARKER_INFO = "biomarker_info"
    PATIENT_DEMOGRAPHICS = "patient_demographics"
    HEALTHCARE_ECONOMICS = "healthcare_economics"
    POST_MARKET_SURVEILLANCE = "post_market_surveillance"


class AnalysisRequest(BaseModel):
    """
    Request schema for drug analysis endpoint.
    
    Accepts drug names and optional category filtering for
    targeted pharmaceutical intelligence gathering.
    
    Since:
        Version 1.0.0
    """
    drug_names: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of drug names to analyze (max 10)"
    )
    categories: Optional[List[CategoryIdentifier]] = Field(
        None,
        description="Specific categories to analyze (all if not specified)"
    )
    include_inactive_categories: bool = Field(
        False,
        description="Include results from inactive categories"
    )
    priority: Optional[str] = Field(
        "normal",
        pattern="^(low|normal|high|urgent)$",
        description="Request priority level"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Client-provided correlation ID for tracking"
    )
    callback_url: Optional[str] = Field(
        None,
        pattern="^https?://",
        description="Webhook URL for async result delivery"
    )
    
    @validator('drug_names', each_item=True)
    def validate_drug_name(cls, v):
        """Validate drug name format and length."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Drug name must be at least 2 characters")
        if len(v) > 200:
            raise ValueError("Drug name must not exceed 200 characters")
        return v.strip()
    
    @validator('correlation_id')
    def validate_correlation_id(cls, v):
        """Generate correlation ID if not provided."""
        if v is None:
            return str(uuid.uuid4())
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "drug_names": ["aspirin", "ibuprofen"],
                "categories": ["clinical_trials", "drug_interactions"],
                "priority": "normal",
                "correlation_id": "client-12345"
            }
        }


class CategoryResult(BaseModel):
    """
    Individual category analysis result.
    
    Since:
        Version 1.0.0
    """
    category: CategoryIdentifier = Field(..., description="Category identifier")
    category_name: str = Field(..., description="Human-readable category name")
    status: AnalysisStatus = Field(..., description="Processing status")
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Category-specific analysis data"
    )
    source_count: Optional[int] = Field(
        None,
        description="Number of sources analyzed"
    )
    processing_time_ms: Optional[int] = Field(
        None,
        description="Processing time in milliseconds"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed"
    )


class DrugAnalysisResult(BaseModel):
    """
    Complete analysis result for a single drug.
    
    Since:
        Version 1.0.0
    """
    drug_name: str = Field(..., description="Analyzed drug name")
    status: AnalysisStatus = Field(..., description="Overall status")
    categories: List[CategoryResult] = Field(
        ...,
        description="Results by category"
    )
    total_sources_analyzed: int = Field(
        0,
        description="Total number of sources analyzed"
    )
    processing_time_ms: int = Field(
        ...,
        description="Total processing time in milliseconds"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Completion timestamp"
    )


class AnalysisResponse(BaseModel):
    """
    Response schema for drug analysis endpoint.
    
    Provides immediate acknowledgment with request ID for tracking
    and initial status information.
    
    Since:
        Version 1.0.0
    """
    request_id: str = Field(..., description="Unique request identifier")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    status: AnalysisStatus = Field(..., description="Current request status")
    message: str = Field(..., description="Status message")
    drug_count: int = Field(..., description="Number of drugs being analyzed")
    category_count: int = Field(..., description="Number of categories to process")
    estimated_completion_time_ms: int = Field(
        ...,
        description="Estimated time to complete in milliseconds"
    )
    results_url: Optional[str] = Field(
        None,
        description="URL to retrieve results when ready"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123def456",
                "correlation_id": "client-12345",
                "status": "processing",
                "message": "Analysis initiated for 2 drugs across 17 categories",
                "drug_count": 2,
                "category_count": 17,
                "estimated_completion_time_ms": 1800,
                "results_url": "https://api.cognitoai.com/v1/results/req_abc123def456"
            }
        }


class AnalysisResultsResponse(BaseModel):
    """
    Full results response for completed analysis.
    
    Returns comprehensive analysis data for all requested drugs
    with category-specific intelligence.
    
    Since:
        Version 1.0.0
    """
    request_id: str = Field(..., description="Original request identifier")
    correlation_id: str = Field(..., description="Correlation ID")
    status: AnalysisStatus = Field(..., description="Overall request status")
    drugs: List[DrugAnalysisResult] = Field(
        ...,
        description="Analysis results per drug"
    )
    total_processing_time_ms: int = Field(
        ...,
        description="Total processing time"
    )
    started_at: datetime = Field(..., description="Processing start time")
    completed_at: Optional[datetime] = Field(
        None,
        description="Processing completion time"
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Any errors encountered"
    )
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class AnalysisErrorResponse(BaseModel):
    """
    Error response schema for analysis API.
    
    Since:
        Version 1.0.0
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Request correlation ID if available"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )