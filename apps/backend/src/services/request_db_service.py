"""
Request service with PostgreSQL database storage.

This service replaces the in-memory request storage with proper PostgreSQL persistence.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database.connection import get_engine, get_db_session
from .audit_service import AuditService

logger = structlog.get_logger(__name__)


class RequestDatabaseService:
    """Service for managing drug analysis requests with PostgreSQL storage."""

    def __init__(self):
        """Initialize request database service."""
        self.engine = None

    def _ensure_engine(self):
        """Ensure database engine is initialized."""
        if self.engine is None:
            self.engine = get_engine()

    async def create_request(
        self,
        request_id: str,
        drug_name: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new drug analysis request in PostgreSQL.

        Args:
            request_id: External request ID (from API)
            drug_name: Name of the drug to analyze
            webhook_url: Optional webhook URL for notifications

        Returns:
            Created request data
        """
        self._ensure_engine()

        # Generate UUID for database, use external request_id in metadata
        db_id = str(uuid.uuid4())
        internal_id = f"INT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()

        request_data = {
            "requestId": request_id,  # External ID for API response
            "drugName": drug_name,
            "webhookUrl": webhook_url,
            "status": "pending",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
            "completedAt": None,
            "progressPercentage": 0,
            "internalId": internal_id,
            "databaseId": db_id  # Internal UUID for database
        }

        try:
            async for session in get_db_session():
                # Insert into drug_requests table with UUID
                await session.execute(text("""
                    INSERT INTO drug_requests (
                        id, drug_name, status,
                        total_categories, completed_categories, failed_categories,
                        created_at, updated_at,
                        request_metadata
                    )
                    VALUES (
                        :id, :drug, :status,
                        :total, :completed, :failed,
                        :created, :updated,
                        :metadata
                    )
                """), {
                    "id": db_id,  # Use UUID for database
                    "drug": drug_name,
                    "status": "pending",
                    "total": 17,  # Total categories
                    "completed": 0,
                    "failed": [],
                    "created": now,
                    "updated": now,
                    "metadata": json.dumps({
                        "webhook_url": webhook_url,
                        "internal_id": internal_id,
                        "external_id": request_id  # Store external ID in metadata
                    })
                })

                await session.commit()
                logger.info(
                    "Request created in database",
                    request_id=request_id,
                    drug_name=drug_name
                )

                break

            # Log audit event (optional - don't fail if audit logging fails)
            try:
                await AuditService.log_event(
                    event_type="create",
                    entity_type="drug_request",
                    entity_id=db_id,
                    event_description=f"Drug request created for {drug_name}",
                    request_id=db_id,
                    audit_metadata={
                        "drug_name": drug_name,
                        "external_id": request_id,
                        "internal_id": internal_id
                    }
                )
            except Exception as audit_error:
                logger.warning("Audit logging failed", error=str(audit_error))

            return request_data

        except Exception as e:
            logger.error(
                "Failed to create request in database",
                request_id=request_id,
                error=str(e)
            )
            raise

    async def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific request by ID from PostgreSQL.

        Args:
            request_id: Request ID to retrieve

        Returns:
            Request data or None if not found
        """
        self._ensure_engine()

        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        id, drug_name, status,
                        completed_categories, total_categories,
                        created_at, updated_at, completed_at,
                        actual_processing_time,
                        request_metadata
                    FROM drug_requests
                    WHERE id = :id
                """), {"id": request_id})

                row = result.fetchone()
                break

            if not row:
                return None

            # Extract metadata
            metadata = row[9] if row[9] else {}

            return {
                "requestId": row[0],
                "drugName": row[1],
                "status": row[2],
                "progressPercentage": int((row[3] / row[4] * 100)) if row[4] > 0 else 0,
                "createdAt": row[5].isoformat() if row[5] else None,
                "updatedAt": row[6].isoformat() if row[6] else None,
                "completedAt": row[7].isoformat() if row[7] else None,
                "processingTime": row[8],
                "webhookUrl": metadata.get("webhook_url"),
                "internalId": metadata.get("internal_id"),
                "completedCategories": row[3],
                "totalCategories": row[4]
            }

        except Exception as e:
            logger.error(
                "Failed to get request from database",
                request_id=request_id,
                error=str(e)
            )
            return None

    async def get_all_requests(self) -> List[Dict[str, Any]]:
        """
        Get all requests from PostgreSQL.

        Returns:
            List of all requests
        """
        self._ensure_engine()

        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        id, drug_name, status,
                        completed_categories, total_categories,
                        created_at, updated_at, completed_at,
                        request_metadata
                    FROM drug_requests
                    ORDER BY created_at DESC
                """))

                rows = result.fetchall()
                break

            requests = []
            for row in rows:
                metadata = row[8] if row[8] else {}

                requests.append({
                    "requestId": row[0],
                    "drugName": row[1],
                    "status": row[2],
                    "progressPercentage": int((row[3] / row[4] * 100)) if row[4] > 0 else 0,
                    "createdAt": row[5].isoformat() if row[5] else None,
                    "updatedAt": row[6].isoformat() if row[6] else None,
                    "completedAt": row[7].isoformat() if row[7] else None,
                    "webhookUrl": metadata.get("webhook_url"),
                    "internalId": metadata.get("internal_id"),
                    "completedCategories": row[3],
                    "totalCategories": row[4]
                })

            return requests

        except Exception as e:
            logger.error("Failed to get all requests from database", error=str(e))
            return []

    async def update_request(
        self,
        request_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update request data in PostgreSQL.

        Args:
            request_id: Request ID to update
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        self._ensure_engine()

        try:
            async for session in get_db_session():
                # Build dynamic update query
                update_fields = []
                params = {"id": request_id, "updated": datetime.utcnow()}

                if "status" in updates:
                    update_fields.append("status = :status")
                    params["status"] = updates["status"]

                if "progressPercentage" in updates:
                    # Calculate completed categories from percentage
                    if "totalCategories" in updates:
                        total = updates["totalCategories"]
                        completed = int(updates["progressPercentage"] / 100 * total)
                        update_fields.append("completed_categories = :completed")
                        params["completed"] = completed

                if "completedAt" in updates:
                    update_fields.append("completed_at = :completed_at")
                    params["completed_at"] = datetime.fromisoformat(updates["completedAt"])

                update_fields.append("updated_at = :updated")

                if not update_fields:
                    return True  # Nothing to update

                query = f"""
                    UPDATE drug_requests
                    SET {', '.join(update_fields)}
                    WHERE id = :id
                """

                result = await session.execute(text(query), params)
                await session.commit()

                logger.info(
                    "Request updated in database",
                    request_id=request_id,
                    updates=updates
                )

                break

            # Log audit event
            await AuditService.log_event(
                event_type="update",
                entity_type="drug_request",
                entity_id=request_id,
                event_description=f"Drug request updated: {', '.join(updates.keys())}",
                request_id=request_id,
                new_values=updates,
                audit_metadata={"update_fields": list(updates.keys())}
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to update request in database",
                request_id=request_id,
                error=str(e)
            )
            return False

    async def delete_request(self, request_id: str) -> bool:
        """
        Delete a request from PostgreSQL.

        Args:
            request_id: Request ID to delete

        Returns:
            True if successful, False otherwise
        """
        self._ensure_engine()

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    DELETE FROM drug_requests
                    WHERE id = :id
                """), {"id": request_id})

                await session.commit()

                logger.info("Request deleted from database", request_id=request_id)
                break

            return True

        except Exception as e:
            logger.error(
                "Failed to delete request from database",
                request_id=request_id,
                error=str(e)
            )
            return False

    async def get_request_status(self, request_id: str) -> Optional[str]:
        """
        Get the status of a request.

        Args:
            request_id: Request ID

        Returns:
            Request status or None if not found
        """
        request = await self.get_request(request_id)
        return request["status"] if request else None

    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests."""
        all_requests = await self.get_all_requests()
        return [r for r in all_requests if r["status"] == "pending"]

    async def get_processing_requests(self) -> List[Dict[str, Any]]:
        """Get all requests currently being processed."""
        all_requests = await self.get_all_requests()
        return [r for r in all_requests if r["status"] == "processing"]

    async def get_completed_requests(self) -> List[Dict[str, Any]]:
        """Get all completed requests."""
        all_requests = await self.get_all_requests()
        return [r for r in all_requests if r["status"] == "completed"]