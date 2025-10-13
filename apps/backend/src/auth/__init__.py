"""
Authentication module for CognitoAI Engine.

Provides authentication and authorization functionality
for the pharmaceutical intelligence platform.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from .dependencies import (
    get_api_key,
    require_api_key,
    get_current_user,
    require_permission,
    require_role
)

__all__ = [
    "get_api_key",
    "require_api_key",
    "get_current_user",
    "require_permission",
    "require_role"
]