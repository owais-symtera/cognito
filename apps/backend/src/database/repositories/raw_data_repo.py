"""
Repository for raw API response data management.

Provides data access layer for API responses with advanced search,
retrieval, and compliance management capabilities.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from ..models import APIResponse, APIResponseMetadata
from .base import BaseRepository

logger = structlog.get_logger(__name__)


class RawDataRepository(BaseRepository[APIResponse]):
    """
    Repository for managing raw API response data.

    Provides advanced search, retention management, and compliance
    features for pharmaceutical data persistence.

    Since:
        Version 1.0.0
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize raw data repository.

        Args:
            db: Database session

        Since:
            Version 1.0.0
        """
        super().__init__(APIResponse, db)

    async def get_with_metadata(self, response_id: str) -> Optional[APIResponse]:
        """
        Get API response with metadata eagerly loaded.

        Args:
            response_id: Response identifier

        Returns:
            API response with metadata or None

        Since:
            Version 1.0.0
        """
        query = select(self.model).options(
            selectinload(self.model.metadata)
        ).where(self.model.id == response_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_process_id(self, process_id: str) -> List[APIResponse]:
        """
        Get all API responses for a process.

        Args:
            process_id: Process tracking ID

        Returns:
            List of API responses

        Since:
            Version 1.0.0
        """
        query = select(self.model).where(
            self.model.process_id == process_id
        ).order_by(self.model.created_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_request_id(self, request_id: str) -> List[APIResponse]:
        """
        Get all API responses for a drug request.

        Args:
            request_id: Drug request ID

        Returns:
            List of API responses

        Since:
            Version 1.0.0
        """
        query = select(self.model).options(
            selectinload(self.model.metadata)
        ).where(
            self.model.request_id == request_id
        ).order_by(self.model.created_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_compound(
        self,
        compound: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[APIResponse]:
        """
        Search responses by pharmaceutical compound.

        Args:
            compound: Drug compound name
            category: Optional category filter
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum results

        Returns:
            List of matching responses

        Since:
            Version 1.0.0
        """
        conditions = [
            self.model.pharmaceutical_compound.ilike(f'%{compound}%'),
            self.model.is_valid == True,
            self.model.archived_at.is_(None)
        ]

        if category:
            conditions.append(self.model.category == category)

        if start_date:
            conditions.append(self.model.created_at >= start_date)

        if end_date:
            conditions.append(self.model.created_at <= end_date)

        query = select(self.model).where(
            and_(*conditions)
        ).order_by(
            self.model.created_at.desc()
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_correlation_id(self, correlation_id: str) -> List[APIResponse]:
        """
        Get all responses for a correlation ID (request trace).

        Args:
            correlation_id: Request correlation ID

        Returns:
            List of related API responses

        Since:
            Version 1.0.0
        """
        query = select(self.model).where(
            self.model.correlation_id == correlation_id
        ).order_by(self.model.created_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_cost_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = 'provider'
    ) -> List[Dict[str, Any]]:
        """
        Get cost summary for date range.

        Args:
            start_date: Start date
            end_date: End date
            group_by: Group by provider, category, or compound

        Returns:
            Cost summary data

        Since:
            Version 1.0.0
        """
        if group_by == 'provider':
            group_column = self.model.provider
        elif group_by == 'category':
            group_column = self.model.category
        elif group_by == 'compound':
            group_column = self.model.pharmaceutical_compound
        else:
            raise ValueError(f"Invalid group_by: {group_by}")

        query = select(
            group_column.label('group_name'),
            func.count(self.model.id).label('request_count'),
            func.sum(self.model.cost).label('total_cost'),
            func.avg(self.model.cost).label('avg_cost'),
            func.sum(self.model.response_time_ms).label('total_time_ms')
        ).where(
            and_(
                self.model.created_at >= start_date,
                self.model.created_at <= end_date
            )
        ).group_by(group_column)

        result = await self.db.execute(query)

        return [
            {
                'group_name': row.group_name,
                'request_count': row.request_count,
                'total_cost': float(row.total_cost) if row.total_cost else 0,
                'avg_cost': float(row.avg_cost) if row.avg_cost else 0,
                'total_time_ms': row.total_time_ms
            }
            for row in result
        ]

    async def get_quality_metrics(
        self,
        provider: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get quality metrics for responses.

        Args:
            provider: Optional provider filter
            category: Optional category filter

        Returns:
            Quality metrics summary

        Since:
            Version 1.0.0
        """
        conditions = [self.model.is_valid == True]

        if provider:
            conditions.append(self.model.provider == provider)

        if category:
            conditions.append(self.model.category == category)

        query = select(
            func.count(self.model.id).label('total_responses'),
            func.avg(self.model.relevance_score).label('avg_relevance'),
            func.avg(self.model.quality_score).label('avg_quality'),
            func.avg(self.model.confidence_score).label('avg_confidence'),
            func.avg(self.model.response_time_ms).label('avg_response_time')
        ).where(and_(*conditions))

        result = await self.db.execute(query)
        row = result.one()

        return {
            'total_responses': row.total_responses,
            'avg_relevance_score': float(row.avg_relevance) if row.avg_relevance else 0,
            'avg_quality_score': float(row.avg_quality) if row.avg_quality else 0,
            'avg_confidence_score': float(row.avg_confidence) if row.avg_confidence else 0,
            'avg_response_time_ms': float(row.avg_response_time) if row.avg_response_time else 0
        }

    async def get_retention_candidates(
        self,
        days_old: int = 365
    ) -> List[APIResponse]:
        """
        Get responses eligible for archival.

        Args:
            days_old: Age threshold in days

        Returns:
            List of responses to archive

        Since:
            Version 1.0.0
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        query = select(self.model).where(
            and_(
                self.model.created_at < cutoff_date,
                self.model.archived_at.is_(None)
            )
        ).limit(1000)  # Process in batches

        result = await self.db.execute(query)
        return result.scalars().all()

    async def archive_responses(self, response_ids: List[str]) -> int:
        """
        Archive multiple responses.

        Args:
            response_ids: List of response IDs to archive

        Returns:
            Number of responses archived

        Since:
            Version 1.0.0
        """
        if not response_ids:
            return 0

        stmt = update(self.model).where(
            self.model.id.in_(response_ids)
        ).values(
            archived_at=datetime.utcnow()
        )

        result = await self.db.execute(stmt)

        # Log archival for audit trail
        await self.log_audit_trail(
            entity_type="APIResponse",
            entity_id=f"batch_{len(response_ids)}",
            action="archive",
            changes={'count': result.rowcount}
        )

        await self.db.commit()
        return result.rowcount

    async def delete_expired_responses(self) -> int:
        """
        Delete responses past retention period.

        Returns:
            Number of responses deleted

        Since:
            Version 1.0.0
        """
        # Only delete if past 7-year retention AND archived
        stmt = delete(self.model).where(
            and_(
                self.model.retention_expires_at < datetime.utcnow(),
                self.model.archived_at.isnot(None)
            )
        )

        result = await self.db.execute(stmt)

        if result.rowcount > 0:
            await self.log_audit_trail(
                entity_type="APIResponse",
                entity_id="retention_cleanup",
                action="delete",
                changes={'count': result.rowcount}
            )

        await self.db.commit()
        return result.rowcount

    async def get_duplicate_responses(
        self,
        compound: str,
        category: str,
        provider: str
    ) -> List[Tuple[str, int]]:
        """
        Find potential duplicate responses.

        Args:
            compound: Drug compound
            category: Category
            provider: Provider name

        Returns:
            List of (checksum, count) for duplicates

        Since:
            Version 1.0.0
        """
        query = select(
            self.model.checksum,
            func.count(self.model.id).label('count')
        ).where(
            and_(
                self.model.pharmaceutical_compound == compound,
                self.model.category == category,
                self.model.provider == provider
            )
        ).group_by(
            self.model.checksum
        ).having(
            func.count(self.model.id) > 1
        )

        result = await self.db.execute(query)

        return [(row.checksum, row.count) for row in result]

    async def validate_integrity_batch(
        self,
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        Validate data integrity for a batch of responses.

        Args:
            batch_size: Number of responses to validate

        Returns:
            Tuple of (valid_count, invalid_count)

        Since:
            Version 1.0.0
        """
        import hashlib
        import json

        # Get unvalidated responses
        query = select(self.model).where(
            self.model.is_valid == True
        ).limit(batch_size)

        result = await self.db.execute(query)
        responses = result.scalars().all()

        valid_count = 0
        invalid_count = 0

        for response in responses:
            # Recalculate checksum
            raw_json = json.dumps(response.raw_response, sort_keys=True)
            current_checksum = hashlib.sha256(raw_json.encode()).hexdigest()

            if current_checksum == response.checksum:
                valid_count += 1
            else:
                invalid_count += 1
                response.is_valid = False
                logger.warning(
                    "Data integrity validation failed",
                    response_id=response.id,
                    expected=response.checksum,
                    actual=current_checksum
                )

        await self.db.commit()

        return valid_count, invalid_count

    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.

        Returns:
            Storage statistics

        Since:
            Version 1.0.0
        """
        # Total storage from metadata
        storage_query = select(
            func.count(APIResponseMetadata.id).label('total_metadata_records'),
            func.sum(APIResponseMetadata.storage_size_bytes).label('total_size'),
            func.avg(APIResponseMetadata.storage_size_bytes).label('avg_size')
        )

        storage_result = await self.db.execute(storage_query)
        storage = storage_result.one()

        # Response counts by status
        status_query = select(
            func.count(self.model.id).label('total'),
            func.sum(func.cast(self.model.archived_at.isnot(None), sa.Integer)).label('archived'),
            func.sum(func.cast(self.model.is_valid == False, sa.Integer)).label('invalid')
        )

        status_result = await self.db.execute(status_query)
        status = status_result.one()

        return {
            'total_responses': status.total,
            'active_responses': status.total - (status.archived or 0),
            'archived_responses': status.archived or 0,
            'invalid_responses': status.invalid or 0,
            'total_storage_bytes': int(storage.total_size) if storage.total_size else 0,
            'average_size_bytes': int(storage.avg_size) if storage.avg_size else 0,
            'total_storage_gb': float(storage.total_size / (1024**3)) if storage.total_size else 0
        }