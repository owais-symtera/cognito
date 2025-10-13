"""
Pydantic schemas for pharmaceutical category management.

Defines request/response schemas for category configuration API endpoints
with comprehensive validation for pharmaceutical compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class ConflictResolutionStrategy(str, Enum):
    """
    Conflict resolution strategies for pharmaceutical data.

    Since:
        Version 1.0.0
    """
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MOST_RECENT = "most_recent"
    MOST_CONSERVATIVE = "most_conservative"
    AVERAGE_VALUES = "average_values"
    RANGE_BASED = "range_based"
    WEIGHTED_BY_SAMPLE_SIZE = "weighted_by_sample_size"


class CategoryResponse(BaseModel):
    """
    Pharmaceutical category configuration response.

    Complete category configuration including search parameters,
    processing rules, and prompt templates.

    Since:
        Version 1.0.0
    """
    id: int = Field(..., description="Unique category identifier")
    name: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    display_order: int = Field(..., description="Display order for UI")
    phase: int = Field(..., ge=1, le=2, description="Processing phase (1 or 2)")
    is_active: bool = Field(..., description="Whether category is active")
    search_parameters: Dict[str, Any] = Field(..., description="Search configuration")
    processing_rules: Dict[str, Any] = Field(..., description="Processing rules")
    prompt_templates: Dict[str, Any] = Field(..., description="AI prompt templates")
    verification_criteria: Dict[str, Any] = Field(..., description="Verification rules")
    conflict_resolution_strategy: ConflictResolutionStrategy = Field(
        ...,
        description="Strategy for resolving source conflicts"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Clinical Trials & Studies",
                "description": "Phase I-IV clinical trials, efficacy data",
                "display_order": 1,
                "phase": 1,
                "is_active": True,
                "search_parameters": {
                    "keywords": ["clinical trial", "phase"],
                    "min_relevance": 0.7
                },
                "processing_rules": {
                    "min_confidence": 0.8
                },
                "prompt_templates": {
                    "search": "Find clinical trials for {drug_name}"
                },
                "verification_criteria": {
                    "required_fields": ["phase", "status"]
                },
                "conflict_resolution_strategy": "confidence_weighted"
            }
        }


class CategoryUpdateRequest(BaseModel):
    """
    Request schema for updating category configuration.

    Allows partial updates to category configuration with validation.

    Since:
        Version 1.0.0
    """
    phase: Optional[int] = Field(None, ge=1, le=2, description="Processing phase")
    is_active: Optional[bool] = Field(None, description="Active status")
    search_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Search configuration updates"
    )
    processing_rules: Optional[Dict[str, Any]] = Field(
        None,
        description="Processing rules updates"
    )
    prompt_templates: Optional[Dict[str, Any]] = Field(
        None,
        description="Prompt template updates"
    )
    verification_criteria: Optional[Dict[str, Any]] = Field(
        None,
        description="Verification criteria updates"
    )
    conflict_resolution_strategy: Optional[ConflictResolutionStrategy] = Field(
        None,
        description="Conflict resolution strategy"
    )

    @validator('search_parameters', 'processing_rules', 'prompt_templates', 'verification_criteria')
    def validate_json_fields(cls, v):
        """Ensure JSON fields are dictionaries."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("Must be a dictionary")
        return v


class CategoryStatusRequest(BaseModel):
    """
    Request schema for enabling/disabling categories.

    Since:
        Version 1.0.0
    """
    enabled: bool = Field(..., description="New status for the category")
    reason: Optional[str] = Field(None, description="Reason for status change")


class CategoryDependencyInfo(BaseModel):
    """
    Category dependency information.

    Since:
        Version 1.0.0
    """
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Dependency description")


class CategoryDependencyResponse(BaseModel):
    """
    Response schema for category dependency information.

    Shows both dependencies and dependents for a category.

    Since:
        Version 1.0.0
    """
    category_id: int = Field(..., description="Category being queried")
    depends_on: List[CategoryDependencyInfo] = Field(
        ...,
        description="Categories this one depends on"
    )
    required_by: List[CategoryDependencyInfo] = Field(
        ...,
        description="Categories that depend on this one"
    )


class CategoryExportResponse(BaseModel):
    """
    Response schema for category configuration export.

    Contains all category configurations for backup purposes.

    Since:
        Version 1.0.0
    """
    export_timestamp: str = Field(..., description="Export timestamp")
    export_version: str = Field(..., description="Export format version")
    categories: List[Dict[str, Any]] = Field(
        ...,
        description="All category configurations"
    )


class CategoryImportRequest(BaseModel):
    """
    Request schema for category configuration import.

    Contains category configurations to restore from backup.

    Since:
        Version 1.0.0
    """
    export_timestamp: Optional[str] = Field(
        None,
        description="Original export timestamp"
    )
    export_version: Optional[str] = Field(
        None,
        description="Export format version"
    )
    categories: List[Dict[str, Any]] = Field(
        ...,
        description="Category configurations to import"
    )


class CategoryImportResponse(BaseModel):
    """
    Response schema for category configuration import.

    Reports import results including successes and failures.

    Since:
        Version 1.0.0
    """
    success: bool = Field(..., description="Whether import was successful")
    imported_count: Optional[int] = Field(
        None,
        description="Number of categories imported"
    )
    errors: Optional[List[str]] = Field(
        None,
        description="List of import errors"
    )
    message: Optional[str] = Field(None, description="Import status message")