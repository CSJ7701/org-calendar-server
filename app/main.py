from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
import logging
import sys
from .db import Base, engine
from .sync import sync_repo
from .sync_worker import run_sync_cycle, SYNC_INTERVAL, SYNC_RETRY

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)

@app.on_event("startup")
@repeat_every(seconds=SYNC_INTERVAL, wait_first=False, raise_exceptions=True)
async def periodic_task() -> None:
    await run_sync_cycle()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/admin/sync")
def trigger_sync():
    from .sync import sync_repo
    return sync_repo()
    

