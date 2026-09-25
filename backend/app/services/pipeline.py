"""Tahlil zanjiri: DB dagi xom ma'lumot → sifat → belgilar → modellar → xavf → sabablar.

Natijalar risk_scores va risk_factors jadvallariga yoziladi. Zanjir seed skriptida
ham, "qayta hisoblash" fon vazifasida ham bir xil ishlaydi.
"""

from __future__ import annotations

import calendar
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    DataLineage,
    FeatureRegistry,
    MonthlyMetric,
    Relation,
    RiskFactor,
    RiskScore,
    Subject,
)
from app.services.data_quality import assess_subjects
from data_gen.generate import month_starts
from ml.explainability.factors import factors_for, peer_ranges
from ml.features.build import FEATURE_DEFS, FEATURE_VERSION, build_features
from ml.inference import engine

PIPELINE_VERSION = "pipeline-1.0.0"


@dataclass
class PipelineOutput:
    subjects: pd.DataFrame
    metrics: pd.DataFrame
    relations: pd.DataFrame
    dq: pd.DataFrame
    feats: pd.DataFrame
    result: engine.EngineResult
    periods: list[date]
    elapsed: float


def data_version(period_end: date) -> str:
    return f"synthetic-{period_end:%Y.%m}-v1"


def load_frames(db: Session) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bind = db.connection()  # joriy tranzaksiya ichidagi (hali commit qilinmagan) yozuvlar ham ko'rinadi
    subjects = pd.read_sql(select(Subject.id, Subject.region_id, Subject.sector_id, Subject.size_group,
                                  Subject.stir, Subject.org_form, Subject.history_months,
                                  Subject.source_count, Subject.duplicate_records), bind)
    metrics = pd.read_sql(select(MonthlyMetric.subject_id, MonthlyMetric.period, MonthlyMetric.turnover,
                                 MonthlyMetric.tx_count, MonthlyMetric.avg_check, MonthlyMetric.tax_index,
                                 MonthlyMetric.registry_turnover), bind)
    metrics["period"] = pd.to_datetime(metrics["period"]).dt.date
    relations = pd.read_sql(select(Relation.source_id, Relation.target_id, Relation.rel_type, Relation.weight), bind)
    return subjects, metrics, relations


def compute(subjects: pd.DataFrame, metrics: pd.DataFrame, relations: pd.DataFrame,
            period_end: date | None = None) -> PipelineOutput:
    t0 = time.perf_counter()
    s = get_settings()
    period_end = period_end or date.fromisoformat(s.data_period_end)
    periods = month_starts(period_end, s.history_months)
    lag = (date.fromisoformat(s.data_period_end).year - period_end.year) * 12 + (
        date.fromisoformat(s.data_period_end).month - period_end.month)
    if lag > 0:
        # Tarixiy kesim: oxirgi `lag` oy hali mavjud bo'lmagan deb hisoblanadi.
        metrics = metrics[metrics["period"] <= period_end]
        subjects = subjects.assign(history_months=(subjects["history_months"] - lag).clip(lower=1,
                                                                                         upper=s.history_months - lag))
    dq = assess_subjects(subjects, metrics, period_end)
    feats = build_features(subjects, metrics, periods)
    result = engine.run(feats, relations, dq, subjects, seed=s.seed)
    return PipelineOutput(subjects, metrics, relations, dq, feats, result, periods, time.perf_counter() - t0)


def persist(db: Session, out: PipelineOutput) -> int:
    periods = out.periods
    p_end = periods[-1]
    period_end = date(p_end.year, p_end.month, calendar.monthrange(p_end.year, p_end.month)[1])
    now = datetime.now(timezone.utc)
    version = f"{engine.MODEL_KEY}-{engine.MODEL_VERSION}"
    dver = data_version(p_end)

    # Mavjud ekspert holatini saqlab qolamiz (qayta hisoblash qarorlarni o'chirmasligi kerak).
    prev_status = dict(db.execute(select(RiskScore.subject_id, RiskScore.expert_status)).all())
    db.execute(delete(RiskFactor))
    db.execute(delete(RiskScore))

    sc = out.result.scores
    dq_dims = out.dq.drop(columns=["dq_score"]).to_dict(orient="index")
    components = out.result.contributions.round(2).to_dict(orient="index")
    fcols = ["turnover_change_3m", "transaction_count_ratio", "avg_check_ratio", "tax_index_6m",
             "source_conflict_ratio", "seasonality_deviation", "last3_turnover"]
    fdf = out.feats[fcols].copy()
    fdf["risky_neighbors"] = out.result.network["risky_neighbors"]
    fdf["degree"] = out.result.network["degree"]
    fdf = fdf.round(4).astype(object).where(fdf.notna(), None)
    features = fdf.to_dict(orient="index")
    rows = []
    for sid, r in sc.iterrows():
        rows.append({
            "subject_id": int(sid),
            "score": float(r.score),
            "confidence": str(r.confidence),
            "confidence_value": float(r.confidence_value),
            "dq_score": float(r.dq_score),
            "dq_dimensions": dq_dims.get(sid, {}),
            "primary_risk_type": str(r.primary_risk_type),
            "risk_types": list(r.risk_types),
            "components": components.get(sid, {}),
            "features": features.get(sid, {}),
            "anomaly_score": float(r.anomaly_score),
            "expert_status": prev_status.get(int(sid), "pending"),
            "model_version": version,
            "data_version": dver,
            "period_start": periods[0],
            "period_end": period_end,
            "computed_at": now,
        })
    db.execute(insert(RiskScore), rows)
    id_map = dict(db.execute(select(RiskScore.subject_id, RiskScore.id)).all())

    ranges = peer_ranges(out.feats, out.result.network, out.result.scores["anomaly_score"])
    frows = []
    for sid in sc.index:
        for f in factors_for(sid, out.feats, out.result.signals, out.result.contributions, out.result.network,
                             out.result.scores["anomaly_score"], ranges)[:8]:
            f["risk_score_id"] = id_map[int(sid)]
            frows.append(f)
    db.execute(insert(RiskFactor), frows)

    db.add(DataLineage(source_id=None, target_table="risk_scores", transformation="risk_engine.run",
                       pipeline_version=PIPELINE_VERSION, source_record_id=dver,
                       target_record_id=f"{len(rows)} ta yozuv"))
    return len(rows)


def register_features(db: Session) -> None:
    db.execute(delete(FeatureRegistry))
    db.execute(insert(FeatureRegistry), [
        {"feature_name": n, "description": d, "source": src, "formula": f, "version": FEATURE_VERSION,
         "status": "active"} for n, d, src, f in FEATURE_DEFS
    ])


def recompute(db: Session) -> dict:
    subjects, metrics, relations = load_frames(db)
    out = compute(subjects, metrics, relations)
    n = persist(db, out)
    db.commit()
    return {"subjects": n, "elapsed_sec": round(out.elapsed, 2)}
