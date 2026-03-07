import feedparser
import logging
import re
from datetime import datetime, timezone
from html import unescape
from time import mktime
import os
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.news import News

logger = logging.getLogger(__name__)

RSS_FEED_URL = os.getenv("RSS_FEED_URL", "https://www.periodicocubano.com/feed/")

def clean_html(raw_html: str) -> str:
    """Helper functional to clean simple HTML tags from excerpts if present."""
    if not raw_html:
        return ""
    text = unescape(raw_html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _entry_published_datetime(entry: dict) -> datetime | None:
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published_parsed:
        return None
    try:
        # feedparser gives time.struct_time; store as UTC-naive for SQLite simplicity
        return datetime.fromtimestamp(mktime(published_parsed), tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def fetch_rss_items(feed_url: str = RSS_FEED_URL) -> list[dict]:
    """Download and parse RSS, returning normalized news dicts."""
    logger.info("Fetching RSS feed: %s", feed_url)
    feed = feedparser.parse(feed_url)

    if getattr(feed, "bozo", False):
        exc = getattr(feed, "bozo_exception", None)
        logger.warning("RSS feed parse warning (bozo=1): %s", exc)

    items: list[dict] = []
    for entry in getattr(feed, "entries", []) or []:
        url = (entry.get("link") or "").strip()
        title = (entry.get("title") or "").strip() or "Sin título"
        raw_summary = entry.get("summary") or entry.get("description") or ""
        summary = clean_html(raw_summary)
        published_date = _entry_published_datetime(entry)

        if not url:
            continue

        items.append(
            {
                "title": title[:255],
                "url": url[:500],
                "summary": summary,
                "published_date": published_date,
            }
        )

    logger.info("Parsed %s entries from RSS", len(items))
    return items


def store_news_items(db: Session, items: list[dict]) -> int:
    """Insert new items into DB, skipping duplicates by URL. Returns inserted count."""
    if not items:
        return 0

    urls = [item["url"] for item in items if item.get("url")]
    if not urls:
        return 0

    existing_urls = set(db.execute(select(News.url).where(News.url.in_(urls))).scalars().all())

    inserted = 0
    for item in items:
        url = item.get("url")
        if not url or url in existing_urls:
            continue

        db.add(
            News(
                title=item.get("title") or "Sin título",
                url=url,
                summary=item.get("summary") or "",
                published_date=item.get("published_date"),
            )
        )
        existing_urls.add(url)
        inserted += 1

    if inserted:
        db.commit()
    return inserted

def fetch_and_store_news(db: Session):
    """
    Fetches the RSS feed from Periódico Cubano and stores new items in the database.
    """
    try:
        items = fetch_rss_items(RSS_FEED_URL)
        inserted = store_news_items(db, items)
        if inserted:
            logger.info("Saved %s new articles", inserted)
        else:
            logger.info("No new articles to save")
    except Exception:
        logger.exception("Failed to fetch or store news")
        db.rollback()
