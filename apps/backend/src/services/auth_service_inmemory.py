"""Authentication service for user management."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any


class AuthService:
    """Service for handling authentication and user management."""

    def __init__(self):
        """Initialize auth service."""
        # In-memory user storage (replace with database in production)
        self.users_db: Dict[str, Dict[str, Any]] = {
            "admin@cognitoai.com": {
                "email": "admin@cognitoai.com",
                "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
                "full_name": "Admin User",
                "role": "admin",
                "is_active": True
            }
        }
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password."""
        user = self.users_db.get(email)
        if not user:
            return None

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            return None

        if not user.get("is_active", True):
            return None

        return {
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }

    def create_session(self, user: Dict[str, Any]) -> str:
        """Create a new session for authenticated user."""
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "user": user,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user data."""
        session = self.sessions.get(token)
        if not session:
            return None

        if datetime.now() > session["expires_at"]:
            del self.sessions[token]
            return None

        return session["user"]

    def logout(self, token: str) -> bool:
        """Logout user by removing session."""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str = "user"
    ) -> bool:
        """Register a new user."""
        if email in self.users_db:
            return False

        self.users_db[email] = {
            "email": email,
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        return True

    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        user = self.users_db.get(email)
        if user:
            # Return user without password hash
            return {
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at")
            }
        return None

    def update_user(self, email: str, updates: Dict[str, Any]) -> bool:
        """Update user information."""
        if email not in self.users_db:
            return False

        user = self.users_db[email]

        if "full_name" in updates:
            user["full_name"] = updates["full_name"]

        if "role" in updates:
            user["role"] = updates["role"]

        if "is_active" in updates:
            user["is_active"] = updates["is_active"]

        if "password" in updates:
            user["password_hash"] = hashlib.sha256(updates["password"].encode()).hexdigest()

        user["updated_at"] = datetime.now().isoformat()
        return True

    def delete_user(self, email: str) -> bool:
        """Delete a user."""
        if email in self.users_db:
            del self.users_db[email]
            # Also remove any sessions for this user
            tokens_to_remove = [
                token for token, session in self.sessions.items()
                if session["user"]["email"] == email
            ]
            for token in tokens_to_remove:
                del self.sessions[token]
            return True
        return False