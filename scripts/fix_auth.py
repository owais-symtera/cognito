#!/usr/bin/env python
"""Fix authentication configuration for CognitoAI Engine."""

import os
import sys
import json
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent

    # 1. Fix frontend auth.ts to use correct API endpoint
    auth_file = project_root / "apps/frontend/src/lib/auth.ts"
    if auth_file.exists():
        content = auth_file.read_text()
        # Fix the API endpoint path
        content = content.replace(
            '`${apiUrl}/api/auth/signin`',
            '`${apiUrl}/api/v1/auth/signin`'
        )
        auth_file.write_text(content)
        print("✅ Updated frontend auth.ts to use /api/v1/auth/signin")

    # 2. Fix frontend .env.local
    env_local = project_root / "apps/frontend/.env.local"
    if env_local.exists():
        lines = env_local.read_text().splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith("NEXTAUTH_URL="):
                updated_lines.append("NEXTAUTH_URL=http://localhost:3003")
            elif line.startswith("NEXT_PUBLIC_API_URL="):
                updated_lines.append("NEXT_PUBLIC_API_URL=http://localhost:8000")
            else:
                updated_lines.append(line)
        env_local.write_text('\n'.join(updated_lines))
        print("✅ Updated .env.local with correct ports")

    # 3. Update backend main.py to ensure user has ID in response
    main_py = project_root / "apps/backend/src/main.py"
    if main_py.exists():
        content = main_py.read_text()
        # Check if we need to update the signin response
        if '"user": user,' in content and '"id":' not in content:
            # Add ID to user response if missing
            content = content.replace(
                '    return {\n        "user": user,',
                '    # Ensure user has an ID field\n    if "id" not in user:\n        user["id"] = user.get("email", "")\n    return {\n        "user": user,'
            )
            main_py.write_text(content)
            print("✅ Updated backend to include user ID in response")

    print("\n🎉 Authentication configuration fixed!")
    print("\nCredentials for testing:")
    print("  Email/Username: admin@cognitoai.com or admin")
    print("  Password: admin123")
    print("\nFrontend URL: http://localhost:3003")
    print("Backend URL: http://localhost:8000")

if __name__ == "__main__":
    main()