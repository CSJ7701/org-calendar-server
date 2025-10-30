import asyncio
import os
import logging
from .sync import sync_repo

logger = logging.getLogger("org-cal.sync")

SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))
SYNC_RETRY = int(os.getenv("SYNC_RETRY_SECONDS", "60"))

async def run_sync_cycle():
    try:
        result = await asyncio.to_thread(sync_repo) # Non-blocking
        if result["status"] == "success":
            logger.info(f"Repo synced to {result['commit_hash']}")
        else:
            logger.error(f"Sync failed: {result['log']}")
        return result
    except Exception as e:
        logger.exception(f"Unexpected error during sync: {e}")
        return {"status": "failure", "log": str(e)}
