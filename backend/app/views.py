import os
import sexpdata
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from .models import Task

views_file = os.getenv("VIEWS_FILE")

# --- Parsing ---
def parse_views_file(path: str):
    """Load all views from a Lisp file into memory."""
    with open(path, "r") as f:
        raw = f.read()

    sexprs = sexpdata.loads(f"({raw})") # Wrap so that multiple views parse
    views = {}
    for expr in sexprs:
        view = parse_view(expr)
        views[view["token"]] = view
    return views

def parse_view(expr):
    """Parse a (view ...) form into a dict"""
    assert expr[0].value() == "view", "Not a view form"
    meta, children = extract_meta_and_children(expr[1:])
    calendars = [parse_calendar(c, meta.get(":detail", "full")) for c in children]
    result = {
        "name": meta.get(":name"),
        "token": meta.get(":token"),
        "detail": meta.get(":detail", "full"),
        # "queries": [parse_query(c, meta.get(":detail", "full")) for c in children],
        "calendars": calendars
    }
    return result

def parse_calendar(expr, detail="full"):
    assert expr[0].value() == "calendar"
    meta, children = extract_meta_and_children(expr[1:])
    queries = [parse_query(q, meta.get(":detail", detail)) for q in children]
    return {
        "name": meta.get(":name"),
        "color": meta.get(":color"),
        "detail": meta.get(":detail", detail),
        "queries": queries
    }

def parse_query(expr, detail="full"):
    """Parse a (query ...) form into a dict."""
    assert expr[0].value() == "query", "Not a query form"
    meta, filters = extract_meta_and_children(expr[1:])
    return {
        "detail": meta.get(":detail", detail),
        "filter": normalize_expr(filters[0]), # expect exactly one filter expression, and parse into python primitives
    }

def atom_value(x):
    """Convert sexpdata atoms to python primitives."""
    if isinstance(x, sexpdata.Symbol):
        return str(x)
    if isinstance(x, sexpdata.Quoted):
        return atom_value(x.value())
    return x

def normalize_expr(expr):
    """Recursively convert sexpdata AST to plain python lists/strings"""
    if isinstance(expr, list):
        return  [normalize_expr(e) for e in expr]
    return atom_value(expr)

def extract_meta_and_children(parts):
    """Helper: split keyword/value pairs from child s-exprs."""
    meta = {}
    children = []
    i = 0
    while i < len(parts):
        if isinstance(parts[i], sexpdata.Symbol) and str(parts[i]).startswith(":"):
            key = str(parts[i])
            val = atom_value(parts[i+1])
            meta[key] = val
            # meta[str(parts[i])] = parts[i+1].value() if isinstance(parts[i+1], sexpdata.Quoted) else parts[i+1]
            i += 2
        else:
            children.append(parts[i])
            i += 1
    return meta, children


# --- Filter Eval ---
def eval_filter(expr):
    """Translate filter s-expr into SQLAlchemy condition."""
    # head = expr[0].value() if isinstance(expr[0], sexpdata.Symbol) else expr[0]
    head = atom_value(expr[0])
    # args = [atom_value(a) if not isinstance(a, list) else a for a in expr[1:]]
    args = [a if isinstance(a, list) else atom_value(a) for a in expr[1:]]

    if head == "and":
        return and_(*[eval_filter(e) for e in expr[1:]])
    if head == "or":
        return or_(*[eval_filter(e) for e in expr[1:]])
    if head == "not":
        return ~eval_filter(expr[1])

    if head == "tag":
        return Task.tags.like(f"%{expr[1]}%")
    if head == "todo":
        return Task.todo == expr[1]
    if head == "kind":
        return Task.kind == expr[1]
    if head == "file":
        return Task.file == expr[1]

    if head == "scheduled_after":
        return Task.scheduled_start_date >= expr[1]
    if head == "scheduled_before":
        return Task.scheduled_start_date <= expr[1]
    if head == "deadline_after":
        return Task.deadline_start_date >= expr[1]
    if head == "deadline_before":
        return Task.deadline_start_date <= expr[1]

    raise ValueError(f"Unknown filter operator: {head}")

def get_tasks_for_view(session: Session, views: dict, token: str):
    """Fetch all tasks/events for a given view, tagging each with its calendar name."""
    view = views.get(token)
    if not view:
        return []

    results = []
    seen = {}  # task.id -> (task, detail, calendar_name)
    # Rule: Keep higher priorities
    priority = {"full": 1, "summary-only": 2, "time-only": 3}

    for calendar in view.get("calendars", []):
        calendar_name = calendar.get("name")
        calendar_detail = calendar.get("detail", view.get("detail", "NOTHING"))
        print(calendar_name + ": " + calendar_detail)
        calendar_color = calendar.get("color")

        for query in calendar.get("queries", []):
            condition = eval_filter(query["filter"])
            q = session.query(Task).filter(condition)
            tasks = q.all()

            for t in tasks:
                entry = {
                    "task": t,
                    "detail": query.get("detail", calendar_detail),
                    "category": calendar_name,
                    "color": calendar_color,
                }

                # If already seen, determine overwrite
                if t.id in seen:
                    # Last calendar wins OR higher detail wins
                    current = seen[t.id]
                    if priority[entry["detail"]] > priority[current["detail"]]:
                        seen[t.id] = entry
                    else:
                        # same or lesser detail → last-defined calendar wins anyway
                        seen[t.id] = entry
                else:
                    seen[t.id] = entry

    result = list(seen.values())
    # print(result)
    return result

