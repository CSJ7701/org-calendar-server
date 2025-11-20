from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature
import httpx
import os

# Reuse same SEsSION_COOKIE name for consistency
SESSION_COOKIE = "session"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
serializer = URLSafeTimedSerializer(SECRET_KEY)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

def is_logged_in(request: Request) -> bool:
    """Check if a session cookie exists."""
    return SESSION_COOKIE in request.cookies

def require_login_old(request: Request):
    """Dependency guard - redirect to /login if not authenticated."""
    if not is_logged_in(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )
    return True

async def require_login(request: Request):
    """Dependency guard - redirect to /login if not authenticated or session expired."""
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )

    # Verify session with backend
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BACKEND_URL}/verify-session",
            cookies = {SESSION_COOKIE: session_cookie},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )

    return True

def clear_session(response: RedirectResponse):
    """Helper to clear session cookie."""
    response.delete_cookie(SESSION_COOKIE)
    return response
