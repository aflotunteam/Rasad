"""Bosh sahifa va hududlar uchun agregatlar."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    ExpertDecision,
    FeatureRegistry,
    ModelRegistry,
    Region,
    RiskScore,
    Sector,
    Subject,
)
from app.services.common import get_thresholds, level_for


def scores_frame(db: Session, region: str | None = None) -> pd.DataFrame:
    q = select(Subject.id, Subject.code, Subject.region_id, Subject.sector_id, Subject.size_group,
               Subject.duplicate_records, RiskScore.score, RiskScore.confidence, RiskScore.confidence_value,
               RiskScore.dq_score, RiskScore.primary_risk_type, RiskScore.expert_status,
               RiskScore.computed_at).join(RiskScore, RiskScore.subject_id == Subject.id)
    if region:
        q = q.where(Subject.region_id == region)
    return pd.read_sql(q, db.connection())


def dashboard(db: Session, region: str | None, scope: str | None) -> dict:
    low, high = get_thresholds(db)
    effective = scope or region
    all_df = scores_frame(db)
    df = all_df if effective is None else all_df[all_df.region_id == effective]

    now = datetime.now(timezone.utc)
    alerts_q = select(Alert.region_id, Alert.status, Alert.detected_at)
    alerts = pd.read_sql(alerts_q, db.connection())
    alerts["detected_at"] = pd.to_datetime(alerts["detected_at"], utc=True)
    recent = alerts["detected_at"] >= now - timedelta(days=7)
    alerts_f = alerts if effective is None else alerts[alerts.region_id == effective]

    active = db.scalar(select(ModelRegistry).where(ModelRegistry.status == "ACTIVE"))
    last = df["computed_at"].max() if len(df) else None

    # Hududlar kesimi (xarita uchun). Tahlilchi boshqa hududlarni ko'rmaydi.
    regions = []
    for r in db.scalars(select(Region).order_by(Region.sort_order)):
        rdf = all_df[all_df.region_id == r.id]
        restricted = scope is not None and r.id != scope
        new_alerts = int(((alerts.region_id == r.id) & (alerts.status == "new")).sum())
        regions.append({
            "id": r.id, "name": r.name, "short_name": r.short_name, "geo_key": r.geo_key,
            "restricted": restricted,
            "subjects": None if restricted else int(len(rdf)),
            "high": None if restricted else int((rdf.score >= high).sum()),
            "medium": None if restricted else int(((rdf.score >= low) & (rdf.score < high)).sum()),
            "risk_index": None if restricted else round(float((rdf.score >= low).mean() * 100), 2),
            "avg_dq": None if restricted else round(float(rdf.dq_score.mean()), 1),
            "new_alerts": None if restricted else new_alerts,
            "updated_at": None if restricted or rdf.empty else pd.Timestamp(rdf.computed_at.max()).isoformat(),
        })

    sectors = {s.id: s.name for s in db.scalars(select(Sector))}
    by_sector = []
    for sid, g in df.groupby("sector_id"):
        by_sector.append({
            "id": sid, "name": sectors.get(sid, sid), "subjects": int(len(g)),
            "high": int((g.score >= high).sum()), "medium": int(((g.score >= low) & (g.score < high)).sum()),
            "share": round(float((g.score >= low).mean() * 100), 2),
        })
    by_sector.sort(key=lambda x: -x["share"])

    flagged = df[df.score >= low]
    by_type = flagged.groupby("primary_risk_type").size().sort_index()
    top = df.sort_values("score", ascending=False).head(10)

    trend = []
    if active and active.drift.get("series"):
        n = len(df)
        for p in active.drift["series"]:
            trend.append({"period": p["period"], "high_share": p["high_share"],
                          "high_est": int(round(p["high_share"] * n)), "mean_score": p["mean_score"]})

    hist, edges = np.histogram(df.score, bins=10, range=(0, 100))

    # Analitik zanjir bo'yicha hajmlar (prompt §9).
    decisions = db.scalar(select(func.count()).select_from(ExpertDecision))
    features = db.scalar(select(func.count()).select_from(FeatureRegistry))
    chain = [
        {"key": "quality", "label": "Ma’lumot sifati", "value": round(float(all_df.dq_score.mean()), 1), "unit": "/100"},
        {"key": "matching", "label": "Subyektni moslashtirish", "value": int(all_df.duplicate_records.sum()), "unit": "ta yozuv birlashtirildi"},
        {"key": "features", "label": "Tahliliy belgilar", "value": int(features or 0), "unit": "ta belgi"},
        {"key": "models", "label": "Modellar", "value": 4, "unit": "ta usul"},
        {"key": "calibration", "label": "Kalibrlash", "value": "0–100", "unit": "shkala"},
        {"key": "score", "label": "Xavf bahosi", "value": int(len(all_df)), "unit": "ta subyekt"},
        {"key": "confidence", "label": "Ishonch darajasi", "value": int((all_df.confidence == "high").sum()), "unit": "ta yuqori ishonch"},
        {"key": "factors", "label": "Sabablar", "value": int((all_df.score >= low).sum()), "unit": "ta izohlangan holat"},
        {"key": "expert", "label": "Ekspert qarori", "value": int(decisions or 0), "unit": "ta qaror"},
    ]

    return {
        "filter": {"region": effective, "scoped": scope is not None},
        "thresholds": {"low": low, "high": high},
        "kpis": {
            "analyzed": int(len(df)),
            "high_priority": int((df.score >= high).sum()),
            "medium_priority": int(((df.score >= low) & (df.score < high)).sum()),
            "new_alerts": int((alerts_f.status == "new").sum()),
            "new_alerts_7d": int(((alerts_f.status == "new") & recent.loc[alerts_f.index]).sum()),
            "avg_dq": round(float(df.dq_score.mean()), 1) if len(df) else None,
            "low_dq_subjects": int((df.dq_score < 60).sum()),
            "active_model": None if active is None else f"{active.name} v{active.version}",
            "last_update": None if last is None else pd.Timestamp(last).isoformat(),
        },
        "regions": regions,
        "sectors": by_sector,
        "risk_types": [{"code": k, "count": int(v)} for k, v in by_type.items()],
        "trend": trend,
        "distribution": [{"from": int(edges[i]), "to": int(edges[i + 1]), "count": int(hist[i])} for i in range(10)],
        "top_cases": [
            {"code": r.code, "region_id": r.region_id, "sector_id": r.sector_id, "score": float(r.score),
             "level": level_for(r.score, low, high), "confidence": r.confidence, "dq_score": float(r.dq_score),
             "primary_risk_type": r.primary_risk_type, "expert_status": r.expert_status}
            for r in top.itertuples()
        ],
        "chain": chain,
    }
