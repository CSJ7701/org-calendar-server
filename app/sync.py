import os
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Snapshot

REPO_DIR = "/data/repo"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(
        cmd, cwd=cwd, text=True, capture_output=True, shell=True
    )
    return result.returncode, result.stdout, result.stderr

def sync_repo():
    repo_url = os.getenv("REPO_URL")
    branch = os.getenv("REPO_BRANCH", "main")
    github_token = os.getenv("GITHUB_TOKEN")

    if github_token and repo_url.startswith("https://"):
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(repo_url)
        repo_url = urlunparse(parsed._replace(netloc=f"{github_token}@{parsed.netloc}"))

    db: Session = SessionLocal()
    snapshot = Snapshot(timestamp=datetime.utcnow())

    try:
        if not os.path.exists(REPO_DIR):
            code, out, err = run_cmd(f"git clone -b {branch} {repo_url} {REPO_DIR}")
        else:
            code, out, err = run_cmd("git fetch origin", cwd=REPO_DIR)
            if code == 0:
                code, out, err = run_cmd(f"git reset --hard origin/{branch}", cwd=REPO_DIR)

        if code != 0:
            snapshot.status = "failure"
            snapshot.log = err
        else:
            code, out, err = run_cmd("git rev-parse HEAD", cwd=REPO_DIR)
            snapshot.commit_hash = out.strip()
            snapshot.status = "success"
            snapshot.log = out

    except Exception as e:
        snapshot.status = "failure"
        snapshot.log = str(e)

    result = {
        "commit_hash": snapshot.commit_hash,
        "status": snapshot.status,
        "log": snapshot.log,
        "timestamp": snapshot.timestamp.isoformat(),
    }
        
    db.add(snapshot)
    db.commit()    
    db.close()
    return result
        
