"""
Access control and authorization for pharmaceutical data.

Implements role-based access control (RBAC) with fine-grained
permissions for pharmaceutical data compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime, timedelta
import structlog
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class DataAccessLevel(Enum):
    """
    Data access levels for pharmaceutical information.

    Since:
        Version 1.0.0
    """
    NONE = 0
    MASKED = 1  # PII/PHI masked
    RESTRICTED = 2  # Limited fields visible
    STANDARD = 3  # Standard access
    FULL = 4  # Complete access
    ADMIN = 5  # Administrative access


class UserRole(Enum):
    """
    User roles in pharmaceutical system.

    Since:
        Version 1.0.0
    """
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    CLINICIAN = "clinician"
    COMPLIANCE = "compliance"
    ADMIN = "admin"
    SYSTEM = "system"


class AccessControlService:
    """
    Service for managing data access control.

    Implements RBAC with audit logging and compliance tracking
    for pharmaceutical data protection.

    Since:
        Version 1.0.0
    """

    # Role to access level mapping
    ROLE_ACCESS_LEVELS = {
        UserRole.VIEWER: DataAccessLevel.MASKED,
        UserRole.RESEARCHER: DataAccessLevel.RESTRICTED,
        UserRole.ANALYST: DataAccessLevel.STANDARD,
        UserRole.CLINICIAN: DataAccessLevel.STANDARD,
        UserRole.COMPLIANCE: DataAccessLevel.FULL,
        UserRole.ADMIN: DataAccessLevel.ADMIN,
        UserRole.SYSTEM: DataAccessLevel.ADMIN
    }

    # Field access restrictions by level
    FIELD_RESTRICTIONS = {
        DataAccessLevel.MASKED: {
            'allowed': ['id', 'category', 'created_at', 'provider'],
            'masked': ['pharmaceutical_compound', 'query', 'raw_response']
        },
        DataAccessLevel.RESTRICTED: {
            'allowed': ['id', 'category', 'pharmaceutical_compound',
                       'created_at', 'provider', 'relevance_score'],
            'masked': ['raw_response', 'query_parameters']
        },
        DataAccessLevel.STANDARD: {
            'allowed': '*',  # All fields except specified masked
            'masked': ['cost', 'token_count']
        },
        DataAccessLevel.FULL: {
            'allowed': '*',
            'masked': []
        },
        DataAccessLevel.ADMIN: {
            'allowed': '*',
            'masked': []
        }
    }

    def __init__(
        self,
        db: AsyncSession,
        audit_logger: Optional[Any] = None
    ):
        """
        Initialize access control service.

        Args:
            db: Database session
            audit_logger: Audit logging service

        Since:
            Version 1.0.0
        """
        self.db = db
        self.audit_logger = audit_logger
        self._permission_cache = {}

    async def check_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has access to resource.

        Args:
            user_id: User identifier
            resource: Resource type (e.g., 'api_responses')
            action: Action (read, write, delete)
            resource_id: Specific resource ID

        Returns:
            True if access allowed

        Since:
            Version 1.0.0
        """
        try:
            # Get user role
            user_role = await self._get_user_role(user_id)

            # Check permission
            has_access = await self._check_permission(
                user_role,
                resource,
                action,
                resource_id
            )

            # Log access attempt
            if self.audit_logger:
                await self.audit_logger.log_data_access(
                    resource=resource,
                    action=action,
                    user_id=user_id,
                    success=has_access,
                    resource_id=resource_id
                )

            return has_access

        except Exception as e:
            logger.error(
                "Access check failed",
                user_id=user_id,
                resource=resource,
                error=str(e)
            )
            return False

    async def _get_user_role(self, user_id: str) -> UserRole:
        """
        Get user's role from database.

        Args:
            user_id: User identifier

        Returns:
            User role

        Since:
            Version 1.0.0
        """
        # Check cache first
        cache_key = f"user_role_{user_id}"
        if cache_key in self._permission_cache:
            cached = self._permission_cache[cache_key]
            if cached['expires'] > datetime.utcnow():
                return cached['role']

        # TODO: Query actual user table
        # For now, return default role
        role = UserRole.RESEARCHER

        # Cache result
        self._permission_cache[cache_key] = {
            'role': role,
            'expires': datetime.utcnow() + timedelta(minutes=15)
        }

        return role

    async def _check_permission(
        self,
        role: UserRole,
        resource: str,
        action: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check specific permission for role.

        Args:
            role: User role
            resource: Resource type
            action: Action type
            resource_id: Specific resource

        Returns:
            True if permitted

        Since:
            Version 1.0.0
        """
        # Get access level for role
        access_level = self.ROLE_ACCESS_LEVELS.get(role)

        if not access_level:
            return False

        # Admin has all permissions
        if access_level == DataAccessLevel.ADMIN:
            return True

        # Check resource-specific permissions
        permissions = self._get_resource_permissions(resource)

        # Check action permission for role
        required_level = permissions.get(action, DataAccessLevel.ADMIN)

        return access_level.value >= required_level.value

    def _get_resource_permissions(self, resource: str) -> Dict[str, DataAccessLevel]:
        """
        Get permission requirements for resource.

        Args:
            resource: Resource type

        Returns:
            Permission requirements

        Since:
            Version 1.0.0
        """
        permissions = {
            'api_responses': {
                'read': DataAccessLevel.MASKED,
                'write': DataAccessLevel.STANDARD,
                'delete': DataAccessLevel.ADMIN,
                'archive': DataAccessLevel.COMPLIANCE
            },
            'drug_requests': {
                'read': DataAccessLevel.RESTRICTED,
                'write': DataAccessLevel.STANDARD,
                'delete': DataAccessLevel.ADMIN,
                'approve': DataAccessLevel.CLINICIAN
            },
            'audit_logs': {
                'read': DataAccessLevel.COMPLIANCE,
                'write': DataAccessLevel.SYSTEM,
                'delete': DataAccessLevel.NONE  # Never delete
            }
        }

        return permissions.get(resource, {})

    async def filter_data(
        self,
        data: Dict[str, Any],
        user_id: str,
        resource: str
    ) -> Dict[str, Any]:
        """
        Filter data based on user's access level.

        Args:
            data: Data to filter
            user_id: User identifier
            resource: Resource type

        Returns:
            Filtered data

        Since:
            Version 1.0.0
        """
        # Get user's access level
        user_role = await self._get_user_role(user_id)
        access_level = self.ROLE_ACCESS_LEVELS.get(user_role)

        if access_level == DataAccessLevel.ADMIN:
            return data  # No filtering for admin

        # Get field restrictions
        restrictions = self.FIELD_RESTRICTIONS.get(access_level, {})
        allowed_fields = restrictions.get('allowed', [])
        masked_fields = restrictions.get('masked', [])

        filtered = {}

        # Apply field filtering
        for field, value in data.items():
            if allowed_fields == '*' or field in allowed_fields:
                if field in masked_fields:
                    filtered[field] = '***MASKED***'
                else:
                    filtered[field] = value

        return filtered

    async def get_accessible_resources(
        self,
        user_id: str,
        resource_type: str
    ) -> List[str]:
        """
        Get list of resources user can access.

        Args:
            user_id: User identifier
            resource_type: Type of resource

        Returns:
            List of accessible resource IDs

        Since:
            Version 1.0.0
        """
        user_role = await self._get_user_role(user_id)
        access_level = self.ROLE_ACCESS_LEVELS.get(user_role)

        if access_level == DataAccessLevel.ADMIN:
            # Admin can access everything
            return ['*']

        # TODO: Query user's specific resource permissions
        # For now, return empty list
        return []

    async def grant_temporary_access(
        self,
        user_id: str,
        resource_id: str,
        duration_hours: int = 24,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Grant temporary elevated access.

        Args:
            user_id: User identifier
            resource_id: Resource to grant access to
            duration_hours: Duration of access
            reason: Reason for access

        Returns:
            Access grant details

        Since:
            Version 1.0.0
        """
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

        grant_id = f"temp_{user_id}_{resource_id}_{datetime.utcnow().timestamp()}"

        # Store temporary grant (would go in database)
        grant = {
            'grant_id': grant_id,
            'user_id': user_id,
            'resource_id': resource_id,
            'expires_at': expires_at.isoformat(),
            'reason': reason,
            'granted_at': datetime.utcnow().isoformat()
        }

        # Log grant
        if self.audit_logger:
            await self.audit_logger.log_data_access(
                resource='access_grants',
                action='create',
                user_id='system',
                success=True,
                details=grant
            )

        logger.info(
            "Temporary access granted",
            user_id=user_id,
            resource_id=resource_id,
            duration_hours=duration_hours
        )

        return grant


def require_access(resource: str, action: str):
    """
    Decorator for access control on API endpoints.

    Args:
        resource: Resource type
        action: Action type

    Since:
        Version 1.0.0
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from request context
            request = kwargs.get('request')
            if not request:
                raise ValueError("No request context")

            user_id = getattr(request, 'user_id', None)
            if not user_id:
                raise ValueError("No user ID in request")

            # Get access control service
            access_control = getattr(request.app, 'access_control', None)
            if not access_control:
                raise ValueError("Access control not configured")

            # Check access
            resource_id = kwargs.get('resource_id')
            has_access = await access_control.check_access(
                user_id,
                resource,
                action,
                resource_id
            )

            if not has_access:
                raise PermissionError(f"Access denied to {resource}:{action}")

            return await func(*args, **kwargs)

        return wrapper
    return decorator