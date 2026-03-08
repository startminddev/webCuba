from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for the MVP, default to news.db in the current directory if not in .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./news.db")

engine = create_engine(
    DATABASE_URL, 
    # check_same_thread=False is needed for SQLite when used with FastAPI
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create database tables if they don't exist."""
    # Ensure models are registered on Base.metadata
    # (important when init_db() is called from contexts that don't import all models)
    from app.models.news import News  # noqa: F401
    from app.models.source import Source  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_news_table()


def _migrate_sqlite_news_table() -> None:
    """Best-effort SQLite migration for adding new columns without Alembic."""
    if "sqlite" not in DATABASE_URL:
        return

    inspector = inspect(engine)
    if "news" not in inspector.get_table_names():
        return

    existing_cols = {col["name"] for col in inspector.get_columns("news")}

    alter_stmts: list[str] = []
    if "country" not in existing_cols:
        alter_stmts.append("ALTER TABLE news ADD COLUMN country VARCHAR(50)")
    if "source_name" not in existing_cols:
        alter_stmts.append("ALTER TABLE news ADD COLUMN source_name VARCHAR(100)")

    if not alter_stmts:
        return

    with engine.begin() as conn:
        for stmt in alter_stmts:
            conn.execute(text(stmt))

        # Backfill existing rows from previous single-feed version
        if "country" not in existing_cols:
            conn.execute(
                text("UPDATE news SET country = :country WHERE country IS NULL OR country = ''"),
                {"country": "Cuba"},
            )
        if "source_name" not in existing_cols:
            conn.execute(
                text(
                    "UPDATE news SET source_name = :source_name WHERE source_name IS NULL OR source_name = ''"
                ),
                {"source_name": "Periódico Cubano"},
            )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
