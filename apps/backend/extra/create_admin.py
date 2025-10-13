#!/usr/bin/env python
"""Script to create an admin user for CognitoAI Engine."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.models.user import User
from src.core.security import get_password_hash
from src.core.config import settings
from src.db.base import Base

# Database URL
DATABASE_URL = "sqlite:///./cognito_ai.db"

def create_admin_user():
    """Create an admin user in the database."""

    # Create engine
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    with Session(engine) as db:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@cognitoai.com").first()

        if existing_admin:
            print("Admin user already exists!")
            print(f"Email: admin@cognitoai.com")
            return

        # Create admin user
        admin_user = User(
            email="admin@cognitoai.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
            role="admin"
        )

        db.add(admin_user)
        db.commit()

        print("Admin user created successfully!")
        print(f"Email: admin@cognitoai.com")
        print(f"Password: admin123")
        print(f"Role: admin")
        print("\nPLEASE CHANGE THE PASSWORD AFTER FIRST LOGIN!")

if __name__ == "__main__":
    create_admin_user()