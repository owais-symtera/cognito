"""Authentication service for user management using database."""

import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class AuthService:
    """Service for handling authentication and user management with database."""

    def __init__(self):
        """Initialize auth service with database connection."""
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'database': os.getenv('DATABASE_NAME', 'cognitoai'),
            'user': os.getenv('DATABASE_USER', 'postgres'),
            'password': os.getenv('DATABASE_PASSWORD', 'postgres'),
            'port': os.getenv('DATABASE_PORT', '5432')
        }
        # In-memory sessions (can be moved to Redis in production)
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(**self.db_config)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password from database."""
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if user exists
            cur.execute("""
                SELECT id, username, email, full_name, hashed_password, role, is_active
                FROM users
                WHERE email = %s OR username = %s
            """, (email, email))  # Allow login with email or username

            user = cur.fetchone()

            if not user:
                return None

            # Check password using bcrypt
            if not bcrypt.checkpw(password.encode('utf-8'), user['hashed_password'].encode('utf-8')):
                return None

            if not user.get('is_active', True):
                return None

            # Update last login time
            cur.execute("""
                UPDATE users
                SET last_login_at = %s
                WHERE id = %s
            """, (datetime.now(), user['id']))
            conn.commit()

            # Return user data without password hash
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"]
            }

        except Exception as e:
            print(f"Authentication error: {e}")
            return None
        finally:
            cur.close()
            conn.close()

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
        username: str,
        full_name: str,
        role: str = "user"
    ) -> bool:
        """Register a new user in database."""
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if user already exists
            cur.execute("""
                SELECT id FROM users
                WHERE email = %s OR username = %s
            """, (email, username))

            if cur.fetchone():
                return False

            # Hash password with bcrypt
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

            # Create new user
            user_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO users (id, username, email, full_name, hashed_password, role, is_active, failed_login_attempts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, email, full_name, hashed_password, role, True, 0))

            conn.commit()
            return True

        except Exception as e:
            print(f"Registration error: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from database."""
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute("""
                SELECT id, username, email, full_name, role, is_active, created_at
                FROM users
                WHERE email = %s
            """, (email,))

            user = cur.fetchone()
            if user:
                # Return user without password hash
                return {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "is_active": user["is_active"],
                    "created_at": user["created_at"].isoformat() if user["created_at"] else None
                }
            return None

        except Exception as e:
            print(f"Get user error: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def update_user(self, email: str, **kwargs) -> bool:
        """Update user information in database."""
        conn = self.get_db_connection()
        cur = conn.cursor()

        try:
            # Build update query dynamically
            update_fields = []
            values = []

            for field, value in kwargs.items():
                if field in ['full_name', 'role', 'is_active']:
                    update_fields.append(f"{field} = %s")
                    values.append(value)

            if not update_fields:
                return False

            values.append(email)
            query = f"""
                UPDATE users
                SET {', '.join(update_fields)}, updated_at = %s
                WHERE email = %s
            """
            values.insert(len(values) - 1, datetime.now())

            cur.execute(query, values)
            conn.commit()
            return cur.rowcount > 0

        except Exception as e:
            print(f"Update user error: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    def change_password(self, email: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        # First authenticate with old password
        user = self.authenticate_user(email, old_password)
        if not user:
            return False

        conn = self.get_db_connection()
        cur = conn.cursor()

        try:
            # Hash new password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

            # Update password
            cur.execute("""
                UPDATE users
                SET hashed_password = %s, updated_at = %s
                WHERE email = %s
            """, (hashed_password, datetime.now(), email))

            conn.commit()
            return cur.rowcount > 0

        except Exception as e:
            print(f"Change password error: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()