from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.errors import AppError, ErrorCode, Forbidden
from app.core.responses import ok
from app.models import Alert, Subject, User

router = APIRouter(prefix="/alerts", tags=["Ogohlantirishlar"])

Status = Literal["new", "in_review", "confirmed", "rejected", "closed"]


def alert_payload(a: Alert) -> dict:
    return {
        "id": a.id, "code": a.code, "subject_code": a.subject.code, "sector_id": a.subject.sector_id,
        "region_id": a.region_id, "risk_type": a.risk_type, "severity": a.severity, "score": a.score,
        "status": a.status, "detected_at": a.detected_at.isoformat(), "updated_at": a.updated_at.isoformat(),
        "analyst": None if a.analyst is None else {"id": a.analyst.id, "full_name": a.analyst.full_name},
    }


@router.get("")
def list_alerts(
    status: Status | None = None,
    severity: Literal["high", "medium"] | None = None,
    region: str | None = Query(None, max_length=8),
    risk_type: str | None = Query(None, pattern=r"^R0[1-8]$"),
    analyst_id: int | None = None,
    q: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    cu: CurrentUser = Depends(require("alerts.read")),
    db: Session = Depends(get_db),
):
    conds = []
    region = cu.region_scope or region
    if region:
        conds.append(Alert.region_id == region)
    if status:
        conds.append(Alert.status == status)
    if severity:
        conds.append(Alert.severity == severity)
    if risk_type:
        conds.append(Alert.risk_type == risk_type)
    if analyst_id:
        conds.append(Alert.analyst_id == analyst_id)
    if q:
        term = q.strip().upper()
        conds.append(Subject.code.like(f"%{term}%") | Alert.code.like(f"%{term}%"))
    base = select(Alert).join(Subject, Subject.id == Alert.subject_id)
    if conds:
        base = base.where(and_(*conds))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.scalars(base.options(joinedload(Alert.subject), joinedload(Alert.analyst))
                      .order_by(desc(Alert.score), desc(Alert.detected_at))
                      .offset((page - 1) * page_size).limit(page_size)).unique().all()

    counts_q = select(Alert.status, func.count()).group_by(Alert.status)
    if cu.region_scope:
        counts_q = counts_q.where(Alert.region_id == cu.region_scope)
    counts = dict(db.execute(counts_q).all())
    return ok({"items": [alert_payload(a) for a in rows], "total": total, "page": page, "page_size": page_size,
               "counts": counts})


@router.get("/analysts")
def analysts(cu: CurrentUser = Depends(require("alerts.read")), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.role.in_(["analyst", "admin"]), User.is_active.is_(True)))
    return ok([{"id": u.id, "full_name": u.full_name, "region_id": u.region_id} for u in rows])


class AlertUpdate(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    status: Status | None = None
    analyst_id: int | None = None
    unassign: bool = False


@router.patch("")
def update_alerts(body: AlertUpdate, cu: CurrentUser = Depends(require("alerts.write")),
                  db: Session = Depends(get_db)):
    if body.status is None and body.analyst_id is None and not body.unassign:
        raise AppError(ErrorCode.DATA_VALIDATION, "O‘zgartirish uchun holat yoki mas’ul xodim ko‘rsatilmagan")
    if body.analyst_id is not None:
        analyst = db.get(User, body.analyst_id)
        if analyst is None or analyst.role not in ("analyst", "admin"):
            raise AppError(ErrorCode.DATA_VALIDATION, "Mas’ul xodim topilmadi")
    rows = db.scalars(select(Alert).options(joinedload(Alert.subject), joinedload(Alert.analyst))
                      .where(Alert.id.in_(body.ids))).unique().all()
    now = datetime.now(timezone.utc)
    changed = []
    for a in rows:
        if cu.region_scope and a.region_id != cu.region_scope:
            raise Forbidden("Ogohlantirish sizga biriktirilgan hududga tegishli emas")
        old = {"status": a.status, "analyst_id": a.analyst_id}
        if body.status:
            a.status = body.status
        if body.analyst_id is not None:
            a.analyst_id = body.analyst_id
        if body.unassign:
            a.analyst_id = None
        a.updated_at = now
        record(db, cu, "alert.update", "alert", a.code, old=old,
               new={"status": a.status, "analyst_id": a.analyst_id})
        changed.append(a)
    db.commit()
    for a in changed:
        db.refresh(a)
    return ok({"updated": len(changed), "items": [alert_payload(a) for a in changed]})
