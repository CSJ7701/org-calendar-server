from fastapi import FastAPI
from .db import Base, engine
from .sync import sync_repo

app = FastAPI()

# Initialize DB
Base.metadata.create_all(bind=engine)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/admin/sync")
def trigger_sync():
    return sync_repo()
    
