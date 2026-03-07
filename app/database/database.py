from sqlalchemy import create_engine
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
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
