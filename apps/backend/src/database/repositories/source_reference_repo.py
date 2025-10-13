"""
Source reference repository for CognitoAI Engine pharmaceutical platform.

Comprehensive source tracking and verification repository with pharmaceutical
regulatory compliance and audit trails.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from ..models import SourceReference, APIProvider, SourceType, VerificationStatus

logger = structlog.get_logger(__name__)


class SourceReferenceRepository(BaseRepository[SourceReference]):
    """
    Repository for pharmaceutical source reference operations.

    Provides comprehensive source tracking and verification with audit trails
    and pharmaceutical regulatory compliance for the intelligence platform.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize source reference repository for pharmaceutical operations.

        Args:
            db: Async database session for pharmaceutical operations
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Since:
            Version 1.0.0
        """
        super().__init__(SourceReference, db, user_id, correlation_id)

    async def create_source_reference(
        self,
        category_result_id: str,
        api_provider: APIProvider,
        content_snippet: str,
        source_url: Optional[str] = None,
        source_title: Optional[str] = None,
        source_type: SourceType = SourceType.OTHER,
        relevance_score: float = 0.0,
        credibility_score: float = 0.0,
        api_response_id: Optional[str] = None
    ) -> SourceReference:
        """
        Create new pharmaceutical source reference with tracking.

        Creates comprehensive source reference with audit trail support
        and pharmaceutical regulatory compliance tracking.

        Args:
            category_result_id: Associated category result identifier
            api_provider: AI API provider that provided this source
            content_snippet: Relevant content excerpt from pharmaceutical source
            source_url: Original pharmaceutical source URL
            source_title: Title of the pharmaceutical source document
            source_type: Type of pharmaceutical source for classification
            relevance_score: Relevance to pharmaceutical query (0.0 to 1.0)
            credibility_score: Source credibility assessment (0.0 to 1.0)
            api_response_id: API response correlation ID

        Returns:
            SourceReference: Created source reference with full audit trail

        Since:
            Version 1.0.0
        """
        try:
            source_data = {
                "category_result_id": category_result_id,
                "api_provider": api_provider,
                "source_url": source_url,
                "source_title": source_title,
                "source_type": source_type,
                "content_snippet": content_snippet,
                "relevance_score": relevance_score,
                "credibility_score": credibility_score,
                "api_response_id": api_response_id,
                "verification_status": VerificationStatus.PENDING,
                "extracted_at": datetime.utcnow()
            }

            source_reference = await self.create(
                source_data,
                audit_description=f"Created pharmaceutical source reference from {api_provider.value}"
            )

            logger.info(
                "Pharmaceutical source reference created",
                source_reference_id=source_reference.id,
                category_result_id=category_result_id,
                api_provider=api_provider.value,
                source_type=source_type.value,
                relevance_score=relevance_score,
                credibility_score=credibility_score
            )

            return source_reference

        except Exception as e:
            logger.error(
                "Failed to create pharmaceutical source reference",
                category_result_id=category_result_id,
                api_provider=api_provider.value,
                error=str(e)
            )
            raise

    async def verify_source(
        self,
        source_id: str,
        verification_status: VerificationStatus,
        verified_by: Optional[str] = None,
        verification_notes: Optional[str] = None
    ) -> Optional[SourceReference]:
        """
        Verify pharmaceutical source reference for regulatory compliance.

        Updates source verification status with comprehensive audit logging
        for pharmaceutical regulatory compliance and quality assurance.

        Args:
            source_id: Unique source reference identifier
            verification_status: New verification status for pharmaceutical source
            verified_by: User ID who verified the pharmaceutical source
            verification_notes: Notes about pharmaceutical source verification

        Returns:
            Optional[SourceReference]: Updated pharmaceutical source reference

        Since:
            Version 1.0.0
        """
        try:
            update_data = {
                "verification_status": verification_status,
                "verified_at": datetime.utcnow(),
                "verified_by": verified_by or self.user_id
            }

            verified_source = await self.update(
                source_id,
                update_data,
                audit_description=f"Verified pharmaceutical source with status: {verification_status.value}"
            )

            if verified_source:
                logger.info(
                    "Pharmaceutical source reference verified",
                    source_reference_id=source_id,
                    verification_status=verification_status.value,
                    verified_by=verified_by or self.user_id
                )

            return verified_source

        except Exception as e:
            logger.error(
                "Failed to verify pharmaceutical source reference",
                source_id=source_id,
                verification_status=verification_status.value,
                error=str(e)
            )
            raise

    async def get_category_sources(
        self,
        category_result_id: str,
        verification_status: Optional[VerificationStatus] = None,
        api_provider: Optional[APIProvider] = None
    ) -> List[SourceReference]:
        """
        Get pharmaceutical sources for category result.

        Retrieves all source references for pharmaceutical category result
        with optional filtering for verification status and API provider.

        Args:
            category_result_id: Category result identifier
            verification_status: Optional verification status filter
            api_provider: Optional API provider filter

        Returns:
            List[SourceReference]: Pharmaceutical sources for category result

        Since:
            Version 1.0.0
        """
        try:
            filters = {"category_result_id": category_result_id}

            if verification_status:
                filters["verification_status"] = verification_status

            if api_provider:
                filters["api_provider"] = api_provider

            sources = await self.list_all(
                filters=filters,
                order_by="extracted_at"
            )

            logger.debug(
                "Retrieved pharmaceutical category sources",
                category_result_id=category_result_id,
                source_count=len(sources),
                verification_status=verification_status.value if verification_status else None,
                api_provider=api_provider.value if api_provider else None
            )

            return sources

        except Exception as e:
            logger.error(
                "Failed to retrieve pharmaceutical category sources",
                category_result_id=category_result_id,
                error=str(e)
            )
            raise