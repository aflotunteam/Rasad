"""Hisobot mazmunini tayyorlash (TZ §37: har bir hisobotda metadata bo'lishi shart)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.errors import AppError, ErrorCode, Forbidden
from app.models import Region, Report, RiskScore, Sector
from app.services import explain
from app.services import subjects as svc
from app.services.analytics import scores_frame
from app.services.common import EXPERT_STATUS_LABELS, LEVEL_LABELS, get_thresholds, level_for
from data_gen.reference import RISK_TYPES

REPORT_TYPES = {
    "subject": "Subyekt hisoboti",
    "region": "Hududiy hisobot",
    "sector": "Tarmoq hisoboti",
    "risk_type": "Xavf turi hisoboti",
    "periodic": "Davriy hisobot",
}
RISK_TYPE_NAMES = {c: n for c, n, _, _ in RISK_TYPES}


def next_number(db: Session, year: int) -> str:
    n = db.scalar(select(func.count()).select_from(Report)) or 0
    return f"RPT-{year}-{n + 1:06d}"


def validate_params(db: Session, report_type: str, params: dict, cu: CurrentUser) -> tuple[str, dict]:
    if report_type not in REPORT_TYPES:
        raise AppError(ErrorCode.REPORT_FAILED, "Hisobot turi noma’lum")
    if report_type == "subject":
        subj = svc._get_subject(db, str(params.get("code", "")), cu)
        return f"{REPORT_TYPES[report_type]}: {subj.code}", {"code": subj.code}
    if report_type == "region":
        region = db.get(Region, str(params.get("region", "")))
        if region is None:
            raise AppError(ErrorCode.REPORT_FAILED, "Hudud ko‘rsatilmagan")
        if cu.region_scope and region.id != cu.region_scope:
            raise Forbidden("Bu hudud bo‘yicha hisobot yaratishga ruxsat yo‘q")
        return f"{REPORT_TYPES[report_type]}: {region.name}", {"region": region.id}
    if report_type == "sector":
        sector = db.get(Sector, str(params.get("sector", "")))
        if sector is None:
            raise AppError(ErrorCode.REPORT_FAILED, "Soha ko‘rsatilmagan")
        return f"{REPORT_TYPES[report_type]}: {sector.name}", {"sector": sector.id}
    if report_type == "risk_type":
        code = str(params.get("risk_type", ""))
        if code not in RISK_TYPE_NAMES:
            raise AppError(ErrorCode.REPORT_FAILED, "Xavf turi ko‘rsatilmagan")
        return f"{REPORT_TYPES[report_type]}: {code} — {RISK_TYPE_NAMES[code]}", {"risk_type": code}
    return REPORT_TYPES["periodic"], {}


def metadata(report: Report) -> dict:
    return {
        "number": report.number,
        "type": report.report_type,
        "type_label": REPORT_TYPES[report.report_type],
        "title": report.title,
        "created_at": report.created_at.isoformat(),
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "model_version": report.model_version,
        "data_version": report.data_version,
        "created_by": report.author.full_name,
        "synthetic": True,
        "disclaimer": explain.DISCLAIMER,
    }


def build_content(db: Session, report: Report, cu: CurrentUser) -> dict:
    low, high = get_thresholds(db)
    p = report.params
    if report.report_type == "subject":
        d = svc.subject_detail(db, p["code"], cu)
        rel = svc.relations(db, p["code"], cu, depth=1)
        return {
            "kind": "subject",
            "subject": {k: d[k] for k in ("code", "region", "sector", "size_group", "stir", "registered_at",
                                          "source_count", "history_months")},
            "risk": d["risk"],
            "factors": d["factors"],
            "explanation": explain.build(d["code"], d["risk"], d["factors"]),
            "decisions": svc.decisions(db, p["code"], cu),
            "relations": rel["summary"],
        }

    df = scores_frame(db, cu.region_scope)
    if report.report_type == "region":
        df = df[df.region_id == p["region"]]
    elif report.report_type == "sector":
        df = df[df.sector_id == p["sector"]]
    elif report.report_type == "risk_type":
        codes = dict(db.execute(select(RiskScore.subject_id, RiskScore.risk_types)).all())
        mask = df.primary_risk_type.eq(p["risk_type"]) | df.id.map(lambda i: p["risk_type"] in (codes.get(i) or []))
        df = df[mask]

    regions = {r.id: r.name for r in db.scalars(select(Region))}
    sectors = {s.id: s.name for s in db.scalars(select(Sector))}
    top = df.sort_values("score", ascending=False).head(20)
    return {
        "kind": "aggregate",
        "summary": {
            "subjects": int(len(df)),
            "high": int((df.score >= high).sum()),
            "medium": int(((df.score >= low) & (df.score < high)).sum()),
            "avg_dq": round(float(df.dq_score.mean()), 1) if len(df) else None,
            "low_dq": int((df.dq_score < 60).sum()),
            "thresholds": {"low": low, "high": high},
        },
        "by_region": [
            {"id": k, "name": regions.get(k, k), "subjects": int(len(g)), "high": int((g.score >= high).sum()),
             "medium": int(((g.score >= low) & (g.score < high)).sum())}
            for k, g in df.groupby("region_id")
        ],
        "by_sector": [
            {"id": k, "name": sectors.get(k, k), "subjects": int(len(g)), "high": int((g.score >= high).sum()),
             "medium": int(((g.score >= low) & (g.score < high)).sum())}
            for k, g in df.groupby("sector_id")
        ],
        "by_risk_type": [
            {"code": k, "name": RISK_TYPE_NAMES.get(k, k), "count": int(len(g))}
            for k, g in df[df.score >= low].groupby("primary_risk_type")
        ],
        "top": [
            {"code": r.code, "region": regions.get(r.region_id, r.region_id),
             "sector": sectors.get(r.sector_id, r.sector_id), "score": float(r.score),
             "level": LEVEL_LABELS[level_for(r.score, low, high)], "confidence": LEVEL_LABELS[r.confidence],
             "risk_type": r.primary_risk_type, "dq_score": float(r.dq_score),
             "expert_status": EXPERT_STATUS_LABELS.get(r.expert_status, r.expert_status)}
            for r in top.itertuples()
        ],
    }
