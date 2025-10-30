from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeSerializer
import os

SECRET_KEY = os.getenv("FRONTEND_SECRET", "change-me")
serializer = URLSafeSerializer(SECRET_KEY)
SESSION_COOKIE = "session"

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
BACKEND_VERIFY_URL = BACKEND_URL + "/admin/verify"

# === Session Management ===

def create_session() -> str:
    """Generate signed session token for admin login."""
    return serializer.dumps({"role": "admin"})

def get_session(request: Request):
    """Return decoded session data if valid, else None."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    try:
        return serializer.loads(cookie)
    except Exception:
        return None

def is_logged_in(request: Request) -> bool:
    """Check whether current request has a valid admin session."""
    data = get_session(request)
    return data is not None and data.get("role") == "admin"

def require_login(request: Request):
    """Dependency guard - redirect to login if not authentiated"""
    if not is_logged_in(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )
    return True

def clear_session(response: RedirectResponse):
    """Helper to clear session cookie."""
    response.delete_cookie(SESSION_COOKIE)
    return response

# === Login / Logout helpers ===

import httpx

async def verify_password_with_backend(password: str) -> bool:
    """Send password to backend for verification via BasicAuth."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                BACKEND_VERIFY_URL,
                auth=("admin", password), # Username is irrelevant
                timeout=5.0,
            )
            return resp.status_code == 200
    except httpx.RequestError:
        return False

def set_login_cookie(response: RedirectResponse):
    """Helper to set session cookie after successful login."""
    token = create_session()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response

