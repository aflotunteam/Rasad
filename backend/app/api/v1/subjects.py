import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.responses import ok
from app.ai import explainer
from app.services import subjects as svc
from app.services.common import CONFIDENCE_LABELS, EXPERT_STATUS_LABELS, LEVEL_LABELS

router = APIRouter(prefix="/subjects", tags=["Subyektlar"])


def filters(
    region: str | None = Query(None, max_length=8),
    sector: str | None = Query(None, max_length=16),
    level: Literal["high", "medium", "low", "attention"] | None = None,
    risk_type: str | None = Query(None, pattern=r"^R0[1-8]$"),
    expert_status: str | None = Query(None, max_length=24),
    dq: Literal["low", "medium", "high"] | None = None,
    confidence: Literal["high", "medium", "low"] | None = None,
    q: str | None = Query(None, max_length=32),
    sort: str = Query("score", max_length=16),
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> svc.SubjectFilters:
    return svc.SubjectFilters(region, sector, level, risk_type, expert_status, dq, confidence, q, sort, order,
                              page, page_size)


@router.get("")
def list_subjects(f: svc.SubjectFilters = Depends(filters), cu: CurrentUser = Depends(require("subjects")),
                  db: Session = Depends(get_db)):
    return ok(svc.list_subjects(db, f, cu))


@router.get("/export.csv")
def export_subjects(f: svc.SubjectFilters = Depends(filters), cu: CurrentUser = Depends(require("subjects")),
                    db: Session = Depends(get_db)):
    rows = svc.export_rows(db, f, cu)
    buf = io.StringIO()
    buf.write("﻿")  # Excel uchun UTF-8 BOM
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Ichki kod", "Hudud", "Faoliyat turi", "Xavf bahosi", "Daraja", "Ishonch", "Asosiy xavf turi",
                "Ma’lumot sifati", "Ekspert holati", "Oxirgi tahlil"])
    for r in rows:
        w.writerow([r["code"], r["region_id"], r["sector_id"], f"{r['score']:.1f}".replace(".", ","),
                    LEVEL_LABELS[r["level"]], CONFIDENCE_LABELS[r["confidence"]], r["primary_risk_type"],
                    f"{r['dq_score']:.1f}".replace(".", ","), EXPERT_STATUS_LABELS.get(r["expert_status"], ""),
                    r["computed_at"][:10]])
    buf.write("\nNAMOYISH MA’LUMOTLARI — SINTETIK\n")
    record(db, cu, "subjects.export", "subjects", None, new={"rows": len(rows), "format": "csv"})
    db.commit()
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="rasad_subyektlar.csv"'})


@router.get("/{code}")
def get_subject(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    data = svc.subject_detail(db, code, cu)
    record(db, cu, "subject.view", "subject", data["code"])
    db.commit()
    return ok(data)


@router.get("/{code}/risk")
def get_risk(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    d = svc.subject_detail(db, code, cu)
    return ok(d["risk"])


@router.get("/{code}/factors")
def get_factors(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    d = svc.subject_detail(db, code, cu)
    return ok({"score": d["risk"]["score"], "factors": d["factors"]})


@router.get("/{code}/timeseries")
def get_timeseries(code: str, metric: Literal["turnover", "tx_count", "avg_check", "tax_index"] = "turnover",
                   cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    return ok(svc.timeseries(db, code, cu, metric))


@router.get("/{code}/peers")
def get_peers(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    return ok(svc.peers(db, code, cu))


@router.get("/{code}/relations")
def get_relations(code: str, depth: int = Query(2, ge=1, le=2), max_nodes: int = Query(40, ge=5, le=80),
                  cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    return ok(svc.relations(db, code, cu, depth, max_nodes))


def _ai_explanation(db: Session, code: str, cu: CurrentUser, force: bool) -> dict:
    subj = svc._get_subject(db, code, cu)
    d = svc.subject_detail(db, code, cu)
    data = explainer.explain_subject(db, subj.id, d["code"], d["region"]["name"], d["sector"]["name"], d["risk"],
                                     d["factors"], user_id=cu.id, force=force)
    if data["source"] == "ai" or force:
        record(db, cu, "ai.explanation", "subject", d["code"],
               new={"source": data["source"], "model": data["model"], "forced": force,
                    "fallback": data["fallback_code"]})
        db.commit()
    return data


@router.get("/{code}/explanation")
def get_explanation(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    return ok(_ai_explanation(db, code, cu, force=False))


@router.post("/{code}/explanation/regenerate")
def regenerate_explanation(code: str, cu: CurrentUser = Depends(require("decisions.write")),
                           db: Session = Depends(get_db)):
    return ok(_ai_explanation(db, code, cu, force=True))


@router.get("/{code}/decisions")
def get_decisions(code: str, cu: CurrentUser = Depends(require("subjects")), db: Session = Depends(get_db)):
    return ok(svc.decisions(db, code, cu))
