import feedparser
import logging
import re
from datetime import datetime, timezone
from html import unescape
from time import mktime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.news import News
from app.models.source import Source

logger = logging.getLogger(__name__)

DEFAULT_SOURCES: list[dict] = [
    {
        "name": "Periódico Cubano",
        "rss_url": "https://www.periodicocubano.com/feed/",
        "country": "Cuba",
    },
    {
        "name": "El Pepazo",
        "rss_url": "https://elpepazo.com/rss/latest-posts",
        "country": "Venezuela",
    },
    {
        "name": "El País (España)",
        "rss_url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
        "country": "España",
    },
]

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


def fetch_rss_items(feed_url: str) -> list[dict]:
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

        title = item.get("title") or "Sin título"
        source_name = item.get("source_name")

        # Optional secondary deduplication: title + source_name
        if source_name:
            existing_by_title = db.execute(
                select(News.id).where(News.title == title, News.source_name == source_name).limit(1)
            ).scalar_one_or_none()
            if existing_by_title is not None:
                continue

        db.add(
            News(
                title=title,
                url=url,
                summary=item.get("summary") or "",
                published_date=item.get("published_date"),
                country=item.get("country"),
                source_name=source_name,
            )
        )
        existing_urls.add(url)
        inserted += 1

    if inserted:
        db.commit()
    return inserted


def ensure_default_sources(db: Session) -> None:
    """Seed default RSS sources if none exist."""
    existing = db.query(Source.id).limit(1).count()
    if existing:
        return

    for src in DEFAULT_SOURCES:
        db.add(
            Source(
                name=src["name"],
                rss_url=src["rss_url"],
                country=src["country"],
                active=True,
            )
        )
    db.commit()


def fetch_and_store_source(db: Session, source: Source) -> int:
    """Fetch a single RSS source and store new items. Continues on feed warnings."""
    items = fetch_rss_items(source.rss_url)
    for item in items:
        item["country"] = source.country
        item["source_name"] = source.name
    return store_news_items(db, items)


def fetch_and_store_all_sources(db: Session) -> int:
    """Fetch all active sources; continue even if one fails. Returns total inserted."""
    ensure_default_sources(db)

    total_inserted = 0
    sources = db.query(Source).filter(Source.active == True).all()  # noqa: E712
    for source in sources:
        try:
            logger.info("Updating source: %s (%s)", source.name, source.country)
            inserted = fetch_and_store_source(db, source)
            total_inserted += inserted
            logger.info("Source updated: %s new items", inserted)
        except Exception:
            logger.exception("Failed updating source: %s", source.rss_url)
            db.rollback()
            continue

    return total_inserted
