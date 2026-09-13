from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.core.config import settings
from datetime import datetime
try:
    import redis
except ImportError:
    redis = None

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    
    # Check Redis (optional)
    redis_status = "ok"
    if redis is None:
        redis_status = "not_installed"
    else:
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
        except Exception:
            redis_status = "error"
    
    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status,
        }
    }