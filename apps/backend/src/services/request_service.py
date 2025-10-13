"""Request service for managing drug analysis requests."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..services.provider_service import ProviderService


class RequestService:
    """Service for managing drug analysis requests."""

    def __init__(self, provider_service: ProviderService):
        """Initialize request service."""
        self.provider_service = provider_service
        # In-memory storage (replace with database in production)
        self.requests_db: Dict[str, Dict[str, Any]] = {}

    def create_request(
        self,
        request_id: str,
        drug_name: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new drug analysis request."""
        internal_id = f"INT-{uuid.uuid4().hex[:8].upper()}"

        request_data = {
            "requestId": request_id,
            "drugName": drug_name,
            "webhookUrl": webhook_url,
            "status": "pending",
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "completedAt": None,
            "progressPercentage": 0,
            "internalId": internal_id
        }

        self.requests_db[request_id] = request_data
        return request_data

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific request by ID."""
        return self.requests_db.get(request_id)

    def get_all_requests(self) -> List[Dict[str, Any]]:
        """Get all requests."""
        return list(self.requests_db.values())

    def update_request(
        self,
        request_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update request data."""
        if request_id not in self.requests_db:
            return False

        request = self.requests_db[request_id]

        # Update allowed fields
        if "status" in updates:
            request["status"] = updates["status"]

        if "progressPercentage" in updates:
            request["progressPercentage"] = updates["progressPercentage"]

        if "completedAt" in updates:
            request["completedAt"] = updates["completedAt"]

        # Always update timestamp
        request["updatedAt"] = datetime.now().isoformat()

        return True

    def delete_request(self, request_id: str) -> bool:
        """Delete a request."""
        if request_id in self.requests_db:
            del self.requests_db[request_id]
            return True
        return False

    async def process_request(self, request_id: str) -> bool:
        """Process a drug analysis request."""
        request = self.get_request(request_id)
        if not request:
            return False

        # Update status to processing
        self.update_request(request_id, {
            "status": "processing",
            "progressPercentage": 10
        })

        try:
            # Process drug through all enabled categories with all enabled providers
            drug_name = request["drugName"]
            api_responses = await self.provider_service.process_drug_with_categories(drug_name)

            # Update progress
            self.update_request(request_id, {
                "progressPercentage": 50
            })

            # Store results (in production, this would go to database)
            request["apiResponses"] = api_responses

            # Mark as completed
            self.update_request(request_id, {
                "status": "completed",
                "progressPercentage": 100,
                "completedAt": datetime.now().isoformat()
            })

            return True

        except Exception as e:
            print(f"Error processing request {request_id}: {e}")
            self.update_request(request_id, {
                "status": "failed",
                "progressPercentage": 0,
                "error": str(e)
            })
            return False

    def get_request_status(self, request_id: str) -> Optional[str]:
        """Get the status of a request."""
        request = self.get_request(request_id)
        return request["status"] if request else None

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests."""
        return [
            request for request in self.requests_db.values()
            if request["status"] == "pending"
        ]

    def get_processing_requests(self) -> List[Dict[str, Any]]:
        """Get all requests currently being processed."""
        return [
            request for request in self.requests_db.values()
            if request["status"] == "processing"
        ]

    def get_completed_requests(self) -> List[Dict[str, Any]]:
        """Get all completed requests."""
        return [
            request for request in self.requests_db.values()
            if request["status"] == "completed"
        ]