#!/usr/bin/env python
"""Fix backend authentication response to match frontend expectations."""

from pathlib import Path

def fix_signin_endpoint():
    """Fix the signin endpoint to return proper response format."""

    main_py = Path(__file__).parent.parent / "apps/backend/src/main.py"

    if not main_py.exists():
        print("Error: main.py not found")
        return False

    content = main_py.read_text()

    # Find and replace the signin endpoint
    old_code = '''@app.post("/api/v1/auth/signin")
async def signin(credentials: LoginRequest):
    """User sign in."""
    user = auth_service.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_session(user)
    return {
        "user": user,
        "accessToken": token,
        "tokenType": "bearer"
    }'''

    new_code = '''@app.post("/api/v1/auth/signin")
async def signin(credentials: LoginRequest):
    """User sign in."""
    user = auth_service.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Ensure user has required fields for frontend compatibility
    if "id" not in user:
        user["id"] = user.get("email", "")
    if "name" not in user:
        user["name"] = user.get("full_name", user.get("email", ""))

    token = auth_service.create_session(user)
    return {
        "user": user,
        "access_token": token,  # Frontend expects access_token not accessToken
        "refresh_token": None,  # Add refresh_token field
        "tokenType": "bearer"
    }'''

    if old_code in content:
        content = content.replace(old_code, new_code)
        main_py.write_text(content)
        print("✓ Fixed signin endpoint in main.py")
        return True
    else:
        print("Warning: Could not find exact match for signin endpoint, attempting alternative fix...")

        # Try a more flexible approach
        import re
        pattern = r'(@app\.post\("/api/v1/auth/signin"\)[\s\S]*?return\s*{[\s\S]*?"tokenType":\s*"bearer"\s*})'

        match = re.search(pattern, content)
        if match:
            old_part = match.group(1)
            # Check if already fixed
            if '"access_token"' in old_part:
                print("Already fixed!")
                return True

            # Apply fix
            new_part = new_code
            content = content.replace(old_part, new_part)
            main_py.write_text(content)
            print("✓ Fixed signin endpoint with pattern match")
            return True

        print("Error: Could not fix signin endpoint")
        return False

if __name__ == "__main__":
    if fix_signin_endpoint():
        print("\nBackend authentication fixed!")
        print("\nNow restart the backend server for changes to take effect.")
        print("\nLogin credentials:")
        print("  Email: admin@cognitoai.com")
        print("  Password: admin123")
    else:
        print("\nFailed to fix backend authentication. Manual intervention may be required.")