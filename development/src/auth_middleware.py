"""
Enhanced HTTP Basic Authentication Middleware with Cloudflare Access Support
Protects all routes except /health
Bypasses Basic Auth for authenticated Cloudflare Access users
"""
import os
import secrets
import json
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


def is_cloudflare_access_authenticated(request: Request) -> bool:
    """
    Check if request is authenticated via Cloudflare Access.
    
    Cloudflare Access adds these headers when authentication is successful:
    - Cf-Access-Jwt-Assertion: JWT token (optional validation)
    - Cf-Access-Authenticated-User-Email: User email
    - Cf-Access-Authenticated-User: User name/ID
    
    For simplicity, we trust Cloudflare's validation and check for presence of headers.
    """
    # Check for Cloudflare Access headers
    jwt_assertion = request.headers.get("Cf-Access-Jwt-Assertion")
    authenticated_email = request.headers.get("Cf-Access-Authenticated-User-Email")
    authenticated_user = request.headers.get("Cf-Access-Authenticated-User")
    
    # If any Cloudflare Access headers are present, consider it authenticated
    # Cloudflare handles the actual JWT validation before adding headers
    if jwt_assertion or authenticated_email or authenticated_user:
        print(f"🔓 Cloudflare Access authenticated: {authenticated_email or authenticated_user}")
        return True
    
    return False


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware that enforces HTTP Basic Authentication OR allows Cloudflare Access.
    Cloudflare Access users bypass Basic Auth completely.
    Direct Railway access falls back to Basic Auth.
    """

    EXCLUDED_PATHS = ["/health", "/api/env"]  # Paths that don't require auth

    # Paths that internal/localhost requests can access without auth
    # This allows Sprint Review Alex to read/write sandbox files
    INTERNAL_ALLOWED_PATHS = ["/api/sandbox/"]

    async def dispatch(self, request: Request, call_next):
        # Skip auth for excluded paths and wireframe endpoints
        if request.url.path in self.EXCLUDED_PATHS or request.url.path.startswith("/api/backlog/wireframe/"):
            return await call_next(request)

        # Allow internal/localhost requests to access sandbox API without auth
        # This is needed for Sprint Review Alex to read/write files
        client_host = request.client.host if request.client else None
        is_internal = client_host in ("127.0.0.1", "localhost", "::1")
        is_sandbox_path = any(request.url.path.startswith(p) for p in self.INTERNAL_ALLOWED_PATHS)

        if is_internal and is_sandbox_path:
            return await call_next(request)

        # FIRST: Check for Cloudflare Access authentication
        if is_cloudflare_access_authenticated(request):
            # Add Cloudflare user info to request state for logging
            authenticated_email = request.headers.get("Cf-Access-Authenticated-User-Email")
            authenticated_user = request.headers.get("Cf-Access-Authenticated-User")
            request.state.authenticated_user = f"Cloudflare: {authenticated_email or authenticated_user}"
            request.state.auth_method = "cloudflare_access"
            
            # Continue with the request (no Basic Auth required)
            response = await call_next(request)
            return response

        # SECOND: Fall back to HTTP Basic Authentication
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

            # Add username and auth method to request state for logging
            request.state.authenticated_user = username
            request.state.auth_method = "basic_auth"

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
