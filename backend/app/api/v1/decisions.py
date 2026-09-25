from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.responses import ok
from app.models import Alert, ExpertDecision, RiskScore
from app.services import subjects as svc

router = APIRouter(prefix="/expert-decisions", tags=["Ekspert qarorlari"])

# Ekspert qarori ogohlantirish holatini ham yangilaydi.
ALERT_STATUS_BY_DECISION = {
    "confirmed": "confirmed",
    "rejected": "rejected",
    "need_info": "in_review",
    "sent_review": "in_review",
}


class DecisionIn(BaseModel):
    subject_code: str = Field(min_length=3, max_length=16)
    decision: Literal["confirmed", "rejected", "need_info", "sent_review"]
    comment: str = Field(min_length=10, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Izoh kamida 10 belgidan iborat bo‘lishi kerak")
        return v


@router.post("")
def create_decision(body: DecisionIn, cu: CurrentUser = Depends(require("decisions.write")),
                    db: Session = Depends(get_db)):
    subj = svc._get_subject(db, body.subject_code, cu)
    rs = db.scalar(select(RiskScore).where(RiskScore.subject_id == subj.id))
    alert = db.scalar(select(Alert).where(Alert.subject_id == subj.id).order_by(desc(Alert.detected_at)))
    decision = ExpertDecision(subject_id=subj.id, alert_id=alert.id if alert else None, user_id=cu.id,
                              decision=body.decision, comment=body.comment, score_at_decision=rs.score,
                              model_version=rs.model_version)
    db.add(decision)
    old_status = rs.expert_status
    rs.expert_status = body.decision
    if alert:
        alert.status = ALERT_STATUS_BY_DECISION[body.decision]
        alert.analyst_id = alert.analyst_id or cu.id
        alert.updated_at = datetime.now(timezone.utc)
    db.flush()
    record(db, cu, "decision.create", "subject", subj.code,
           old={"expert_status": old_status},
           new={"decision": body.decision, "comment": body.comment, "score": rs.score,
                "model_version": rs.model_version})
    db.commit()
    db.refresh(decision)
    return ok(svc.decision_payload(decision))


@router.get("")
def list_decisions(limit: int = 50, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    q = select(ExpertDecision).order_by(desc(ExpertDecision.created_at)).limit(min(limit, 200))
    rows = db.scalars(q).all()
    out = []
    for d in rows:
        if cu.region_scope and d.subject_id and svc_region(db, d.subject_id) != cu.region_scope:
            continue
        out.append(svc.decision_payload(d) | {"subject_id": d.subject_id})
    return ok(out)


def svc_region(db: Session, subject_id: int) -> str | None:
    from app.models import Subject

    s = db.get(Subject, subject_id)
    return s.region_id if s else None
