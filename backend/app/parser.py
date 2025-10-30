import subprocess
import os
import json
from pathlib import Path
from .db import SessionLocal
from .models import Task

SCRIPT_PATH = Path(__file__).parent / "org-to-json.el"

def get_org_files() -> list[str]:
    files = os.getenv("ORG_FILES", "")
    return [f.strip() for f in files.split(",") if f.strip()]

def parse_org_file(file_path: str) -> list[dict]:
    """Run Emacs in batch mode to extract tasks from an org file as JSON."""
    cmd = [
        "emacs", "--batch",
        "-l", str(SCRIPT_PATH),
        "--eval", f"(find-file \"{file_path}\")",
        "-f", "cal-server/org-extract-tasks"
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

def refresh_db():
    """
    Wipe existing rows in the database so we can re-import.
    """
    session = SessionLocal()
    try:
        session.query(Task).delete()
        session.commit()
    finally:
        session.close()
            

def import_tasks(parsed_tasks: list[dict]):
    """
    Import parsed tasks into the database

    
    """
    session = SessionLocal()
    try:
        for task in parsed_tasks:
            db_task = Task(
                title=task.get("title"),
                todo=task.get("todo"),
                tags=",".join(task.get("tags")) if isinstance(task.get("tags"), list) else task.get("tags"),
                file=task.get("file"),
                parent=task.get("parent"),
                kind=task.get("kind"),
                
                scheduled_start_date=task.get("scheduled_start_date"),
                scheduled_start_time=task.get("scheduled_start_time"),
                scheduled_end_date=task.get("scheduled_end_date"),
                scheduled_end_time=task.get("scheduled_end_time"),
                scheduled_all_day=task.get("scheduled_all_day", False),
                scheduled_repeater_type=task.get("scheduled_repeater_type"),
                scheduled_repeater_value=task.get("scheduled_repeater_value"),
                scheduled_repeater_unit=task.get("scheduled_repeater_unit"),
                scheduled_warning_type=task.get("scheduled_warning_type"),
                scheduled_warning_value=task.get("scheduled_warning_value"),
                scheduled_warning_unit=task.get("scheduled_warning_unit"),
                
                deadline_start_date=task.get("deadline_start_date"),
                deadline_start_time=task.get("deadline_start_time"),
                deadline_end_date=task.get("deadline_end_date"),
                deadline_end_time=task.get("deadline_end_time"),
                deadline_all_day=task.get("deadline_all_day", False),
                deadline_repeater_type=task.get("deadline_repeater_type"),
                deadline_repeater_value=task.get("deadline_repeater_value"),
                deadline_repeater_unit=task.get("deadline_repeater_unit"),
                deadline_warning_type=task.get("deadline_warning_type"),
                deadline_warning_value=task.get("deadline_warning_value"),
                deadline_warning_unit=task.get("deadline_warning_unit"),
                
                ts_start_date=task.get("timestamp_start_date"),
                ts_start_time=task.get("timestamp_start_time"),
                ts_end_date=task.get("timestamp_end_date"),
                ts_end_time=task.get("timestamp_end_time"),
                ts_all_day=task.get("timestamp_all_day", False),
                ts_repeater_type=task.get("timestamp_repeater_type"),
                ts_repeater_value=task.get("timestamp_repeater_value"),
                ts_repeater_unit=task.get("timestamp_repeater_unit"),
                ts_warning_type=task.get("timestamp_warning_type"),
                ts_warning_value=task.get("timestamp_warning_value"),
                ts_warning_unit=task.get("timestamp_warning_unit"),                
            )
            session.add(db_task)
        session.commit()
    finally:
        session.close()

