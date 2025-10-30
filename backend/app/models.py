from sqlalchemy import Column, Integer, String, Date, Time, Boolean, DateTime, Enum
from datetime import datetime
from .db import Base

class Placeholder(Base):
    __tablename__ = "placeholders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    commit_hash = Column(String, nullable=True)
    status = Column(String, default="pending")
    log = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    todo = Column(String, nullable=True)

    # Scheduled timestamp details
    scheduled_start_date = Column(String, nullable=True)    # YYYY-MM-DD
    scheduled_start_time = Column(String, nullable=True)    # HH:MM
    scheduled_end_date   = Column(String, nullable=True)    # YYYY-MM-DD
    scheduled_end_time   = Column(String, nullable=True)    # HH:MM
    scheduled_all_day    = Column(Boolean, default=False)
    # Repeater info
    scheduled_repeater_type  = Column(String, nullable=True)    # "+", "++", ".+"
    scheduled_repeater_value = Column(Integer, nullable=True)   # e.g. 1
    scheduled_repeater_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"
    # Warning info
    scheduled_warning_type  = Column(String, nullable=True)    # "-" (warning), "--" (delay)
    scheduled_warning_value = Column(Integer, nullable=True)   # e.g. 2
    scheduled_warning_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"

    # Deadline timestamp details
    deadline_start_date = Column(String, nullable=True)    # YYYY-MM-DD
    deadline_start_time = Column(String, nullable=True)    # HH:MM
    deadline_end_date   = Column(String, nullable=True)    # YYYY-MM-DD
    deadline_end_time   = Column(String, nullable=True)    # HH:MM
    deadline_all_day    = Column(Boolean, default=False)
    # Repeater info
    deadline_repeater_type  = Column(String, nullable=True)    # "+", "++", ".+"
    deadline_repeater_value = Column(Integer, nullable=True)   # e.g. 1
    deadline_repeater_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"
    # Warning info
    deadline_warning_type  = Column(String, nullable=True)    # "-" (warning), "--" (delay)
    deadline_warning_value = Column(Integer, nullable=True)   # e.g. 2
    deadline_warning_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"

    # Generic timestamp details (used for events)
    ts_start_date = Column(String, nullable=True)    # YYYY-MM-DD
    ts_start_time = Column(String, nullable=True)    # HH:MM
    ts_end_date   = Column(String, nullable=True)    # YYYY-MM-DD
    ts_end_time   = Column(String, nullable=True)    # HH:MM
    ts_all_day    = Column(Boolean, default=False)
    # Repeater info
    ts_repeater_type  = Column(String, nullable=True)    # "+", "++", ".+"
    ts_repeater_value = Column(Integer, nullable=True)   # e.g. 1
    ts_repeater_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"
    # Warning info
    ts_warning_type  = Column(String, nullable=True)    # "-" (warning), "--" (delay)
    ts_warning_value = Column(Integer, nullable=True)   # e.g. 2
    ts_warning_unit  = Column(String, nullable=True)    # "d", "w", "m", "y"

    # Other metadata
    tags = Column(String, nullable=True)        # "work,personal"
    file = Column(String, nullable=True)        # /data/work.org
    parent = Column(String, nullable=True)      # "Headline"
    kind = Column(String, default="task")       # "task" or "event"    
    created_at = Column(DateTime, default=datetime.utcnow)


def serialize_task(task, category, detail="full"):
    return {
        "id": task.id,
        "title": task.title if detail != "time-only" else "Busy",
        "category": category,
        "todo": task.todo,
        "kind": task.kind,
        "scheduled_start_date": task.scheduled_start_date,
        "scheduled_start_time": task.scheduled_start_time,
        "scheduled_end_date": task.scheduled_end_date,
        "scheduled_end_time": task.scheduled_end_time,
        "tags": task.tags,
        "detail_level": detail
    }

def serialize_event(event, category, detail="full"):
    return {
        "id": event.id,
        "title": event.title if detail != "time-only" else "Busy",
        "category": category,
        "kind": event.kind,
        "tags": event.tags,
        "file": event.file,
        "ts_start_date": event.ts_start_date,
        "ts_start_time": event.ts_start_time,
        "ts_end_date": event.ts_end_date,
        "ts_end_time": event.ts_end_time
    }
        
