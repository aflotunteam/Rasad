from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.responses import ok

router = APIRouter(tags=["Tizim"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return ok({"status": "ok", "service": "rasad-api", "version": "0.1.0"})
