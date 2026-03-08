import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database.database import SessionLocal, init_db
from app.models.news import News
from app.models.source import Source  # noqa: F401
from app.routes.news import router as news_router
from app.services.rss_service import ensure_default_sources, fetch_and_store_all_sources
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="News Aggregator (RSS por país)")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(news_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()

    # Initial load if DB is empty
    db = SessionLocal()
    try:
        ensure_default_sources(db)
        logger.info("Running RSS update for all sources on startup")
        fetch_and_store_all_sources(db)
    except Exception:
        logger.exception("Startup initial fetch failed")
    finally:
        db.close()

    start_scheduler()
    logger.info("Scheduler started (every 30 minutes)")


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()
    logger.info("Scheduler stopped")
