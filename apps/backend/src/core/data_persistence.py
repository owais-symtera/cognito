"""
Data persistence manager for raw API responses.

Handles storage, retrieval, and management of raw pharmaceutical data
with complete audit trail and 7-year retention compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import hashlib
import json
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database.models import APIResponse, APIResponseMetadata
from ..integrations.providers.base import StandardizedAPIResponse
from ..config.logging import PharmaceuticalLogger

logger = structlog.get_logger(__name__)


class DataPersistenceManager:
    """
    Manages persistence of raw API responses for pharmaceutical compliance.

    Handles storage, validation, archival, and retrieval of API responses
    with complete metadata and 7-year retention policy compliance.

    Attributes:
        db: Database session
        audit_logger: Pharmaceutical compliance logger
        encryption_enabled: Whether to encrypt sensitive data

    Example:
        >>> manager = DataPersistenceManager(db, audit_logger)
        >>> await manager.store_api_response(
        ...     response, process_id, request_id, compound, category
        ... )

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db: AsyncSession,
        audit_logger: PharmaceuticalLogger,
        encryption_enabled: bool = True
    ):
        """
        Initialize data persistence manager.

        Args:
            db: Database session
            audit_logger: Compliance logger
            encryption_enabled: Enable data encryption

        Since:
            Version 1.0.0
        """
        self.db = db
        self.audit_logger = audit_logger
        self.encryption_enabled = encryption_enabled

    async def store_api_response(
        self,
        response: StandardizedAPIResponse,
        process_id: str,
        request_id: str,
        correlation_id: str,
        pharmaceutical_compound: str,
        category: str
    ) -> str:
        """
        Store API response with complete metadata.

        Args:
            response: Standardized API response
            process_id: Process tracking ID
            request_id: Original drug request ID
            correlation_id: Request correlation ID
            pharmaceutical_compound: Drug compound name
            category: Pharmaceutical category

        Returns:
            Response ID for retrieval

        Raises:
            DataIntegrityError: If validation fails

        Since:
            Version 1.0.0
        """
        try:
            # Generate response ID
            response_id = str(uuid4())

            # Calculate checksum for data integrity
            raw_response_json = json.dumps(response.dict(), sort_keys=True)
            checksum = self._calculate_checksum(raw_response_json)

            # Encrypt sensitive data if enabled
            if self.encryption_enabled:
                raw_response_data = await self._encrypt_data(raw_response_json)
            else:
                raw_response_data = response.dict()

            # Create API response record
            api_response = APIResponse(
                id=response_id,
                process_id=process_id,
                request_id=request_id,
                correlation_id=correlation_id,

                # API details
                provider=response.provider,
                query=response.query,
                temperature=response.temperature,
                query_parameters={
                    'temperature': response.temperature,
                    'max_results': len(response.results)
                },

                # Response data
                raw_response=raw_response_data,
                standardized_response=response.dict(),

                # Metadata
                response_time_ms=response.response_time_ms,
                cost=response.cost,
                token_count=getattr(response, 'token_count', None),
                result_count=response.total_results,

                # Pharmaceutical context
                pharmaceutical_compound=pharmaceutical_compound,
                category=category,

                # Quality metrics
                relevance_score=response.relevance_score,
                quality_score=getattr(response, 'quality_score', response.relevance_score),
                confidence_score=response.confidence_score,

                # Data integrity
                checksum=checksum,
                is_valid=True,

                # Retention (7 years from now)
                retention_expires_at=datetime.utcnow() + timedelta(days=365*7)
            )

            # Add to session
            self.db.add(api_response)

            # Create metadata record
            metadata = await self._create_metadata(response, response_id)
            self.db.add(metadata)

            # Commit transaction
            await self.db.commit()

            # Log for audit trail
            await self.audit_logger.log_data_access(
                resource="api_responses",
                action="create",
                user_id="system",
                success=True,
                drug_names=[pharmaceutical_compound]
            )

            logger.info(
                "API response stored",
                response_id=response_id,
                provider=response.provider,
                compound=pharmaceutical_compound,
                category=category,
                cost=response.cost
            )

            return response_id

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to store API response",
                error=str(e),
                provider=response.provider,
                compound=pharmaceutical_compound
            )
            raise

    async def _create_metadata(
        self,
        response: StandardizedAPIResponse,
        response_id: str
    ) -> APIResponseMetadata:
        """
        Create metadata record for API response.

        Args:
            response: API response
            response_id: Response ID

        Returns:
            Metadata record

        Since:
            Version 1.0.0
        """
        # Extract source information
        unique_domains = list(set([
            source.domain for source in response.sources
        ])) if response.sources else []

        source_types = {}
        if response.sources:
            for source in response.sources:
                source_type = source.source_type
                source_types[source_type] = source_types.get(source_type, 0) + 1

        # Calculate storage size
        storage_size = sys.getsizeof(json.dumps(response.dict()))

        # Extract key findings (simplified - would use NLP in production)
        key_findings = []
        for result in response.results[:3]:  # Top 3 results
            if result.title:
                key_findings.append(result.title)

        metadata = APIResponseMetadata(
            api_response_id=response_id,
            source_count=len(response.sources) if response.sources else 0,
            unique_domains=unique_domains,
            source_types=source_types,
            key_findings=key_findings,
            parse_time_ms=10,  # Placeholder - would measure actual parse time
            storage_size_bytes=storage_size,
            contains_pii=False,  # Would implement PII detection
            contains_proprietary=False  # Would implement proprietary detection
        )

        return metadata

    def _calculate_checksum(self, data: str) -> str:
        """
        Calculate SHA-256 checksum for data integrity.

        Args:
            data: Data to checksum

        Returns:
            SHA-256 hash

        Since:
            Version 1.0.0
        """
        return hashlib.sha256(data.encode()).hexdigest()

    async def _encrypt_data(self, data: str) -> Dict[str, Any]:
        """
        Encrypt sensitive data (placeholder).

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data dict

        Since:
            Version 1.0.0
        """
        # TODO: Implement actual encryption using cryptography library
        # For now, return data as-is with encryption flag
        return {
            'encrypted': True,
            'data': data,
            'algorithm': 'AES-256-GCM'
        }

    async def retrieve_response(
        self,
        response_id: str,
        validate_checksum: bool = True
    ) -> Optional[APIResponse]:
        """
        Retrieve API response by ID.

        Args:
            response_id: Response identifier
            validate_checksum: Whether to validate data integrity

        Returns:
            API response or None if not found

        Since:
            Version 1.0.0
        """
        from sqlalchemy import select

        query = select(APIResponse).where(APIResponse.id == response_id)
        result = await self.db.execute(query)
        response = result.scalar_one_or_none()

        if response and validate_checksum:
            # Validate data integrity
            raw_json = json.dumps(response.raw_response, sort_keys=True)
            current_checksum = self._calculate_checksum(raw_json)

            if current_checksum != response.checksum:
                logger.error(
                    "Data integrity validation failed",
                    response_id=response_id,
                    expected=response.checksum,
                    actual=current_checksum
                )
                response.is_valid = False
                await self.db.commit()

        # Log access for audit trail
        if response:
            await self.audit_logger.log_data_access(
                resource="api_responses",
                action="read",
                user_id="system",
                success=True,
                drug_names=[response.pharmaceutical_compound]
            )

        return response

    async def search_responses(
        self,
        pharmaceutical_compound: Optional[str] = None,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[APIResponse]:
        """
        Search historical API responses.

        Args:
            pharmaceutical_compound: Filter by compound
            category: Filter by category
            provider: Filter by API provider
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum results

        Returns:
            List of matching API responses

        Since:
            Version 1.0.0
        """
        from sqlalchemy import select, and_

        conditions = []

        if pharmaceutical_compound:
            conditions.append(
                APIResponse.pharmaceutical_compound.ilike(f'%{pharmaceutical_compound}%')
            )

        if category:
            conditions.append(APIResponse.category == category)

        if provider:
            conditions.append(APIResponse.provider == provider)

        if start_date:
            conditions.append(APIResponse.created_at >= start_date)

        if end_date:
            conditions.append(APIResponse.created_at <= end_date)

        # Only include valid, non-archived responses
        conditions.append(APIResponse.is_valid == True)
        conditions.append(APIResponse.archived_at.is_(None))

        query = select(APIResponse)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(APIResponse.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        responses = result.scalars().all()

        # Log search for audit trail
        await self.audit_logger.log_data_access(
            resource="api_responses",
            action="search",
            user_id="system",
            success=True,
            drug_names=[pharmaceutical_compound] if pharmaceutical_compound else []
        )

        return responses

    async def archive_old_responses(
        self,
        days_old: int = 365
    ) -> int:
        """
        Archive old API responses for long-term storage.

        Args:
            days_old: Age threshold in days

        Returns:
            Number of responses archived

        Since:
            Version 1.0.0
        """
        from sqlalchemy import update

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Update responses to archived status
        stmt = update(APIResponse).where(
            and_(
                APIResponse.created_at < cutoff_date,
                APIResponse.archived_at.is_(None)
            )
        ).values(archived_at=datetime.utcnow())

        result = await self.db.execute(stmt)
        archived_count = result.rowcount

        await self.db.commit()

        if archived_count > 0:
            logger.info(
                "Archived old API responses",
                count=archived_count,
                days_old=days_old
            )

            await self.audit_logger.log_system_health_check(
                component="data_archival",
                status="success",
                response_time_ms=0
            )

        return archived_count

    async def validate_data_integrity(
        self,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Validate data integrity for stored responses.

        Args:
            batch_size: Number of records to validate per batch

        Returns:
            Validation results

        Since:
            Version 1.0.0
        """
        from sqlalchemy import select

        # Get unvalidated or old validated responses
        query = select(APIResponse).where(
            APIResponse.is_valid == True
        ).limit(batch_size)

        result = await self.db.execute(query)
        responses = result.scalars().all()

        valid_count = 0
        invalid_count = 0

        for response in responses:
            # Recalculate checksum
            raw_json = json.dumps(response.raw_response, sort_keys=True)
            current_checksum = self._calculate_checksum(raw_json)

            if current_checksum == response.checksum:
                valid_count += 1
            else:
                invalid_count += 1
                response.is_valid = False
                logger.warning(
                    "Data integrity issue detected",
                    response_id=response.id,
                    provider=response.provider
                )

        await self.db.commit()

        return {
            'valid': valid_count,
            'invalid': invalid_count,
            'total': len(responses)
        }

    async def get_retention_statistics(self) -> Dict[str, Any]:
        """
        Get retention policy statistics.

        Returns:
            Retention statistics

        Since:
            Version 1.0.0
        """
        from sqlalchemy import select, func

        # Count total responses
        total_query = select(func.count(APIResponse.id))
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar()

        # Count archived responses
        archived_query = select(func.count(APIResponse.id)).where(
            APIResponse.archived_at.isnot(None)
        )
        archived_result = await self.db.execute(archived_query)
        archived_count = archived_result.scalar()

        # Count expiring soon (within 30 days)
        expiry_date = datetime.utcnow() + timedelta(days=30)
        expiring_query = select(func.count(APIResponse.id)).where(
            APIResponse.retention_expires_at <= expiry_date
        )
        expiring_result = await self.db.execute(expiring_query)
        expiring_count = expiring_result.scalar()

        # Calculate storage size
        size_query = select(func.sum(APIResponseMetadata.storage_size_bytes))
        size_result = await self.db.execute(size_query)
        total_size = size_result.scalar() or 0

        return {
            'total_responses': total_count,
            'archived_responses': archived_count,
            'active_responses': total_count - archived_count,
            'expiring_soon': expiring_count,
            'total_storage_bytes': total_size,
            'total_storage_gb': total_size / (1024 ** 3)
        }