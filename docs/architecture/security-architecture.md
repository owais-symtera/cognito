# Security Architecture

### Authentication and Authorization
```python
# apps/backend/src/core/security.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt

security = HTTPBearer()

class SecurityManager:
    """
    Handles authentication and authorization for pharmaceutical data access
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_minutes = 1440  # 24 hours

    def create_access_token(self, user_id: str, permissions: List[str]) -> str:
        """Create JWT token with pharmaceutical data access permissions"""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)

        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "cognito-ai-engine"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user information"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check expiration
            if datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )

            return payload

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and verify current user from JWT token"""
    security_manager = SecurityManager(settings.JWT_SECRET_KEY)
    user_data = security_manager.verify_token(credentials.credentials)
    return user_data

# Permission-based access control
class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: dict = Depends(get_current_user)):
        if self.required_permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {self.required_permission}"
            )
        return current_user

# Usage in routes
@router.get("/api/v1/requests/{request_id}")
async def get_request(
    request_id: str,
    current_user: dict = Depends(PermissionChecker("read_drug_requests"))
):
    # Implementation here
    pass
```

### API Rate Limiting and Security
```python
# apps/backend/src/middleware/security.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/2"
)

class SecurityMiddleware:
    """
    Security middleware for pharmaceutical data protection
    """

    @staticmethod
    @limiter.limit("100/minute")  # API rate limiting
    async def rate_limit_requests(request: Request):
        """Rate limit API requests to prevent abuse"""
        pass

    @staticmethod
    async def audit_api_access(request: Request, call_next):
        """Audit all API access for regulatory compliance"""
        start_time = time.time()

        # Log request details
        audit_data = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": get_remote_address(request),
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow().isoformat()
        }

        response = await call_next(request)

        # Log response details
        audit_data.update({
            "status_code": response.status_code,
            "processing_time": time.time() - start_time
        })

        # Store in audit log
        await store_audit_log(audit_data)

        return response
```
