"""Simple token-based authentication for the dashboard."""

import secrets
from typing import Optional

from fastapi import Cookie, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from config import get_settings

# Session cookie name
SESSION_COOKIE = "sdcp_session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


def get_serializer() -> URLSafeTimedSerializer:
    """Get the serializer for session tokens."""
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def create_session_token(user_id: str = "admin") -> str:
    """Create a new session token."""
    serializer = get_serializer()
    return serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> Optional[dict]:
    """Verify a session token and return the payload."""
    serializer = get_serializer()
    try:
        return serializer.loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None


def set_session_cookie(response: Response, user_id: str = "admin"):
    """Set the session cookie on a response."""
    token = create_session_token(user_id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )


def clear_session_cookie(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE)


def get_current_user(request: Request) -> Optional[dict]:
    """Get the current user from the session cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return verify_session_token(token)


def require_auth(request: Request) -> dict:
    """Dependency that requires authentication.

    For now, just checks if a valid session exists.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=303,
            headers={"Location": "/login"},
        )
    return user


# Simple password check (configure via environment)
def verify_password(password: str) -> bool:
    """Verify the dashboard password."""
    settings = get_settings()
    # Use dashboard_password if set, otherwise fall back to secret_key
    expected = settings.dashboard_password if settings.dashboard_password else settings.secret_key
    return secrets.compare_digest(password, expected)
