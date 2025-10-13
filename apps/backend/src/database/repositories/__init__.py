"""
Repository pattern implementation for CognitoAI Engine pharmaceutical platform.

Provides data access layer with comprehensive audit trail support and
pharmaceutical regulatory compliance for the intelligence platform.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from .base import BaseRepository
from .process_tracking_repo import ProcessTrackingRepository
from .drug_request_repo import DrugRequestRepository
from .category_result_repo import CategoryResultRepository
from .source_reference_repo import SourceReferenceRepository
from .audit_repo import AuditRepository

__all__ = [
    "BaseRepository",
    "ProcessTrackingRepository",
    "DrugRequestRepository",
    "CategoryResultRepository",
    "SourceReferenceRepository",
    "AuditRepository",
]