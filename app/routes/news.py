from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.database import get_db
from app.models.news import News
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/")
def read_news(
    request: Request,
    q: str = Query(None, description="Search query for news titles"),
    page: int = Query(1, description="Page number", ge=1),
    db: Session = Depends(get_db)
):
    limit = 12
    offset = (page - 1) * limit
    
    query = db.query(News)
    
    if q:
        # Search by title
        query = query.filter(News.title.ilike(f"%{q}%"))
        
    # Order by published_date descending (newest first)
    # Using created_at as a fallback if published_date is null
    query = query.order_by(desc(News.published_date), desc(News.created_at))
    
    total_items = query.count()
    total_pages = (total_items + limit - 1) // limit
    
    news_items = query.offset(offset).limit(limit).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "news_items": news_items,
        "page": page,
        "total_pages": total_pages,
        "q": q or ""
    })
