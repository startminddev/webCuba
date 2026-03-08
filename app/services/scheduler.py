from apscheduler.schedulers.background import BackgroundScheduler
from app.services.rss_service import fetch_and_store_all_sources
from app.database.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def job_fetch_news():
    db = SessionLocal()
    try:
        inserted = fetch_and_store_all_sources(db)
        logger.info("Scheduler ingest finished: %s new items", inserted)
    except Exception:
        logger.exception("Scheduler job failed")
    finally:
        db.close()

scheduler = BackgroundScheduler(timezone="UTC")

def start_scheduler():
    if scheduler.running:
        return

    # Run the job every 30 minutes
    scheduler.add_job(
        job_fetch_news,
        "interval",
        minutes=30,
        id="fetch_news_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
