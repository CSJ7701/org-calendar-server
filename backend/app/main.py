from fastapi import FastAPI, APIRouter, Depends, Query, Request
from fastapi_utils.tasks import repeat_every
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import logging
from icalendar import Calendar, Todo, Event
from datetime import datetime, timezone
import uuid
import os
from zoneinfo import ZoneInfo

from .db import Base, engine, SessionLocal
from .sync import sync_repo
from .sync_worker import run_sync_cycle, SYNC_INTERVAL, SYNC_RETRY
from .parser import get_org_files, parse_org_file, import_tasks, refresh_db
from .models import Task, serialize_task, serialize_event
from .views import views_file, parse_views_file, get_tasks_for_view
from .auth import verify_admin_login, require_admin, verify_session

TIMEZONE = os.getenv("TIMEZONE", "UTC")

app = FastAPI(title="Org Parser API")
router = APIRouter()

# Configure logging
formatter = logging.Formatter('[{levelname}] {name:<15s} - {message}', style='{')
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)

logger = logging.getLogger("org-cal")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

uv_log = logging.getLogger("uvicorn")
uv_log.handlers.clear()
uv_log.addHandler(handler)

# Security - mainly rate limiting
limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
security_logger = logging.getLogger("org-cal.security")
security_logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Or frontend url
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    security_logger.info(f"{request.client.host} {request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    security_logger.exception(f"Unhandled error during {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Main routing definitions

@app.on_event("startup")
async def startup_event():
    await run_sync_cycle()
    logger.info("Initial sync complete")
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

    import_org_files(refresh = True) # Wipe database and re-read on every restart
    logger.info("Database populated")

    global VIEWS
    VIEWS = parse_views_file(views_file)
    logger.info("Views parsed: " + str(len(VIEWS)))

@app.on_event("startup")
@repeat_every(seconds=SYNC_INTERVAL, wait_first=False, raise_exceptions=True)
async def periodic_task() -> None:
    logger.info("Running sync cycle")
    await run_sync_cycle()
    VIEWS = parse_views_file(views_file)
    logger.info("Views updated")
    import_org_files()
    logger.info("Database updated")
    
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/login")
def login(response: Response, result = Depends(verify_admin_login)):
    return result

@app.get("/verify-session")
def verify_session_endpoint(request: Request):
    """
    Used by frontend to check if current session is still valid.
    Return 200 if valid, 401 if not
    """
    try:
        verify_session(request)
        return JSONResponse({"ok": True}, status_code=200)
    except Exception as e:
        print(e)
        return JSONResponse({"ok": False}, status_code=401)

@app.post("/admin/sync")
@limiter.limit("2/minute")
def trigger_sync(request: Request, _ = Depends(require_admin)):
    result = sync_repo()
    return JSONResponse(content={"status": "sync_started", "result": result})

@app.post("/admin/import")
@limiter.limit("2/minute")
def import_org_files_route(request: Request, refresh: bool=Query(True, description="Wipe DB before import"), _ = Depends(require_admin)):
    """Route wrapper that rate-limits and calls the real import function."""
    return import_org_files(refresh)

def import_org_files(refresh: bool = Query(True, description="Wipe DB before import")):
    """Import tasks from all org files into database"""
    files = get_org_files()
    all_tasks = []
    if refresh:
        refresh_db()
    for f in files:
        parsed = parse_org_file(f)
        import_tasks(parsed)
        all_tasks.extend(parsed)
    return {
        "imported": len(all_tasks),
        "refresh": refresh,
        "tasks": all_tasks
    }

@app.get("/admin/calendar.ics")
def get_calendar(request: Request, _ = Depends(require_admin)):
    session = SessionLocal()
    try:
        cal = Calendar()
        cal.add("prodid", "-//Org Parser//EN")
        cal.add("version", "2.0")

        for t in session.query(Task).all():
            if t.kind == "event":
                cal.add_component(
                    make_event(t.title, t.ts_start_date, t.ts_start_time,
                               t.ts_end_date, t.ts_end_time)
                    )
            elif t.kind == "task":
                cal.add_component(
                    make_todo(t.title, t.deadline_start_date, t.deadline_start_time, t.todo)
                )
        return Response(cal.to_ical(), media_type="text/calendar")
    finally:
        session.close()

@app.get("/admin/views")
def list_views(request: Request, _ = Depends(require_admin)):
    return VIEWS

@app.get("/view/{token}")
def view_details(request: Request, token: str):
    return VIEWS[token]
    
@app.get("/calendar/{token}/tasks.json")
@limiter.limit("10/minute")
def get_view_tasks(request: Request, token: str):
    """Get a JSON representation of all tasks for a 'view'."""
    session = SessionLocal()
    serialized_tasks = []
    try:
        task_entries = get_tasks_for_view(session, VIEWS, token)
        for entry in task_entries:
            task = entry["task"]
            detail = entry["detail"]
            category = entry["category"]
            serialized_tasks.append(serialize_task(task, category, detail))
        return serialized_tasks
    finally:
        session.close()

@app.get("/calendar/{token}/events.json")
@limiter.limit("10/minute")
def get_view_events(request: Request, token: str):
    """Get a JSON representation of all events for a 'view'."""
    session = SessionLocal()
    serialized_events = []
    try:
        event_entries = get_tasks_for_view(session, VIEWS, token)
        for entry in event_entries:
            event = entry["task"]
            detail = entry["detail"]
            category = entry["category"]
            serialized_events.append(serialize_event(event, category, detail))
        return serialized_events
    finally:
        session.close()

@app.get("/calendar/{token}.ics")
@limiter.limit("30/minute")
def get_calendar_view(request: Request, token: str):
    """Create a multi-calendar .ics feed for a give view TOKEN"""
    session = SessionLocal()
    try:
        task_entries = get_tasks_for_view(session, VIEWS, token)
        cal = Calendar()
        cal.add("prodid", "-//Org Parser//EN")
        cal.add("version", "2.0")
        
        for entry in task_entries:
            task = entry["task"]
            detail = entry["detail"]
            category = entry["category"]
            color = entry["color"]
            title = "Busy" if detail == "time-only" else task.title
            
            if task.kind == "event":
                event = make_event(
                    title,
                    task.ts_start_date,
                    task.ts_start_time,
                    task.ts_end_date,
                    task.ts_end_time)
                if category:
                    event.add("categories", [category])
                if color:
                    event.add("color", color)
                cal.add_component(event)
            elif task.kind == "task":
                todo = make_todo(
                    title,
                    task.deadline_start_date,
                    task.deadline_start_time,
                    task.todo)
                if category:
                    todo.add("categories", [category])
                if color:
                    todo.add("color", color)
                cal.add_component(todo)

        return Response(content=cal.to_ical(), media_type="text/calendar")
    finally:
        session.close()

# Helper Functions

def make_dt(date_str, time_str=None):
    """Convert DB strings to UTC datetime or date."""
    if not date_str:
        return None
    tz = ZoneInfo(TIMEZONE)
    if time_str:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=tz)
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def make_event(title, start_date, start_time, end_date=None, end_time=None):
    event = Event()
    event.add("uid", str(uuid.uuid4()))
    event.add("dtstamp", datetime.now(timezone.utc))
    event.add("summary", title)
    
    dtstart = make_dt(start_date, start_time)
    if isinstance(dtstart, datetime):
        event.add("dtstart", dtstart, parameters={"TZID": TIMEZONE})
    else:
        event.add("dtstart", dtstart)
    dtend = make_dt(end_date, end_time)
    if dtend:
        if isinstance(dtend, datetime):
            event.add("dtend", dtend, parameters={"TZID": TIMEZONE})
        else:
            event.add("dtend", dtend)
    return event

def make_todo(title, due_date=None, due_time=None, todo_value=None):
    todo = Todo()
    todo.add("uid", str(uuid.uuid4()))
    todo.add("dtstamp", datetime.now(timezone.utc))
    todo.add("summary", title)
    if todo_value:
        todo.add("status", todo_value)
        
    due = make_dt(due_date, due_time)
    if due:
        if isinstance(due, datetime):
            todo.add("due", due, parameters={"TZID": TIMEZONE})
        else:
            todo.add("due", due)
    return todo

# Additional TODO fields to add (based on fields defined in github.com/ical-org/ical.net/wiki
# PRIORITY, STATUS (todo)
# Custom field for scheduled?
# Handle repeaters? Would need RRULE for timestamp repeater, and custom RRULE for scheduled and deadline repeaters.
        
# Debugging functions.
# Endpoints are deactivated - useful if something breaks in future.        

#@app.get("/tasks")
def get_tasks():
    """Return a dict of all tasks in the db."""
    # THIS NEEDS TO BE REWORKED FOR NEW 'calendar' ARCHITECTURE
    session = SessionLocal()
    try:
        tasks = session.query(Task).all()
        return {"tasks": [t.__dict__ for t in tasks]}
    finally:
        session.close()



# Deprecated        
#@app.post("/admin/verify")
#def verify_admin_password(authorized: bool = Depends(verify_admin)):
def verify_admin_password():        
    """Used by frontend to validate admin password."""
    return {"status": "ok"}        
