from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature
import secrets, os, logging

logger = logging.getLogger(__name__)

# --- Config ---
security = HTTPBasic()
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
SESSION_COOKIE = "session"

# --- Serializer ---
serializer = URLSafeTimedSerializer(SECRET_KEY)

# --- Session Management ---

def create_session() -> str:
    """Generate signed session token for admin login."""
    return serializer.dumps({"role": "admin"})

def verify_session(request: Request):
    """Validate session cookie, raise 401 if invalid."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No cookie")
    try:
        data = serializer.loads(cookie, max_age=3600 * 12) # 12 hour session
        if data.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad role")
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad signature")
    return True

# --- Auth Helpers ---

def verify_admin_login(response: Response, creds: HTTPBasicCredentials = Depends(security)):
    """Authenticate admin via BasicAuth and set session cookie."""
    if not secrets.compare_digest(creds.password, ADMIN_PASS):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = create_session()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="Lax",
    )
    return {"message": "Login Successful"}

def require_admin(request: Request):
    """Dependency guard for protected routes."""
    return verify_session(request)
    
# --- Deprecated ---

def verify_admin_old(creds: HTTPBasicCredentials = Depends(security)):
    if not secrets.compare_digest(creds.password, ADMIN_PASS):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True
