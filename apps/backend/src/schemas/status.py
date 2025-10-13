"""
Status tracking schemas for pharmaceutical process monitoring.

Defines request/response schemas for process status queries
and tracking with comprehensive audit information.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProcessingStatus(str, Enum):
    """
    Processing status states for pharmaceutical analysis.
    
    Since:
        Version 1.0.0
    """
    SUBMITTED = "submitted"
    COLLECTING = "collecting"      # Gathering data from APIs
    VERIFYING = "verifying"        # Source verification
    MERGING = "merging"            # Conflict resolution and data merging
    SUMMARIZING = "summarizing"    # Final summary generation
    COMPLETED = "completed"        # Successfully finished
    FAILED = "failed"              # Processing failure
    CANCELLED = "cancelled"        # Cancelled by user


class AuditSummary(BaseModel):
    """
    Audit summary for process status.
    
    Since:
        Version 1.0.0
    """
    total_stages_completed: int = Field(
        ...,
        description="Number of processing stages completed"
    )
    current_stage_start_time: datetime = Field(
        ...,
        description="Start time of current processing stage"
    )
    processing_duration: str = Field(
        ...,
        description="Total processing duration in HH:MM:SS format"
    )
    categories_completed: int = Field(
        ...,
        description="Number of categories completed"
    )
    categories_total: int = Field(
        ...,
        description="Total number of categories to process"
    )
    last_activity: datetime = Field(
        ...,
        description="Timestamp of last activity"
    )


class ProcessStatusResponse(BaseModel):
    """
    Response schema for process status query.
    
    Since:
        Version 1.0.0
    """
    process_id: str = Field(..., description="Unique process identifier")
    request_id: str = Field(..., description="Original request identifier")
    current_stage: ProcessingStatus = Field(
        ...,
        description="Current processing stage"
    )
    progress_percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Processing progress percentage (0-100)"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion timestamp"
    )
    error_details: Optional[str] = Field(
        None,
        description="Error details if processing failed"
    )
    audit_summary: AuditSummary = Field(
        ...,
        description="Audit trail summary"
    )
    drug_names: List[str] = Field(
        ...,
        description="List of drugs being analyzed"
    )
    created_at: datetime = Field(..., description="Process creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "process_id": "proc_abc123def456",
                "request_id": "req_xyz789ghi012",
                "current_stage": "collecting",
                "progress_percentage": 45,
                "estimated_completion": "2024-01-26T15:30:00Z",
                "error_details": None,
                "audit_summary": {
                    "total_stages_completed": 1,
                    "current_stage_start_time": "2024-01-26T15:00:00Z",
                    "processing_duration": "00:15:30",
                    "categories_completed": 8,
                    "categories_total": 17,
                    "last_activity": "2024-01-26T15:15:30Z"
                },
                "drug_names": ["aspirin", "ibuprofen"],
                "created_at": "2024-01-26T14:45:00Z",
                "updated_at": "2024-01-26T15:15:30Z"
            }
        }


class ProcessHistoryEntry(BaseModel):
    """
    Individual history entry for process status changes.
    
    Since:
        Version 1.0.0
    """
    timestamp: datetime = Field(..., description="Status change timestamp")
    status: ProcessingStatus = Field(..., description="Processing status")
    progress_percentage: int = Field(..., description="Progress at this point")
    duration_in_stage: Optional[str] = Field(
        None,
        description="Duration spent in this stage"
    )
    message: Optional[str] = Field(
        None,
        description="Status change message or reason"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for this status change"
    )


class ProcessHistoryResponse(BaseModel):
    """
    Response schema for process history query.
    
    Since:
        Version 1.0.0
    """
    process_id: str = Field(..., description="Process identifier")
    request_id: str = Field(..., description="Request identifier")
    history: List[ProcessHistoryEntry] = Field(
        ...,
        description="Chronological list of status changes"
    )
    total_duration: str = Field(
        ...,
        description="Total processing duration"
    )
    final_status: ProcessingStatus = Field(
        ...,
        description="Final processing status"
    )
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class BulkStatusRequest(BaseModel):
    """
    Request schema for bulk status queries.
    
    Since:
        Version 1.0.0
    """
    process_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of process IDs to query (max 100)"
    )
    include_history: bool = Field(
        False,
        description="Include brief history for each process"
    )
    
    @validator('process_ids')
    def validate_unique_ids(cls, v):
        """Ensure process IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate process IDs not allowed")
        return v


class BulkStatusResponse(BaseModel):
    """
    Response schema for bulk status queries.
    
    Since:
        Version 1.0.0
    """
    total_queried: int = Field(..., description="Total process IDs queried")
    found: int = Field(..., description="Number of processes found")
    not_found: List[str] = Field(
        ...,
        description="List of process IDs not found"
    )
    unauthorized: List[str] = Field(
        ...,
        description="List of process IDs user cannot access"
    )
    statuses: List[ProcessStatusResponse] = Field(
        ...,
        description="Status information for found processes"
    )
    query_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of bulk query"
    )


class StatusUpdateRequest(BaseModel):
    """
    Internal request schema for status updates.
    
    Used by background processors to update status.
    
    Since:
        Version 1.0.0
    """
    status: ProcessingStatus = Field(..., description="New status")
    progress_percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Updated progress percentage"
    )
    message: Optional[str] = Field(
        None,
        description="Status update message"
    )
    error_details: Optional[str] = Field(
        None,
        description="Error details if failed"
    )
    categories_completed: Optional[int] = Field(
        None,
        description="Number of categories completed"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Updated estimated completion time"
    )


class ProcessingMetrics(BaseModel):
    """
    Processing metrics for performance monitoring.
    
    Since:
        Version 1.0.0
    """
    average_processing_time: str = Field(
        ...,
        description="Average processing time across requests"
    )
    active_processes: int = Field(
        ...,
        description="Number of currently active processes"
    )
    queued_processes: int = Field(
        ...,
        description="Number of queued processes"
    )
    completed_today: int = Field(
        ...,
        description="Processes completed today"
    )
    failed_today: int = Field(
        ...,
        description="Processes failed today"
    )
    system_load: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current system load (0-1)"
    )