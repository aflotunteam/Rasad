"""Ma'lumotnomalar: hududlar, sohalar, xavf tasnifi, holat yorliqlari."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import ROLE_LABELS, CurrentUser, get_current_user
from app.core.responses import ok
from app.models import DataSource, ModelRegistry, Region, RiskScore, Sector
from app.services.common import (
    ALERT_STATUS_LABELS,
    EXPERT_STATUS_LABELS,
    LEVEL_LABELS,
    SIZE_LABELS,
    get_thresholds,
)
from app.services.data_quality import DIMENSIONS, LOW_DQ
from data_gen.reference import RELATION_TYPES, RISK_TYPES

router = APIRouter(tags=["Ma'lumotnomalar"])

DECISION_LABELS = {
    "confirmed": "Tasdiqlandi",
    "rejected": "Rad etildi",
    "need_info": "Qo‘shimcha ma’lumot kerak",
    "sent_review": "Tekshiruvga yuborildi",
}


@router.get("/meta")
def meta(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    low, high = get_thresholds(db)
    active = db.scalar(select(ModelRegistry).where(ModelRegistry.status == "ACTIVE"))
    last = db.scalar(select(func.max(RiskScore.computed_at)))
    period = db.execute(select(RiskScore.period_start, RiskScore.period_end, RiskScore.data_version).limit(1)).first()
    freshest = db.scalar(select(func.max(DataSource.last_load_at)).where(DataSource.status == "active"))
    return ok({
        "regions": [
            {"id": r.id, "name": r.name, "short_name": r.short_name, "geo_key": r.geo_key}
            for r in db.scalars(select(Region).order_by(Region.sort_order))
        ],
        "sectors": [{"id": s.id, "name": s.name, "icon": s.icon} for s in db.scalars(select(Sector).order_by(Sector.name))],
        "risk_types": [{"code": c, "name": n, "icon": i, "description": d} for c, n, i, d in RISK_TYPES],
        "relation_types": RELATION_TYPES,
        "levels": LEVEL_LABELS,
        "expert_statuses": EXPERT_STATUS_LABELS,
        "decision_types": DECISION_LABELS,
        "alert_statuses": ALERT_STATUS_LABELS,
        "size_groups": SIZE_LABELS,
        "roles": ROLE_LABELS,
        "dq_dimensions": DIMENSIONS,
        "dq_low_threshold": LOW_DQ,
        "thresholds": {"low": low, "high": high, "is_mvp_default": True},
        "active_model": None if active is None else {"name": active.name, "version": active.version,
                                                     "key": active.model_key},
        "last_computed_at": last.isoformat() if last else None,
        "data_freshness_at": freshest.isoformat() if freshest else None,
        "period": None if period is None else {
            "start": period.period_start.isoformat(), "end": period.period_end.isoformat(),
            "data_version": period.data_version,
        },
        "synthetic": True,
    })
