"""
Simple HTTP Basic Authentication Middleware
Protects all routes except /health
"""
import os
import secrets
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.base import BaseHTTPMiddleware

security = HTTPBasic()


def load_users_from_env() -> Dict[str, str]:
    """
    Load username:password pairs from environment variable.
    Format: BASIC_AUTH_USERS="user1:pass1,user2:pass2,user3:pass3"
    """
    users = {}
    auth_users_str = os.environ.get("BASIC_AUTH_USERS", "")

    if not auth_users_str:
        # Default credentials if none provided
        print("⚠️  No BASIC_AUTH_USERS set, using default admin:changeme")
        return {"admin": "changeme"}

    for user_pass in auth_users_str.split(","):
        if ":" in user_pass:
            username, password = user_pass.strip().split(":", 1)
            users[username] = password

    return users


VALID_USERS = load_users_from_env()


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against stored credentials."""
    if username not in VALID_USERS:
        return False

    stored_password = VALID_USERS[username]

    # Use constant-time comparison to prevent timing attacks
    username_match = secrets.compare_digest(username.encode(), username.encode())
    password_match = secrets.compare_digest(password.encode(), stored_password.encode())

    return username_match and password_match


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTP Basic Authentication on all routes
    except excluded paths like /health
    """

    EXCLUDED_PATHS = ["/health", "/api/env"]  # Paths that don't require auth

    async def dispatch(self, request: Request, call_next):
        # Skip auth for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Basic "):
            # Return 401 with WWW-Authenticate header to trigger browser login prompt
            return self._unauthorized_response()

        # Parse credentials
        try:
            import base64
            encoded_credentials = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded.split(":", 1)

            # Verify credentials
            if not verify_credentials(username, password):
                return self._unauthorized_response()

            # Add username to request state for logging
            request.state.authenticated_user = username

        except Exception as e:
            print(f"Auth error: {e}")
            return self._unauthorized_response()

        # Continue with the request
        response = await call_next(request)
        return response

    def _unauthorized_response(self):
        """Return 401 Unauthorized with WWW-Authenticate header."""
        from starlette.responses import Response
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AI-DIY Access"'}
        )
