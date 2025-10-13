"""
Audit logging service for tracking all database operations.

Provides centralized audit trail management for pharmaceutical compliance.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Any
from sqlalchemy import text
import structlog

from ..database.connection import get_db_session

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for managing audit events."""

    @staticmethod
    async def log_event(
        event_type: str,
        entity_type: str,
        entity_id: str,
        event_description: str = "",
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        audit_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Log an audit event to the database.

        Args:
            event_type: Type of audit event (e.g., 'DATA_CREATED', 'DATA_UPDATED')
            entity_type: Type of entity (e.g., 'drug_request', 'category_result')
            entity_id: ID of the entity being audited
            event_description: Description of the event
            user_id: Optional user ID who performed the action
            request_id: Optional request ID for correlation
            ip_address: Optional IP address of the client
            user_agent: Optional user agent string
            old_values: Optional old values before change
            new_values: Optional new values after change
            audit_metadata: Optional additional metadata
            correlation_id: Optional correlation ID for tracking related events
            session_id: Optional session ID

        Returns:
            Audit event ID
        """
        audit_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Generate description if not provided
        if not event_description:
            event_description = f"{event_type} on {entity_type} {entity_id}"

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO audit_events (
                        id, event_type, event_description, entity_type, entity_id,
                        user_id, request_id, timestamp,
                        ip_address, user_agent, old_values, new_values,
                        audit_metadata, correlation_id, session_id
                    )
                    VALUES (
                        :id, :event_type, :description, :entity_type, :entity_id,
                        :user_id, :request_id, :timestamp,
                        :ip_address, :user_agent, :old_values, :new_values,
                        :metadata, :correlation_id, :session_id
                    )
                """), {
                    "id": audit_id,
                    "event_type": event_type,
                    "description": event_description,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "user_id": user_id,
                    "request_id": request_id,
                    "timestamp": now,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "old_values": json.dumps(old_values) if old_values else None,
                    "new_values": json.dumps(new_values) if new_values else None,
                    "metadata": json.dumps(audit_metadata) if audit_metadata else None,
                    "correlation_id": correlation_id or str(uuid.uuid4()),
                    "session_id": session_id
                })

                await session.commit()

                logger.info(
                    "Audit event logged",
                    audit_id=audit_id,
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id
                )

                break

            return audit_id

        except Exception as e:
            logger.error(
                "Failed to log audit event",
                event_type=event_type,
                entity_type=entity_type,
                error=str(e)
            )
            raise

    @staticmethod
    async def get_audit_trail(
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve audit trail for an entity or request.

        Args:
            entity_type: Optional filter by entity type
            entity_id: Optional filter by entity ID
            request_id: Optional filter by request ID
            limit: Maximum number of records to return

        Returns:
            List of audit events
        """
        try:
            query_parts = ["SELECT * FROM audit_events WHERE 1=1"]
            params = {}

            if entity_type:
                query_parts.append("AND entity_type = :entity_type")
                params["entity_type"] = entity_type

            if entity_id:
                query_parts.append("AND entity_id = :entity_id")
                params["entity_id"] = entity_id

            if request_id:
                query_parts.append("AND request_id = :request_id")
                params["request_id"] = request_id

            query_parts.append("ORDER BY timestamp DESC LIMIT :limit")
            params["limit"] = limit

            query = " ".join(query_parts)

            async for session in get_db_session():
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                break

            audit_events = []
            for row in rows:
                audit_events.append({
                    "id": row[0],
                    "event_type": row[1],
                    "entity_type": row[2],
                    "entity_id": row[3],
                    "user_id": row[4],
                    "request_id": row[5],
                    "timestamp": row[6].isoformat() if row[6] else None,
                    "ip_address": row[7],
                    "user_agent": row[8],
                    "changes_made": row[9],
                    "audit_metadata": row[10],
                    "correlation_id": row[11]
                })

            return audit_events

        except Exception as e:
            logger.error("Failed to retrieve audit trail", error=str(e))
            return []