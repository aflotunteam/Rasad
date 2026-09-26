"""SI xizmati holati va ulanish sinovi."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.explainer import PROMPT_VERSION
from app.audit.service import record
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.responses import ok
from app.models import AiExplanation, Subject

router = APIRouter(prefix="/ai", tags=["Sun'iy intellekt"])


@router.get("/status")
def status(cu: CurrentUser = Depends(require("settings")), db: Session = Depends(get_db)):
    s = get_settings()
    st = ai_client.state
    by_status = dict(db.execute(select(AiExplanation.status, func.count()).group_by(AiExplanation.status)).all())
    tokens = db.execute(select(func.coalesce(func.sum(AiExplanation.input_tokens), 0),
                               func.coalesce(func.sum(AiExplanation.output_tokens), 0))).one()
    recent = db.execute(
        select(AiExplanation, Subject.code).join(Subject, Subject.id == AiExplanation.subject_id)
        .order_by(desc(AiExplanation.created_at)).limit(10)
    ).all()
    lat = st.recent_latency_ms
    return ok({
        "enabled": s.ai_enabled,
        "configured": ai_client.is_configured(),
        "model": s.ai_model,
        "model_label": ai_client.model_label(),
        "effort": s.ai_effort,
        "timeout_seconds": s.ai_timeout_seconds,
        "prompt_version": PROMPT_VERSION,
        "mode": "ai" if ai_client.is_configured() else "template",
        "session": {
            "calls": st.calls, "ok": st.ok, "rejected": st.rejected, "errors": st.errors,
            "last_ok_at": st.last_ok_at.isoformat() if st.last_ok_at else None,
            "last_error": st.last_error,
            "last_error_at": st.last_error_at.isoformat() if st.last_error_at else None,
            "avg_latency_ms": int(sum(lat) / len(lat)) if lat else None,
        },
        "totals": {
            "ok": by_status.get("ok", 0), "rejected": by_status.get("rejected", 0), "error": by_status.get("error", 0),
            "input_tokens": int(tokens[0]), "output_tokens": int(tokens[1]),
        },
        "recent": [
            {"subject_code": code, "status": r.status, "model": r.model, "reason": r.rejection_reason,
             "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "latency_ms": r.latency_ms,
             "created_at": r.created_at.isoformat()}
            for r, code in recent
        ],
    })


@router.post("/test")
def test_connection(cu: CurrentUser = Depends(require("settings.write")), db: Session = Depends(get_db)):
    result = ai_client.check_connection()
    record(db, cu, "ai.test", "ai", get_settings().ai_model, new={"ok": result["ok"], "message": result["message"]})
    db.commit()
    return ok(result)
