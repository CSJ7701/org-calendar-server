
from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import requests
import os

from .config import config
from .auth import require_login, clear_session

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000") # Internal url to proxy backend requests to

# === Auth and Login/Logout ===

@app.get("/")
def root_redirect(request: Request):
    return RedirectResponse("/home")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, password: str=Form(...)):
    """
    POSTs the password to abckend /login (BasicAuth).
    Mirrors any Set-Cookie headers back to browser.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.post(
            f"{BACKEND_URL}/login",
            auth=("admin", password)
        )

    if resp.status_code == 200:
        response = RedirectResponse(url="/home", status_code=303)
        if "set-cookie" in resp.headers:
            response.headers["set-cookie"] = resp.headers["set-cookie"]
        return response

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid admin password."},
        status_code=401,
    )

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    return clear_session(response)

@app.get("/home", response_class=HTMLResponse)
def home(request: Request, _: bool = Depends(require_login)):
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "app_name": config.get("App", "name"), "username": config.get("User", "name"), "backend_calendar_url": "/proxy"+config.get("App", "default calendar")}
    )

@app.get("/events", response_class=HTMLResponse)
def events(request: Request, _: bool = Depends(require_login)):
    return templates.TemplateResponse(
        "calendar_events.html",
        {"request": request, "backend_calendar_url": "/proxy"+config.get("App", "default calendar"), "show_navbar": True, "calendar_name": "Admin"}
    )

@app.get("/tasks", response_class=HTMLResponse)
def tasks(request: Request, _: bool = Depends(require_login)):
    return templates.TemplateResponse(
        "calendar_tasks.html",
        {"request": request, "backend_calendar_url": "/proxy"+config.get("App", "default calendar"), "show_navbar": True, "calendar_name": "Admin"}
    )

@app.get("/views", response_class=HTMLResponse)
def views(request: Request, _: bool = Depends(require_login)):
    return templates.TemplateResponse(
        "views.html",
        {"request": request, "backend_views_url": "/proxy/admin/views"}
    )

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request, _: bool = Depends(require_login)):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "config": config._config}
    )

@app.post("/settings")
async def save_settings(request: Request, _: bool = Depends(require_login)):
    form = await request.form()
    config.update_from_form(form)
    return RedirectResponse(url="/settings", status_code=303)

def get_view_name(token: str):
        try:
            response = requests.get(f"{BACKEND_URL}/view/{token}")
            response.raise_for_status()

            data = response.json()
            name = data.get("name")
            print(name)

            if name is None:
                raise HTTPException(status_code=404, details="Name not found in response data")

            return name

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detial=f"Error connecting to backend: {str(e)}")

@app.get("/calendar/{token}")
def calendar_view(request: Request, token: str):
    name = get_view_name(token)
    return templates.TemplateResponse(
        "calendar_view.html",
        {"request": request, "token": token, "backend_calendar_url": f"/proxy/calendar/{token}.ics", "calendar_name": name}
    )

@app.get("/calendar/{token}/events")
def calendar_events(request: Request, token: str):
    name = get_view_name(token)    
    return templates.TemplateResponse(
        "calendar_events.html",
        {"request": request, "token": token, "backend_calendar_url": f"/proxy/calendar/{token}.ics", "calendar_name": name}
    )

@app.get("/calendar/{token}/tasks")
def calendar_tasks(request: Request, token: str):
    name = get_view_name(token)    
    return templates.TemplateResponse(
        "calendar_tasks.html",
        {"request": request, "token": token, "backend_calendar_url": f"/proxy/calendar/{token}.ics", "calendar_name": name}
    )

@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    """
    General-purpose proxy that forwards requests under /proxy/*
    to the backend container, preserving method, headers, and body.
    """
    # Construct the full backend url
    target_url = f"{BACKEND_URL}/{path}"

    # Forward original headers (minus host)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Add frontend cookies to backend request
    if "cookie" in request.headers:
        headers["cookie"] = request.headers["cookie"]

    # Forward request body, if any
    body = await request.body()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        backend_response = await client.request(
            request.method,
            target_url,
            headers=headers,
            content=body
        )

    response_headers = dict(backend_response.headers)
    if "set-cookie" in response_headers:
        response_headers["set-cookie"] = response_headers["set-cookie"]

    # Mirror the backend response
    return Response(
        content = backend_response.content,
        status_code = backend_response.status_code,
        headers = response_headers,
        media_type = backend_response.headers.get("content-type")
    )
