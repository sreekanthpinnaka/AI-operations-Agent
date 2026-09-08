from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "app_name": get_settings().app_name,
        "database_connected": db_ok,
        "openai_configured": bool(get_settings().openai_api_key),
        "model": get_settings().openai_model,
        "gemini_configured": bool(get_settings().gemini_api_key),
    }
