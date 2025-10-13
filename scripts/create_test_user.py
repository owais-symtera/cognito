"""Create a test user for CognitoAI Engine."""

import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid
import bcrypt

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def hash_password(password):
    """Hash password using bcrypt."""
    # Use bcrypt for proper password hashing
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_test_user():
    """Create a test user in the database."""

    # Database connection
    conn = psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        database=os.getenv('DATABASE_NAME', 'cognitoai'),
        user=os.getenv('DATABASE_USER', 'postgres'),
        password=os.getenv('DATABASE_PASSWORD', 'postgres'),
        port=os.getenv('DATABASE_PORT', '5432')
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if users table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'users'
            )
        """)
        table_exists = cur.fetchone()['exists']

        if not table_exists:
            # Create users table
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    role VARCHAR(50) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            print("Created users table")

        # Check if test user exists
        test_email = 'admin@cognitoai.com'
        test_username = 'admin'
        cur.execute("SELECT * FROM users WHERE email = %s OR username = %s", (test_email, test_username))
        existing_user = cur.fetchone()

        if existing_user:
            print(f"User {test_email} already exists")
            print(f"  ID: {existing_user['id']}")
            print(f"  Username: {existing_user['username']}")
            print(f"  Email: {existing_user['email']}")
        else:
            # Create test user
            user_id = str(uuid.uuid4())
            hashed_password = hash_password('admin123')
            cur.execute("""
                INSERT INTO users (id, username, email, full_name, hashed_password, role, is_active, failed_login_attempts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, test_username, test_email, 'Admin User', hashed_password, 'admin', True, 0))

            user_id = cur.fetchone()['id']
            conn.commit()
            print(f"Created test user:")
            print(f"  Email: {test_email}")
            print(f"  Username: {test_username}")
            print(f"  Password: admin123")
            print(f"  User ID: {user_id}")

        # List all users
        cur.execute("SELECT id, username, email, full_name, role, is_active FROM users")
        users = cur.fetchall()
        print("\nAll users in database:")
        for user in users:
            print(f"  - {user['username']} ({user['email']}) - {user['full_name']} - Role: {user['role']} - Active: {user['is_active']}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_test_user()