from fastapi import FastAPI
from app.database.database import create_db_dump
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from app.scraper.scraper import start_scraping
from app.server.server_states import Scraper_state

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database.database import create_db_dump
from datetime import datetime, timedelta

# 1. Setup the Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the API starts
    
    #trigger in one minute for test.
    next_min = datetime.now() + timedelta(minutes=1)

    scheduler.add_job(
        create_db_dump, 
        CronTrigger(hour=next_min.hour, minute=next_min.minute),
        id="daily_dump",
        replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started: Daily dump set for {next_min.hour}h:{next_min.minute}m")
    
    yield
    
    # This runs when the API shuts down
    scheduler.shutdown()
    print("Scheduler stopped.")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def read_root():
    return {"status": "Server is online"}

@app.get("/save_dump")
async def save_dumps():
    status = await create_db_dump()
    return {"status": status}


state = Scraper_state()

@app.get("/start_scraping")
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    pages: int = Query(default=1, alias="limit", ge=1),
    workers: int = Query(default=3, ge=1, le=10)
):
    if state.is_running:
        raise HTTPException(status_code=409, detail="Already busy")
    
    background_tasks.add_task(start_scraping, state, workers, pages)

    return {
        "status": "Scraping started",
        "config": {
            "workers": workers,
            "limit_pages": pages
        },
        "message": "The scraper is running in the background. Check logs or database for progress."
    }