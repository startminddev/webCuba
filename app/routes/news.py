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

COUNTRIES = [
    {"key": "cuba", "label": "Cuba"},
    {"key": "venezuela", "label": "Venezuela"},
    {"key": "espana", "label": "España"},
]

COUNTRY_KEY_TO_LABEL = {c["key"]: c["label"] for c in COUNTRIES}
COUNTRY_LABELS = set(COUNTRY_KEY_TO_LABEL.values())

@router.get("/")
def read_news(
    request: Request,
    country: str = Query("cuba", description="Country filter"),
    q: str = Query(None, description="Search query for news titles"),
    page: int = Query(1, description="Page number", ge=1),
    db: Session = Depends(get_db)
):
    limit = 12
    offset = (page - 1) * limit

    # Accept both key (espana) and label (España) for compatibility
    if country in COUNTRY_KEY_TO_LABEL:
        country_key = country
        country_label = COUNTRY_KEY_TO_LABEL[country]
    elif country in COUNTRY_LABELS:
        country_label = country
        country_key = next((k for k, v in COUNTRY_KEY_TO_LABEL.items() if v == country_label), "cuba")
    else:
        country_key = "cuba"
        country_label = COUNTRY_KEY_TO_LABEL[country_key]
    
    query = db.query(News).filter(News.country == country_label)
    
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
        ,
        "country": country_key,
        "country_label": country_label,
        "countries": COUNTRIES,
    })
