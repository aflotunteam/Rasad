"""Subyektlar: ro'yxat, karta, vaqt qatori, o'xshashlar bilan taqqoslash, aloqadorliklar."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import String, and_, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser
from app.core.errors import ErrorCode, Forbidden, NotFound
from app.models import Alert, ExpertDecision, MonthlyMetric, Relation, RiskScore, Subject
from app.services.common import get_thresholds, level_for, mask_stir
from data_gen.reference import RELATION_TYPES

SORT_FIELDS = {
    "score": RiskScore.score,
    "confidence": RiskScore.confidence_value,
    "dq_score": RiskScore.dq_score,
    "code": Subject.code,
    "computed_at": RiskScore.computed_at,
    "region": Subject.region_id,
    "sector": Subject.sector_id,
}

METRIC_LABELS = {
    "turnover": ("Aylanma", "mln so‘m"),
    "tx_count": ("Operatsiyalar soni", "ta"),
    "avg_check": ("O‘rtacha chek", "ming so‘m"),
    "tax_index": ("Soliq yuklamasi indeksi", "indeks"),
}


@dataclass
class SubjectFilters:
    region: str | None = None
    sector: str | None = None
    level: str | None = None
    risk_type: str | None = None
    expert_status: str | None = None
    dq: str | None = None  # low | medium | high
    confidence: str | None = None
    q: str | None = None
    sort: str = "score"
    order: str = "desc"
    page: int = 1
    page_size: int = 25


def _get_subject(db: Session, code: str, cu: CurrentUser) -> Subject:
    subj = db.scalar(
        select(Subject).options(joinedload(Subject.region), joinedload(Subject.sector))
        .where(Subject.code == code.upper())
    )
    if subj is None:
        raise NotFound("Subyekt topilmadi", ErrorCode.SUBJECT_NOT_FOUND)
    if cu.region_scope and subj.region_id != cu.region_scope:
        raise Forbidden("Bu subyekt sizga biriktirilgan hududga tegishli emas")
    return subj


def _risk(db: Session, subject_id: int) -> RiskScore:
    rs = db.scalar(select(RiskScore).options(joinedload(RiskScore.factors)).where(RiskScore.subject_id == subject_id))
    if rs is None:
        raise NotFound("Xavf bahosi hali hisoblanmagan", ErrorCode.RISK_UNAVAILABLE)
    return rs


def _filtered_query(db: Session, f: SubjectFilters, cu: CurrentUser):
    low, high = get_thresholds(db)
    q = select(Subject, RiskScore).join(RiskScore, RiskScore.subject_id == Subject.id)
    conds = []
    region = cu.region_scope or f.region
    if region:
        conds.append(Subject.region_id == region)
    if f.sector:
        conds.append(Subject.sector_id == f.sector)
    if f.level == "high":
        conds.append(RiskScore.score >= high)
    elif f.level == "medium":
        conds.append(and_(RiskScore.score >= low, RiskScore.score < high))
    elif f.level == "low":
        conds.append(RiskScore.score < low)
    elif f.level == "attention":
        conds.append(RiskScore.score >= low)
    if f.risk_type:
        conds.append(or_(RiskScore.primary_risk_type == f.risk_type,
                         cast(RiskScore.risk_types, String).like(f'%"{f.risk_type}"%')))
    if f.expert_status:
        conds.append(RiskScore.expert_status == f.expert_status)
    if f.confidence:
        conds.append(RiskScore.confidence == f.confidence)
    if f.dq == "low":
        conds.append(RiskScore.dq_score < 60)
    elif f.dq == "medium":
        conds.append(and_(RiskScore.dq_score >= 60, RiskScore.dq_score < 80))
    elif f.dq == "high":
        conds.append(RiskScore.dq_score >= 80)
    if f.q:
        term = f.q.strip().upper()
        if term.isdigit():
            term = f"SUB-{int(term):06d}"
        conds.append(Subject.code.like(f"%{term}%"))
    if conds:
        q = q.where(and_(*conds))
    return q, low, high


def subject_row(subj: Subject, rs: RiskScore, low: float, high: float, can_stir: bool) -> dict:
    return {
        "code": subj.code,
        "region_id": subj.region_id,
        "sector_id": subj.sector_id,
        "size_group": subj.size_group,
        "stir": mask_stir(subj.stir, can_stir),
        "score": rs.score,
        "level": level_for(rs.score, low, high),
        "confidence": rs.confidence,
        "confidence_value": rs.confidence_value,
        "primary_risk_type": rs.primary_risk_type,
        "risk_types": rs.risk_types,
        "dq_score": rs.dq_score,
        "expert_status": rs.expert_status,
        "computed_at": rs.computed_at.isoformat(),
    }


def list_subjects(db: Session, f: SubjectFilters, cu: CurrentUser) -> dict:
    q, low, high = _filtered_query(db, f, cu)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    col = SORT_FIELDS.get(f.sort, RiskScore.score)
    q = q.order_by(desc(col) if f.order == "desc" else asc(col), Subject.code)
    rows = db.execute(q.offset((f.page - 1) * f.page_size).limit(f.page_size)).all()
    can_stir = cu.can("subjects.stir")
    return {
        "items": [subject_row(s, r, low, high, can_stir) for s, r in rows],
        "total": total,
        "page": f.page,
        "page_size": f.page_size,
    }


def export_rows(db: Session, f: SubjectFilters, cu: CurrentUser, limit: int = 10000) -> list[dict]:
    q, low, high = _filtered_query(db, f, cu)
    col = SORT_FIELDS.get(f.sort, RiskScore.score)
    q = q.order_by(desc(col) if f.order == "desc" else asc(col)).limit(limit)
    can_stir = cu.can("subjects.stir")
    return [subject_row(s, r, low, high, can_stir) for s, r in db.execute(q).all()]


def risk_payload(rs: RiskScore, low: float, high: float) -> dict:
    return {
        "score": rs.score,
        "level": level_for(rs.score, low, high),
        "confidence": rs.confidence,
        "confidence_value": rs.confidence_value,
        "dq_score": rs.dq_score,
        "dq_dimensions": rs.dq_dimensions,
        "primary_risk_type": rs.primary_risk_type,
        "risk_types": rs.risk_types,
        "components": rs.components,
        "anomaly_score": rs.anomaly_score,
        "expert_status": rs.expert_status,
        "model_version": rs.model_version,
        "data_version": rs.data_version,
        "period_start": rs.period_start.isoformat(),
        "period_end": rs.period_end.isoformat(),
        "computed_at": rs.computed_at.isoformat(),
        "thresholds": {"low": low, "high": high},
    }


def factor_payload(f) -> dict:
    return {
        "rank": f.rank, "feature": f.feature, "factor": f.factor, "risk_type": f.risk_type,
        "current_value": f.current_value, "baseline_low": f.baseline_low, "baseline_high": f.baseline_high,
        "unit": f.unit, "deviation": f.deviation, "impact": f.impact, "source": f.source,
    }


def subject_detail(db: Session, code: str, cu: CurrentUser) -> dict:
    subj = _get_subject(db, code, cu)
    rs = _risk(db, subj.id)
    low, high = get_thresholds(db)
    alert = db.scalar(select(Alert).where(Alert.subject_id == subj.id).order_by(desc(Alert.detected_at)))
    return {
        "code": subj.code,
        "region": {"id": subj.region.id, "name": subj.region.name},
        "sector": {"id": subj.sector.id, "name": subj.sector.name},
        "size_group": subj.size_group,
        "org_form": subj.org_form,
        "stir": mask_stir(subj.stir, cu.can("subjects.stir")),
        "stir_masked": not cu.can("subjects.stir"),
        "registered_at": subj.registered_at.isoformat(),
        "source_count": subj.source_count,
        "history_months": subj.history_months,
        "duplicate_records": subj.duplicate_records,
        "is_synthetic": subj.is_synthetic,
        "risk": risk_payload(rs, low, high),
        "factors": [factor_payload(f) for f in rs.factors],
        "alert": None if alert is None else {
            "code": alert.code, "status": alert.status, "severity": alert.severity,
            "detected_at": alert.detected_at.isoformat(), "analyst_id": alert.analyst_id,
        },
    }


# --- Kesh: soha bo'yicha taqsimotlar (ma'lumot versiyasi o'zgarsa yangilanadi) ------

_cache: dict[tuple, Any] = {}
_cache_lock = threading.Lock()


def _cache_key(db: Session, *parts) -> tuple:
    version = db.scalar(select(func.max(RiskScore.computed_at)))
    return (str(version), *parts)


def _cached(key: tuple, fn):
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    value = fn()
    with _cache_lock:
        if len(_cache) > 256:
            _cache.clear()
        _cache[key] = value
    return value


def _sector_matrix(db: Session, sector: str, size: str | None, metric: str) -> pd.DataFrame:
    q = (select(MonthlyMetric.subject_id, MonthlyMetric.period, getattr(MonthlyMetric, metric).label("v"))
         .join(Subject, Subject.id == MonthlyMetric.subject_id).where(Subject.sector_id == sector))
    if size:
        q = q.where(Subject.size_group == size)
    df = pd.read_sql(q, db.connection())
    df.loc[df["v"] <= 0, "v"] = np.nan
    return df.pivot(index="subject_id", columns="period", values="v")


def timeseries(db: Session, code: str, cu: CurrentUser, metric: str = "turnover") -> dict:
    if metric not in METRIC_LABELS:
        metric = "turnover"
    subj = _get_subject(db, code, cu)
    rows = db.execute(select(MonthlyMetric).where(MonthlyMetric.subject_id == subj.id)
                      .order_by(MonthlyMetric.period)).scalars().all()

    def peer_stats():
        mat = _sector_matrix(db, subj.sector_id, subj.size_group, metric)
        with np.errstate(all="ignore"):
            median = mat.median(axis=0)
            yoy = np.log(mat) - np.log(mat.shift(12, axis=1))
            q = yoy.quantile([0.1, 0.5, 0.9], axis=0)
        return median, q

    median, yoy_q = _cached(_cache_key(db, "ts", subj.sector_id, subj.size_group, metric), peer_stats)
    by_period = {r.period: r for r in rows}
    points = []
    for p in median.index:
        r = by_period.get(p)
        value = getattr(r, metric) if r else None
        if value is not None and value <= 0 and metric != "tax_index":
            value = None
        prev_period = p.replace(year=p.year - 1)
        prev = by_period.get(prev_period)
        prev_v = getattr(prev, metric) if prev else None
        exp = lo = hi = None
        if prev_v and prev_v > 0 and p in yoy_q.columns and not np.isnan(yoy_q.at[0.5, p]):
            exp = prev_v * float(np.exp(yoy_q.at[0.5, p]))
            lo = prev_v * float(np.exp(yoy_q.at[0.1, p]))
            hi = prev_v * float(np.exp(yoy_q.at[0.9, p]))
        deviation = None
        if value is not None and exp:
            deviation = round((value / exp - 1) * 100, 1)
        points.append({
            "period": p.isoformat(),
            "value": None if value is None else round(float(value), 2),
            "peer_median": None if np.isnan(median[p]) else round(float(median[p]), 2),
            "expected": None if exp is None else round(exp, 2),
            "expected_low": None if lo is None else round(lo, 2),
            "expected_high": None if hi is None else round(hi, 2),
            "deviation_pct": deviation,
            "outside": bool(value is not None and lo is not None and (value < lo or value > hi)),
            "registry": None if not r or r.registry_turnover is None or metric != "turnover"
            else round(float(r.registry_turnover), 2),
        })
    label, unit = METRIC_LABELS[metric]
    return {"metric": metric, "label": label, "unit": unit, "points": points,
            "peer_group": f"{subj.sector.name}, hajm guruhi bo‘yicha o‘xshash subyektlar",
            "source": "synthetic_demo_transactions_v1"}


def _features_frame(db: Session) -> pd.DataFrame:
    def load():
        rows = db.execute(select(Subject.id, Subject.region_id, Subject.sector_id, Subject.size_group,
                                 RiskScore.features).join(RiskScore, RiskScore.subject_id == Subject.id)).all()
        recs = []
        for sid, region, sector, size, feats in rows:
            recs.append({"id": sid, "region_id": region, "sector_id": sector, "size_group": size, **(feats or {})})
        return pd.DataFrame(recs).set_index("id")

    return _cached(_cache_key(db, "features"), load)


PEER_METRICS = [
    ("turnover_change_3m", "Aylanma o‘zgarishi (yillik)", "%", 100.0, 0.0),
    ("avg_check_ratio", "O‘rtacha chek o‘zgarishi", "%", 100.0, -100.0),
    ("tax_index_6m", "Soliq yuklamasi indeksi", "indeks", 1.0, 0.0),
    ("last3_turnover", "Oylik aylanma (oxirgi 3 oy)", "mln so‘m", 1.0, 0.0),
]


def peers(db: Session, code: str, cu: CurrentUser) -> dict:
    subj = _get_subject(db, code, cu)
    df = _features_frame(db)
    me = df.loc[subj.id]
    groups = [
        ("sector", f"Soha: {subj.sector.name}", df.sector_id == subj.sector_id),
        ("region", f"Hudud: {subj.region.name}", df.region_id == subj.region_id),
        ("size", "O‘xshash hajmdagi subyektlar (soha ichida)",
         (df.sector_id == subj.sector_id) & (df.size_group == subj.size_group)),
    ]
    out = []
    for key, label, unit, mult, offset in PEER_METRICS:
        value = me.get(key)
        rows = []
        for gkey, glabel, mask in groups:
            s = pd.to_numeric(df.loc[mask, key], errors="coerce").dropna()
            if s.empty or value is None or pd.isna(value):
                continue
            q = s.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
            conv = (lambda x: round(float(x) * mult + offset, 2))
            rows.append({
                "group": gkey, "label": glabel, "n": int(len(s)),
                "p10": conv(q[0.1]), "p25": conv(q[0.25]), "median": conv(q[0.5]),
                "p75": conv(q[0.75]), "p90": conv(q[0.9]),
                "percentile": round(float((s < value).mean() * 100), 1),
            })
        out.append({"metric": key, "label": label, "unit": unit,
                    "value": None if value is None or pd.isna(value) else round(float(value) * mult + offset, 2),
                    "groups": rows})
    return {"code": subj.code, "metrics": out}


STRUCTURAL = {"founder", "director", "address"}


def relations(db: Session, code: str, cu: CurrentUser, depth: int = 2, max_nodes: int = 40) -> dict:
    subj = _get_subject(db, code, cu)
    low, high = get_thresholds(db)

    def edges_of(ids: set[int]):
        return db.execute(select(Relation).where(or_(Relation.source_id.in_(ids), Relation.target_id.in_(ids)))).scalars().all()

    first = edges_of({subj.id})
    level1 = {e.target_id if e.source_id == subj.id else e.source_id for e in first}
    all_edges = {e.id: e for e in first}
    scores = dict(db.execute(select(RiskScore.subject_id, RiskScore.score)
                             .where(RiskScore.subject_id.in_(level1 | {subj.id}))).all())
    level2: set[int] = set()
    hidden: dict[int, int] = {}
    if depth >= 2 and level1:
        # Faqat xavfli qo'shnilar kengaytiriladi; periferiya yig'ilgan holda qoladi.
        risky1 = {n for n in level1 if scores.get(n, 0) >= low}
        second = edges_of(risky1) if risky1 else []
        cand = {}
        for e in second:
            a, b = e.source_id, e.target_id
            owner, other = (a, b) if a in risky1 else (b, a)
            if other == subj.id or other in level1:
                if other in level1 or other == subj.id:
                    all_edges[e.id] = e
                continue
            cand.setdefault(other, []).append((owner, e))
        if cand:
            scores.update(dict(db.execute(select(RiskScore.subject_id, RiskScore.score)
                                          .where(RiskScore.subject_id.in_(set(cand)))).all()))
        ranked = sorted(cand, key=lambda n: -scores.get(n, 0))
        budget = max(0, max_nodes - 1 - len(level1))
        for n in ranked:
            if scores.get(n, 0) >= low and len(level2) < budget:
                level2.add(n)
                for _, e in cand[n]:
                    all_edges[e.id] = e
            else:
                for owner, _ in cand[n]:
                    hidden[owner] = hidden.get(owner, 0) + 1

    ids = {subj.id} | level1 | level2
    info = {s.id: s for s in db.scalars(select(Subject).where(Subject.id.in_(ids)))}
    nodes = []
    for nid in ids:
        s = info[nid]
        restricted = bool(cu.region_scope and s.region_id != cu.region_scope)
        sc = scores.get(nid)
        nodes.append({
            "id": s.code,
            "region_id": s.region_id,
            "sector_id": s.sector_id,
            "score": None if restricted else sc,
            "level": None if restricted or sc is None else level_for(sc, low, high),
            "depth": 0 if nid == subj.id else (1 if nid in level1 else 2),
            "is_center": nid == subj.id,
            "restricted": restricted,
            "hidden_neighbors": hidden.get(nid, 0),
        })
    edges = []
    for e in all_edges.values():
        if e.source_id not in ids or e.target_id not in ids:
            continue
        a, b = scores.get(e.source_id, 0), scores.get(e.target_id, 0)
        edges.append({
            "source": info[e.source_id].code, "target": info[e.target_id].code,
            "type": e.rel_type, "label": RELATION_TYPES.get(e.rel_type, e.rel_type),
            "weight": e.weight, "structural": e.rel_type in STRUCTURAL,
            "risky_path": a >= low and b >= low,
        })
    return {
        "center": subj.code,
        "nodes": sorted(nodes, key=lambda n: (n["depth"], -(n["score"] or 0))),
        "edges": edges,
        "summary": {
            "direct": len(level1),
            "risky_direct": sum(1 for n in level1 if scores.get(n, 0) >= low),
            "second_level_shown": len(level2),
            "hidden": sum(hidden.values()),
        },
    }


def decisions(db: Session, code: str, cu: CurrentUser) -> list[dict]:
    subj = _get_subject(db, code, cu)
    rows = db.scalars(select(ExpertDecision).options(joinedload(ExpertDecision.user))
                      .where(ExpertDecision.subject_id == subj.id).order_by(desc(ExpertDecision.created_at)))
    return [decision_payload(d) for d in rows]


def decision_payload(d: ExpertDecision) -> dict:
    return {
        "id": d.id, "decision": d.decision, "comment": d.comment,
        "user": {"id": d.user.id, "full_name": d.user.full_name, "role": d.user.role},
        "created_at": d.created_at.isoformat(), "score_at_decision": d.score_at_decision,
        "model_version": d.model_version,
    }
