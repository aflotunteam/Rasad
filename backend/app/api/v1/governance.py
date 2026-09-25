"""Modellar reestri, monitoring, audit, sozlamalar va foydalanuvchilar."""

from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import ROLE_LABELS, CurrentUser, require
from app.core.errors import AppError, ErrorCode, NotFound
from app.core.responses import ok
from app.models import AppSetting, AuditLog, ExpertDecision, ModelRegistry, Region, User
from app.services.common import get_thresholds

router = APIRouter(tags=["Boshqaruv"])

# Faqat artefakti mavjud (kodda amalga oshirilgan) model versiyalari faollashtirilishi mumkin.
IMPLEMENTED = {("rasad-risk", "1.0.0"), ("rasad-risk", "0.9.0")}
TRANSITIONS = {
    "DRAFT": {"TESTING", "ARCHIVED"},
    "TESTING": {"APPROVED", "DRAFT", "ARCHIVED"},
    "APPROVED": {"ACTIVE", "ARCHIVED"},
    "ACTIVE": set(),
    "ARCHIVED": {"DRAFT"},
}


def model_payload(m: ModelRegistry) -> dict:
    drift = dict(m.drift or {})
    drift.pop("series", None)
    return {
        "id": m.id, "key": m.model_key, "name": m.name, "version": m.version, "algorithm": m.algorithm,
        "training_dataset": m.training_dataset, "features": m.features, "metrics": m.metrics,
        "threshold": m.threshold, "drift": drift, "status": m.status, "created_by": m.created_by,
        "approved_by": m.approved_by, "approved_at": m.approved_at.isoformat() if m.approved_at else None,
        "created_at": m.created_at.isoformat(), "implemented": (m.model_key, m.version) in IMPLEMENTED,
        "allowed_transitions": sorted(TRANSITIONS.get(m.status, set())),
    }


@router.get("/models")
def list_models(cu: CurrentUser = Depends(require("models.read")), db: Session = Depends(get_db)):
    rows = db.scalars(select(ModelRegistry).order_by(ModelRegistry.model_key, desc(ModelRegistry.created_at)))
    return ok([model_payload(m) for m in rows])


class StatusIn(BaseModel):
    status: Literal["DRAFT", "TESTING", "APPROVED", "ACTIVE", "ARCHIVED"]


@router.post("/models/{model_id}/status")
def change_status(model_id: int, body: StatusIn, cu: CurrentUser = Depends(require("models.write")),
                  db: Session = Depends(get_db)):
    m = db.get(ModelRegistry, model_id)
    if m is None:
        raise NotFound("Model topilmadi")
    if body.status == "ACTIVE" and m.status != "APPROVED":
        raise AppError(ErrorCode.MODEL_RULE, "Tekshirilmagan model faol bo‘la olmaydi. Avval modelni tasdiqlang.", 409)
    if body.status not in TRANSITIONS.get(m.status, set()):
        raise AppError(ErrorCode.MODEL_RULE, f"{m.status} holatidan {body.status} holatiga o‘tish mumkin emas", 409)
    if body.status == "ACTIVE" and (m.model_key, m.version) not in IMPLEMENTED:
        raise AppError(ErrorCode.MODEL_RULE, "Model artefakti mavjud emas: bu versiyani faollashtirib bo‘lmaydi", 409)
    old = m.status
    if body.status == "APPROVED":
        m.approved_by, m.approved_at = cu.user.full_name, datetime.now(timezone.utc)
    if body.status == "ACTIVE":
        for other in db.scalars(select(ModelRegistry).where(ModelRegistry.model_key == m.model_key,
                                                            ModelRegistry.status == "ACTIVE")):
            other.status = "ARCHIVED"
            record(db, cu, "model.status", "model", f"{other.model_key}-{other.version}",
                   old={"status": "ACTIVE"}, new={"status": "ARCHIVED"})
    m.status = body.status
    record(db, cu, "model.status", "model", f"{m.model_key}-{m.version}", old={"status": old},
           new={"status": body.status})
    db.commit()
    return ok(model_payload(m))


@router.get("/monitoring")
def monitoring(cu: CurrentUser = Depends(require("models.read")), db: Session = Depends(get_db)):
    active = db.scalar(select(ModelRegistry).where(ModelRegistry.status == "ACTIVE",
                                                   ModelRegistry.model_key == "rasad-risk"))
    cfg = db.get(AppSetting, "drift_thresholds")
    limits = cfg.value if cfg else {"psi": 0.2, "rejection_rate": 0.35, "confidence_drop": 0.1}
    series = list((active.drift or {}).get("series", [])) if active else []

    # Ekspert rad etish darajasi oylar bo'yicha.
    by_month: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for d, created in db.execute(select(ExpertDecision.decision, ExpertDecision.created_at)):
        key = created.strftime("%Y-%m")
        by_month[key][1] += 1
        by_month[key][0] += int(d == "rejected")
    rejection = [{"month": k, "rejected": v[0], "total": v[1], "rate": round(v[0] / v[1], 3) if v[1] else None}
                 for k, v in sorted(by_month.items())]
    total_dec = sum(v[1] for v in by_month.values())
    current_rej = round(sum(v[0] for v in by_month.values()) / total_dec, 3) if total_dec else None

    warnings = []
    if series and series[-1]["psi"] > limits["psi"]:
        warnings.append({"code": "PSI", "message": "Natija taqsimoti siljigan (PSI chegaradan oshdi)."})
    if current_rej is not None and current_rej > limits["rejection_rate"]:
        warnings.append({"code": "REJECTION", "message": "Ekspert rad etish darajasi chegaradan oshdi."})
    if len(series) >= 2 and series[0]["mean_confidence"] - series[-1]["mean_confidence"] > limits["confidence_drop"]:
        warnings.append({"code": "CONFIDENCE", "message": "O‘rtacha ishonch darajasi sezilarli pasaydi."})
    return ok({
        "model": None if active is None else model_payload(active),
        "series": series,
        "rejection": rejection,
        "current": {
            "psi": series[-1]["psi"] if series else None,
            "rejection_rate": current_rej,
            "mean_confidence": series[-1]["mean_confidence"] if series else None,
            "anomalies": series[-1]["anomalies"] if series else None,
        },
        "limits": limits,
        "warnings": warnings,
        "status": "review_required" if warnings else "normal",
        "status_message": "Modelni qayta tekshirish talab etiladi." if warnings else "Model barqaror ishlamoqda.",
    })


# --- Audit -----------------------------------------------------------------


@router.get("/audit")
def audit(
    date_from: date | None = None,
    date_to: date | None = None,
    username: str | None = Query(None, max_length=64),
    action: str | None = Query(None, max_length=48),
    object_type: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    cu: CurrentUser = Depends(require("audit")),
    db: Session = Depends(get_db),
):
    conds = []
    if date_from:
        conds.append(AuditLog.at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conds.append(AuditLog.at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    if username:
        conds.append(AuditLog.username == username)
    if action:
        conds.append(AuditLog.action.like(f"{action}%"))
    if object_type:
        conds.append(AuditLog.object_type == object_type)
    q = select(AuditLog)
    if conds:
        q = q.where(and_(*conds))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(desc(AuditLog.at), desc(AuditLog.id)).offset((page - 1) * page_size).limit(page_size))
    return ok({
        "items": [{"id": r.id, "at": r.at.isoformat(), "username": r.username, "action": r.action,
                   "object_type": r.object_type, "object_id": r.object_id, "old_value": r.old_value,
                   "new_value": r.new_value, "ip": r.ip, "session_id": r.session_id} for r in rows],
        "total": total, "page": page, "page_size": page_size,
        "actions": sorted(a for (a,) in db.execute(select(AuditLog.action).distinct())),
        "users": sorted(u for (u,) in db.execute(select(AuditLog.username).distinct())),
    })


# --- Sozlamalar ------------------------------------------------------------


class ThresholdsIn(BaseModel):
    low: int = Field(ge=1, le=98)
    high: int = Field(ge=2, le=99)

    @model_validator(mode="after")
    def _order(self):
        if self.low >= self.high:
            raise ValueError("Past chegara yuqori chegaradan kichik bo‘lishi kerak")
        return self


@router.get("/settings")
def get_settings_all(cu: CurrentUser = Depends(require("settings")), db: Session = Depends(get_db)):
    low, high = get_thresholds(db)
    rows = {s.key: s for s in db.scalars(select(AppSetting))}
    th = rows.get("risk_thresholds")
    return ok({
        "risk_thresholds": {"low": low, "high": high, "updated_at": th.updated_at.isoformat() if th else None,
                            "updated_by": th.updated_by if th else None,
                            "note": "MVP uchun shartli chegaralar. Ilmiy asoslangan kalibrlash Pilot bosqichida o‘tkaziladi."},
        "drift_thresholds": rows["drift_thresholds"].value if "drift_thresholds" in rows else None,
        "retention_policy": rows["retention_policy"].value if "retention_policy" in rows else [],
        "can_edit": cu.can("settings.write"),
    })


@router.put("/settings/thresholds")
def set_thresholds(body: ThresholdsIn, cu: CurrentUser = Depends(require("settings.write")),
                   db: Session = Depends(get_db)):
    row = db.get(AppSetting, "risk_thresholds")
    old = dict(row.value) if row else None
    new = {"low": body.low, "high": body.high}
    if row is None:
        row = AppSetting(key="risk_thresholds", value=new)
        db.add(row)
    else:
        row.value = new
    row.updated_at, row.updated_by = datetime.now(timezone.utc), cu.user.username
    record(db, cu, "settings.thresholds", "settings", "risk_thresholds", old=old, new=new)
    db.commit()
    return ok(new)


# --- Foydalanuvchilar ------------------------------------------------------


def user_row(db: Session, u: User) -> dict:
    region = db.get(Region, u.region_id) if u.region_id else None
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "role_label": ROLE_LABELS.get(u.role, u.role), "region_id": u.region_id,
            "region_name": region.name if region else None, "is_active": u.is_active,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}


@router.get("/users")
def list_users(cu: CurrentUser = Depends(require("users")), db: Session = Depends(get_db)):
    return ok([user_row(db, u) for u in db.scalars(select(User).order_by(User.id))])


class UserPatch(BaseModel):
    role: Literal["admin", "analyst", "manager", "auditor"] | None = None
    region_id: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, cu: CurrentUser = Depends(require("users")),
                db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise NotFound("Foydalanuvchi topilmadi")
    if u.id == cu.id and (body.is_active is False or (body.role and body.role != "admin")):
        raise AppError(ErrorCode.DATA_VALIDATION, "O‘z hisobingiz rolini yoki faolligini o‘zgartira olmaysiz")
    old = user_row(db, u)
    if body.role:
        u.role = body.role
    if body.region_id is not None:
        if body.region_id and db.get(Region, body.region_id) is None:
            raise AppError(ErrorCode.DATA_VALIDATION, "Hudud topilmadi")
        u.region_id = body.region_id or None
    if body.is_active is not None:
        u.is_active = body.is_active
    new = user_row(db, u)
    record(db, cu, "user.update", "user", u.username,
           old={k: old[k] for k in ("role", "region_id", "is_active")},
           new={k: new[k] for k in ("role", "region_id", "is_active")})
    db.commit()
    return ok(new)
