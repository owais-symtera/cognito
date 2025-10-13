"""
Base repository implementation for CognitoAI Engine pharmaceutical platform.

Provides foundational repository pattern with audit trail support and
pharmaceutical regulatory compliance for all data operations.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Type, TypeVar, Generic, Optional, List, Dict, Any, Union
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import structlog

from ..connection import Base
from ..models import AuditEvent, AuditEventType, ProcessTracking

logger = structlog.get_logger(__name__)

# Type variable for generic repository
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class for pharmaceutical intelligence platform operations.

    Provides common database operations with comprehensive audit trail
    support and pharmaceutical regulatory compliance for all entities.

    Attributes:
        model: SQLAlchemy model class
        db: Async database session
        audit_enabled: Whether audit logging is enabled
        user_id: Current user ID for audit tracking
        correlation_id: Process correlation ID for audit lineage

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Initialize base repository for pharmaceutical data operations.

        Args:
            model: SQLAlchemy model class for this repository
            db: Async database session for pharmaceutical operations
            user_id: Current user ID for comprehensive audit tracking
            correlation_id: Process correlation ID for audit lineage

        Example:
            >>> repo = BaseRepository(DrugRequest, db_session, user_id="user-123")
            >>> request = await repo.create({"drug_name": "Aspirin"})

        Since:
            Version 1.0.0
        """
        self.model = model
        self.db = db
        self.audit_enabled = True
        self.user_id = user_id
        self.correlation_id = correlation_id or str(uuid4())

    async def create(
        self,
        data: Dict[str, Any],
        audit_description: Optional[str] = None
    ) -> ModelType:
        """
        Create new entity with comprehensive pharmaceutical audit trail.

        Creates new database entity with automatic audit logging for
        pharmaceutical regulatory compliance and full change tracking.

        Args:
            data: Entity data dictionary for creation
            audit_description: Custom audit description for regulatory tracking

        Returns:
            ModelType: Created entity with complete pharmaceutical audit trail

        Raises:
            IntegrityError: If entity creation violates database constraints
            SQLAlchemyError: If database operation fails
            ValueError: If required pharmaceutical data is missing

        Example:
            >>> drug_request = await repo.create({
            ...     "drug_name": "Metformin",
            ...     "user_id": "user-123",
            ...     "total_categories": 17
            ... }, audit_description="New pharmaceutical intelligence request")

        Since:
            Version 1.0.0
        """
        try:
            # Generate ID if not provided
            if 'id' not in data:
                data['id'] = str(uuid4())

            # Create entity instance
            entity = self.model(**data)
            self.db.add(entity)

            # Flush to get the ID for audit logging
            await self.db.flush()

            # Create audit trail for pharmaceutical compliance
            if self.audit_enabled:
                await self._create_audit_event(
                    event_type=AuditEventType.CREATE,
                    entity_id=str(entity.id),
                    new_values=data,
                    description=audit_description or f"Created {self.model.__name__}"
                )

            await self.db.commit()

            logger.info(
                "Entity created with pharmaceutical audit trail",
                entity_type=self.model.__name__,
                entity_id=str(entity.id),
                user_id=self.user_id,
                correlation_id=self.correlation_id
            )

            return entity

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                "Entity creation failed - integrity constraint violation",
                entity_type=self.model.__name__,
                error=str(e),
                correlation_id=self.correlation_id
            )
            raise

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "Entity creation failed - database error",
                entity_type=self.model.__name__,
                error=str(e),
                correlation_id=self.correlation_id
            )
            raise

    async def get_by_id(
        self,
        entity_id: Union[str, int],
        load_relationships: bool = False
    ) -> Optional[ModelType]:
        """
        Retrieve entity by ID with optional relationship loading.

        Retrieves pharmaceutical intelligence entity by ID with support
        for eager loading of related data for comprehensive analysis.

        Args:
            entity_id: Unique identifier of the pharmaceutical entity
            load_relationships: Whether to eagerly load entity relationships

        Returns:
            Optional[ModelType]: Entity if found, None otherwise

        Example:
            >>> drug_request = await repo.get_by_id("req-123", load_relationships=True)
            >>> if drug_request:
            ...     print(f"Found request for {drug_request.drug_name}")

        Since:
            Version 1.0.0
        """
        try:
            query = select(self.model).where(self.model.id == entity_id)

            # Add relationship loading for comprehensive pharmaceutical data
            if load_relationships and hasattr(self.model, '__mapper__'):
                relationships = [rel.key for rel in self.model.__mapper__.relationships]
                for rel_name in relationships:
                    query = query.options(selectinload(getattr(self.model, rel_name)))

            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()

            if entity:
                logger.debug(
                    "Entity retrieved for pharmaceutical analysis",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id),
                    has_relationships=load_relationships
                )

            return entity

        except SQLAlchemyError as e:
            logger.error(
                "Entity retrieval failed",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            raise

    async def update(
        self,
        entity_id: Union[str, int],
        data: Dict[str, Any],
        audit_description: Optional[str] = None
    ) -> Optional[ModelType]:
        """
        Update entity with pharmaceutical audit trail compliance.

        Updates pharmaceutical entity with comprehensive audit logging
        including before/after state tracking for regulatory compliance.

        Args:
            entity_id: Unique identifier of entity to update
            data: Update data dictionary with pharmaceutical fields
            audit_description: Custom audit description for regulatory tracking

        Returns:
            Optional[ModelType]: Updated entity or None if not found

        Raises:
            SQLAlchemyError: If database update operation fails
            ValueError: If pharmaceutical update data is invalid

        Example:
            >>> updated_request = await repo.update(
            ...     "req-123",
            ...     {"status": "completed", "completed_at": datetime.utcnow()},
            ...     audit_description="Pharmaceutical processing completed"
            ... )

        Since:
            Version 1.0.0
        """
        try:
            # Get current entity state for audit trail
            current_entity = await self.get_by_id(entity_id)
            if not current_entity:
                logger.warning(
                    "Entity not found for pharmaceutical update",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id)
                )
                return None

            # Capture old values for pharmaceutical audit compliance
            old_values = {}
            if self.audit_enabled:
                for key, value in data.items():
                    if hasattr(current_entity, key):
                        old_values[key] = getattr(current_entity, key)

            # Add update timestamp if model has updated_at field
            if hasattr(self.model, 'updated_at'):
                data['updated_at'] = datetime.utcnow()

            # Perform update
            query = (
                update(self.model)
                .where(self.model.id == entity_id)
                .values(**data)
                .returning(self.model)
            )

            result = await self.db.execute(query)
            updated_entity = result.scalar_one_or_none()

            if updated_entity:
                # Create comprehensive audit trail for pharmaceutical compliance
                if self.audit_enabled:
                    await self._create_audit_event(
                        event_type=AuditEventType.UPDATE,
                        entity_id=str(entity_id),
                        old_values=old_values,
                        new_values=data,
                        description=audit_description or f"Updated {self.model.__name__}"
                    )

                await self.db.commit()

                logger.info(
                    "Entity updated with pharmaceutical audit trail",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id),
                    fields_updated=list(data.keys()),
                    user_id=self.user_id,
                    correlation_id=self.correlation_id
                )

            return updated_entity

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "Entity update failed",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e),
                correlation_id=self.correlation_id
            )
            raise

    async def delete(
        self,
        entity_id: Union[str, int],
        soft_delete: bool = True,
        audit_description: Optional[str] = None
    ) -> bool:
        """
        Delete entity with pharmaceutical audit trail preservation.

        Performs soft delete by default to preserve pharmaceutical audit trails
        or hard delete when explicitly required for data management.

        Args:
            entity_id: Unique identifier of entity to delete
            soft_delete: Whether to perform soft delete (recommended for pharma)
            audit_description: Custom audit description for regulatory tracking

        Returns:
            bool: True if entity was successfully deleted

        Raises:
            SQLAlchemyError: If database delete operation fails

        Note:
            Soft delete is recommended for pharmaceutical compliance to preserve
            complete audit trails and regulatory documentation.

        Example:
            >>> deleted = await repo.delete(
            ...     "req-123",
            ...     soft_delete=True,
            ...     audit_description="Request archived after completion"
            ... )

        Since:
            Version 1.0.0
        """
        try:
            # Get current entity for audit trail
            current_entity = await self.get_by_id(entity_id)
            if not current_entity:
                logger.warning(
                    "Entity not found for pharmaceutical deletion",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id)
                )
                return False

            # Capture entity state for pharmaceutical audit compliance
            old_values = {}
            if self.audit_enabled:
                old_values = {
                    column.name: getattr(current_entity, column.name)
                    for column in current_entity.__table__.columns
                }

            if soft_delete and hasattr(self.model, 'is_active'):
                # Perform soft delete for pharmaceutical audit preservation
                await self.update(
                    entity_id,
                    {'is_active': False},
                    audit_description=audit_description or f"Soft deleted {self.model.__name__}"
                )
                operation = "soft_deleted"

            else:
                # Perform hard delete
                query = delete(self.model).where(self.model.id == entity_id)
                result = await self.db.execute(query)

                if result.rowcount > 0:
                    # Create audit trail before commit
                    if self.audit_enabled:
                        await self._create_audit_event(
                            event_type=AuditEventType.DELETE,
                            entity_id=str(entity_id),
                            old_values=old_values,
                            description=audit_description or f"Hard deleted {self.model.__name__}"
                        )

                    await self.db.commit()
                    operation = "hard_deleted"
                else:
                    return False

            logger.info(
                f"Entity {operation} with pharmaceutical audit trail",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                operation=operation,
                user_id=self.user_id,
                correlation_id=self.correlation_id
            )

            return True

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "Entity deletion failed",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e),
                correlation_id=self.correlation_id
            )
            raise

    async def list_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        List entities with filtering and pagination for pharmaceutical analysis.

        Retrieves pharmaceutical entities with comprehensive filtering,
        pagination, and ordering for regulatory reporting and analysis.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip for pagination
            filters: Filter conditions for pharmaceutical entity queries
            order_by: Field name for result ordering

        Returns:
            List[ModelType]: List of pharmaceutical entities matching criteria

        Example:
            >>> requests = await repo.list_all(
            ...     limit=10,
            ...     filters={"status": "completed"},
            ...     order_by="created_at"
            ... )

        Since:
            Version 1.0.0
        """
        try:
            query = select(self.model)

            # Apply pharmaceutical data filters
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        column = getattr(self.model, key)
                        if isinstance(value, list):
                            filter_conditions.append(column.in_(value))
                        else:
                            filter_conditions.append(column == value)

                if filter_conditions:
                    query = query.where(and_(*filter_conditions))

            # Apply ordering for pharmaceutical regulatory reporting
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                query = query.order_by(order_column.desc())

            # Apply pagination for large pharmaceutical datasets
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.db.execute(query)
            entities = result.scalars().all()

            logger.debug(
                "Entities listed for pharmaceutical analysis",
                entity_type=self.model.__name__,
                count=len(entities),
                filters=filters,
                limit=limit,
                offset=offset
            )

            return list(entities)

        except SQLAlchemyError as e:
            logger.error(
                "Entity listing failed",
                entity_type=self.model.__name__,
                error=str(e),
                filters=filters
            )
            raise

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count entities matching pharmaceutical analysis criteria.

        Returns count of pharmaceutical entities matching specified
        filters for regulatory reporting and analysis.

        Args:
            filters: Filter conditions for pharmaceutical entity counting

        Returns:
            int: Number of entities matching pharmaceutical criteria

        Example:
            >>> completed_count = await repo.count({"status": "completed"})

        Since:
            Version 1.0.0
        """
        try:
            query = select(func.count(self.model.id))

            # Apply pharmaceutical data filters
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        column = getattr(self.model, key)
                        if isinstance(value, list):
                            filter_conditions.append(column.in_(value))
                        else:
                            filter_conditions.append(column == value)

                if filter_conditions:
                    query = query.where(and_(*filter_conditions))

            result = await self.db.execute(query)
            count = result.scalar()

            logger.debug(
                "Entity count retrieved for pharmaceutical analysis",
                entity_type=self.model.__name__,
                count=count,
                filters=filters
            )

            return count or 0

        except SQLAlchemyError as e:
            logger.error(
                "Entity counting failed",
                entity_type=self.model.__name__,
                error=str(e),
                filters=filters
            )
            raise

    async def _create_audit_event(
        self,
        event_type: AuditEventType,
        entity_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> None:
        """
        Create comprehensive audit event for pharmaceutical regulatory compliance.

        Creates immutable audit trail entry for all pharmaceutical intelligence
        platform operations to ensure complete regulatory compliance.

        Args:
            event_type: Type of audit event for regulatory classification
            entity_id: ID of pharmaceutical entity being audited
            old_values: Entity state before change (for updates/deletes)
            new_values: Entity state after change (for creates/updates)
            description: Detailed description of pharmaceutical operation

        Note:
            This method creates immutable audit records required for
            pharmaceutical regulatory compliance and 7-year retention.

        Since:
            Version 1.0.0
        """
        try:
            # Clean values for audit storage (remove non-serializable objects)
            cleaned_old_values = self._clean_audit_values(old_values) if old_values else None
            cleaned_new_values = self._clean_audit_values(new_values) if new_values else None

            audit_event = AuditEvent(
                event_type=event_type,
                event_description=description or f"{event_type.value} {self.model.__name__}",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                old_values=cleaned_old_values,
                new_values=cleaned_new_values,
                user_id=self.user_id,
                correlation_id=self.correlation_id,
                timestamp=datetime.utcnow()
            )

            self.db.add(audit_event)
            await self.db.flush()

        except Exception as e:
            logger.error(
                "Failed to create pharmaceutical audit event",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                event_type=event_type.value,
                error=str(e)
            )
            # Don't raise - audit failure shouldn't block operations
            # but should be logged for pharmaceutical compliance review

    def _clean_audit_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean values for audit storage by removing non-serializable objects.

        Prepares pharmaceutical data values for JSON storage in audit trails
        by converting or removing non-serializable objects.

        Args:
            values: Raw values dictionary from pharmaceutical entity

        Returns:
            Dict[str, Any]: Cleaned values suitable for JSON audit storage

        Since:
            Version 1.0.0
        """
        if not values:
            return {}

        cleaned = {}
        for key, value in values.items():
            if value is None:
                cleaned[key] = None
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                cleaned[key] = value
            else:
                # Convert other types to string for pharmaceutical audit trails
                cleaned[key] = str(value)

        return cleaned