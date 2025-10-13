"""
Authentication dependencies for pharmaceutical API.

Provides FastAPI dependencies for API key validation,
JWT authentication, and user authorization.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import jwt
import structlog
from datetime import datetime, timedelta

from ..database.connection import get_db_session
from ..database.models import APIKey, User
from ..core.config import settings

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer()


async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract API key from request headers.
    
    Args:
        x_api_key: API key from X-API-Key header
        authorization: API key from Authorization header
    
    Returns:
        API key if found
    
    Since:
        Version 1.0.0
    """
    # Check X-API-Key header first
    if x_api_key:
        return x_api_key
    
    # Check Authorization header
    if authorization:
        # Handle "Bearer <key>" format
        if authorization.startswith("Bearer "):
            return authorization[7:]
        # Handle "ApiKey <key>" format
        if authorization.startswith("ApiKey "):
            return authorization[7:]
        return authorization
    
    return None


async def require_api_key(
    api_key: Optional[str] = Depends(get_api_key),
    db: AsyncSession = Depends(get_db_session)
) -> str:
    """
    Validate API key and return it.
    
    Args:
        api_key: API key from headers
        db: Database session
    
    Returns:
        Validated API key
    
    Raises:
        HTTPException: If API key is invalid or missing
    
    Since:
        Version 1.0.0
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Validate API key format (basic check)
    if len(api_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    # Check API key in database
    from sqlalchemy import select
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    try:
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        )
        result = await db.execute(stmt)
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            logger.warning(
                "Invalid API key attempted",
                key_prefix=api_key[:8] + "..."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            logger.warning(
                "Expired API key used",
                key_id=api_key_record.id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired"
            )
        
        # Update last used timestamp
        api_key_record.last_used_at = datetime.utcnow()
        api_key_record.request_count = (api_key_record.request_count or 0) + 1
        await db.commit()
        
        logger.info(
            "API key validated",
            key_id=api_key_record.id,
            user_id=api_key_record.user_id
        )
        
        return api_key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "API key validation error",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token credentials
        db: Database session
    
    Returns:
        User information dictionary
    
    Raises:
        HTTPException: If token is invalid
    
    Since:
        Version 1.0.0
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        from sqlalchemy import select
        stmt = select(User).where(
            User.id == user_id,
            User.is_active == True
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "roles": user.roles or [],
            "permissions": user.permissions or []
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User authentication error",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


def require_permission(permission: str):
    """
    Dependency to require specific permission.
    
    Args:
        permission: Required permission name
    
    Returns:
        Dependency function
    
    Since:
        Version 1.0.0
    """
    async def permission_checker(
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        Check if user has required permission.
        
        Args:
            user: Current authenticated user
        
        Returns:
            User if permission granted
        
        Raises:
            HTTPException: If permission denied
        """
        if permission not in user.get("permissions", []):
            # Check if user has admin role (bypass)
            if "admin" not in user.get("roles", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
        
        return user
    
    return permission_checker


def require_role(role: str):
    """
    Dependency to require specific role.
    
    Args:
        role: Required role name
    
    Returns:
        Dependency function
    
    Since:
        Version 1.0.0
    """
    async def role_checker(
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        Check if user has required role.
        
        Args:
            user: Current authenticated user
        
        Returns:
            User if role granted
        
        Raises:
            HTTPException: If role not found
        """
        if role not in user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        
        return user
    
    return role_checker