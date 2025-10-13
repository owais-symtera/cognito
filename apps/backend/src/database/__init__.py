"""
Database package initialization for CognitoAI Engine.

This package contains all database-related components for the pharmaceutical
intelligence processing platform, including models, repositories, and
database configuration with comprehensive audit trail support.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from .models import (
    Base,
    DrugRequest,
    CategoryResult,
    SourceReference,
    SourceConflict,
    PharmaceuticalCategory,
    User,
    APIUsageLog,
    ProcessTracking,
    AuditEvent,
)

from .connection import (
    get_database_url,
    create_engine,
    get_db_session,
)

__all__ = [
    "Base",
    "DrugRequest",
    "CategoryResult",
    "SourceReference",
    "SourceConflict",
    "PharmaceuticalCategory",
    "User",
    "APIUsageLog",
    "ProcessTracking",
    "AuditEvent",
    "get_database_url",
    "create_engine",
    "get_db_session",
]