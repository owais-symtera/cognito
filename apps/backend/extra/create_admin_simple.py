#!/usr/bin/env python
"""Simple script to create admin user via API."""

import requests
import json

BASE_URL = "http://localhost:8000"

# First, try to register an admin user
register_data = {
    "email": "admin@cognitoai.com",
    "password": "admin123",
    "full_name": "System Administrator"
}

print("Creating admin user...")

try:
    # Try to register
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)

    if response.status_code == 200:
        print("✅ Admin user created successfully!")
        print(f"Email: admin@cognitoai.com")
        print(f"Password: admin123")
    elif response.status_code == 400:
        print("Admin user might already exist.")
        # Try to login
        login_data = {
            "username": "admin@cognitoai.com",
            "password": "admin123"
        }
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
        if login_response.status_code == 200:
            print("✅ Admin login verified successfully!")
            print(f"Email: admin@cognitoai.com")
            print(f"Password: admin123")
        else:
            print("❌ Could not verify admin login")
    else:
        print(f"Error: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Backend server is not running at http://localhost:8000")
    print("Please ensure the backend is running first.")
except Exception as e:
    print(f"Error: {e}")

print("\n⚠️  IMPORTANT: Please change the password after first login!")