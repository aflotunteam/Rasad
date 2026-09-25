from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.responses import ok
from app.services.analytics import dashboard

router = APIRouter(tags=["Bosh sahifa"])


@router.get("/dashboard")
def get_dashboard(
    region: str | None = Query(None, max_length=8),
    cu: CurrentUser = Depends(require("dashboard")),
    db: Session = Depends(get_db),
):
    return ok(dashboard(db, region, cu.region_scope))


@router.get("/regions")
def regions(cu: CurrentUser = Depends(require("dashboard")), db: Session = Depends(get_db)):
    return ok(dashboard(db, None, cu.region_scope)["regions"])
