"""Bazani sintetik namoyish ma'lumotlari bilan to'ldirish.

Ishga tushirish (backend papkasidan):
    python -m scripts.seed

Skript sxemani Alembic orqali yangilaydi, jadvallarni tozalaydi, sintetik
ma'lumotni yaratadi va Risk Engine ni to'liq ishga tushiradi. Xavf baholari
hisoblanadi, oldindan yozib qo'yilmaydi.
"""

from __future__ import annotations

import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sqlalchemy import delete, insert, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.core.config import BACKEND_DIR, get_settings  # noqa: E402
from app.core.db import Base, SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Alert,
    AppSetting,
    AuditLog,
    DataLineage,
    DataSource,
    ExpertDecision,
    ModelRegistry,
    MonthlyMetric,
    Region,
    Relation,
    RiskScore,
    Sector,
    Subject,
    User,
)
from app.services import pipeline  # noqa: E402
from data_gen.generate import generate  # noqa: E402
from data_gen.reference import (  # noqa: E402
    DATA_SOURCES,
    DEMO_USERS,
    GOLDEN_SUBJECT,
    REGIONS,
    SECTORS,
)
from ml.features.build import FEATURE_DEFS  # noqa: E402
from ml.inference import engine  # noqa: E402


def _chunks(rows: list[dict], n: int = 5000):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def migrate() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


def clear(db) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == "alembic_version":
            continue
        db.execute(delete(table))
    db.commit()


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index: taqsimot siljishi o'lchovi."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    e = np.histogram(expected, edges)[0] / len(expected) + 1e-4
    a = np.histogram(np.clip(actual, edges[0], edges[-1]), edges)[0] / len(actual) + 1e-4
    return float(np.sum((a - e) * np.log(a / e)))


def main() -> None:
    t0 = time.perf_counter()
    s = get_settings()
    rng = np.random.default_rng(s.seed + 1)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    period_end = date.fromisoformat(s.data_period_end)

    print("• Sxema yangilanmoqda (alembic upgrade head)…")
    migrate()
    db = SessionLocal()
    clear(db)

    print("• Ma'lumotnomalar va foydalanuvchilar…")
    db.execute(insert(Region), [
        {"id": r[0], "name": r[1], "short_name": r[2], "geo_key": r[3], "sort_order": i}
        for i, r in enumerate(REGIONS)
    ])
    db.execute(insert(Sector), [{"id": x[0], "name": x[1], "icon": x[2]} for x in SECTORS])
    users = {}
    for username, pwd, name, role, region in DEMO_USERS:
        u = User(username=username, full_name=name, role=role, region_id=region, password_hash=hash_password(pwd))
        db.add(u)
        users[username] = u
    db.flush()

    sources = {}
    for i, (code, name, stype, status, desc, err) in enumerate(DATA_SOURCES):
        lag_h = {"active": 6 + i, "delayed": 24 * 38, "error": 24 * 3}.get(status, 0)
        ds = DataSource(code=code, name=name, source_type=stype, status=status, description=desc,
                        last_load_at=now - timedelta(hours=lag_h), last_error=err)
        db.add(ds)
        sources[code] = ds
    db.flush()

    print("• Sintetik ma'lumot yaratilmoqda (5000 subyekt, 24 oy)…")
    ds = generate(n_subjects=5000, seed=s.seed, end=period_end, n_months=s.history_months)
    subj = ds.subjects
    db.execute(insert(Subject), [
        {"id": int(r.id), "code": r.code, "region_id": r.region_id, "sector_id": r.sector_id,
         "size_group": r.size_group, "stir": r.stir, "org_form": r.org_form, "registered_at": r.registered_at,
         "source_count": int(r.source_count), "duplicate_records": int(r.duplicate_records),
         "history_months": int(r.history_months), "is_synthetic": True}
        for r in subj.itertuples()
    ])
    tx_src = sources["synthetic_demo_transactions_v1"].id
    m = ds.metrics.astype(object).where(ds.metrics.notna(), None)
    metric_rows = [
        {"subject_id": int(r.subject_id), "period": r.period, "turnover": r.turnover,
         "tx_count": None if r.tx_count is None else int(r.tx_count), "avg_check": r.avg_check,
         "tax_index": r.tax_index, "registry_turnover": r.registry_turnover, "source_id": tx_src}
        for r in m.itertuples()
    ]
    for chunk in _chunks(metric_rows):
        db.execute(insert(MonthlyMetric), chunk)
    db.execute(insert(Relation), [
        {"source_id": int(r.source_id), "target_id": int(r.target_id), "rel_type": r.rel_type,
         "weight": float(r.weight), "since": r.since} for r in ds.relations.itertuples()
    ])
    db.flush()

    # Manbalar statistikasi va ma'lumot kelib chiqishi.
    n_rows = len(ds.metrics)
    stats = {
        "synthetic_demo_transactions_v1": (n_rows, int(ds.metrics["turnover"].isna().sum() + (ds.metrics["turnover"] < 0).sum())),
        "synthetic_demo_registry_v1": (len(subj) + n_rows, int(ds.metrics["registry_turnover"].isna().sum())),
        "synthetic_demo_tax_v1": (n_rows, int(ds.metrics["tax_index"].isna().sum())),
        "synthetic_demo_relations_v1": (len(ds.relations), 0),
        "synthetic_demo_customs_v1": (0, 0),
    }
    for code, (rows, rejected) in stats.items():
        src = sources[code]
        src.rows, src.rejected = rows, rejected
        src.quality_score = None if rows == 0 else round(100 * (1 - rejected / max(rows, 1)) - (8 if src.status == "delayed" else 0), 1)
    steps = ["ingestion", "schema_validation", "data_quality", "deduplication", "entity_resolution",
             "normalization", "anonymization"]
    for code, target in [("synthetic_demo_transactions_v1", "monthly_metrics"),
                         ("synthetic_demo_registry_v1", "subjects"),
                         ("synthetic_demo_tax_v1", "monthly_metrics"),
                         ("synthetic_demo_relations_v1", "relations")]:
        for step in steps:
            db.add(DataLineage(source_id=sources[code].id, source_record_id=f"{code}/batch-{period_end:%Y%m}",
                               target_table=target, target_record_id=None, transformation=step,
                               pipeline_version=pipeline.PIPELINE_VERSION, processed_at=now - timedelta(hours=5)))

    print("• Risk Engine ishga tushirilmoqda…")
    subjects_df, metrics_df, relations_df = pipeline.load_frames(db)
    out = pipeline.compute(subjects_df, metrics_df, relations_df)
    pipeline.persist(db, out)
    pipeline.register_features(db)
    scores = out.result.scores
    print(f"  hisoblandi: {len(scores)} subyekt, {out.elapsed:.1f} s")

    # Sintetik sinov ko'rsatkichlari: joylangan anomaliyalarga nisbatan.
    labels = scores.index.map(lambda i: int(i in ds.ground_truth)).to_numpy()
    auc = float(roc_auc_score(labels, scores["score"]))
    top = scores["score"].rank(ascending=False) <= len(scores) * 0.05
    precision5 = float(labels[top.to_numpy()].mean())
    recall_high = float(labels[(scores["score"] >= s.high_threshold).to_numpy()].sum() / labels.sum())

    # Model monitoringi: oxirgi 6 oy bo'yicha tarixiy kesimlar (haqiqiy qayta hisob).
    print("• Model monitoringi uchun tarixiy kesimlar…")
    series = []
    ref_scores = None
    snap_ends = [date(period_end.year + (period_end.month - k - 1) // 12, (period_end.month - k - 1) % 12 + 1, 1)
                 for k in range(5, -1, -1)]
    for pe in snap_ends:
        snap = out if pe == period_end else pipeline.compute(subjects_df, metrics_df, relations_df, period_end=pe)
        sc = snap.result.scores
        if ref_scores is None:
            ref_scores = sc["score"].to_numpy()
        series.append({
            "period": pe.isoformat(),
            "mean_score": round(float(sc["score"].mean()), 2),
            "high_share": round(float((sc["score"] >= s.high_threshold).mean()), 4),
            "anomalies": int((snap.result.signals["anomaly"] > 0).sum()),
            "mean_confidence": round(float(sc["confidence_value"].mean()), 3),
            "psi": round(psi(ref_scores, sc["score"].to_numpy()), 4),
            "distribution": np.histogram(sc["score"], bins=10, range=(0, 100))[0].tolist(),
        })

    print("• Modellar reestri…")
    feature_names = [f[0] for f in FEATURE_DEFS]
    synthetic_note = "Sintetik namoyish ma’lumotlarida o‘lchangan sinov ko‘rsatkichi"
    db.add_all([
        ModelRegistry(model_key=engine.MODEL_KEY, name="RASAD Risk Engine", version="0.9.0",
                      algorithm="Qoidalar + z-og‘ish", training_dataset="synthetic-2026.02-v0",
                      features=feature_names[:5], metrics={"note": "Ma’lumot mavjud emas"},
                      threshold={"low": 40, "high": 70}, status="ARCHIVED", created_by="admin",
                      approved_by="Namoyish administratori", approved_at=now - timedelta(days=120),
                      created_at=now - timedelta(days=140)),
        ModelRegistry(model_key=engine.MODEL_KEY, name="RASAD Risk Engine", version=engine.MODEL_VERSION,
                      algorithm="Qoidalar + Isolation Forest + vaqt og‘ishi + graf (NetworkX) + kalibrlash",
                      training_dataset=pipeline.data_version(period_end), features=feature_names,
                      metrics={"auc": round(auc, 3), "precision_at_5pct": round(precision5, 3),
                               "recall_high": round(recall_high, 3), "note": synthetic_note},
                      threshold={"low": s.low_threshold, "high": s.high_threshold,
                                 "calibration_scale": engine.CALIBRATION_SCALE},
                      drift={"psi": series[-1]["psi"], "status": "normal" if series[-1]["psi"] < 0.2 else "warning",
                             "series": series},
                      status="ACTIVE", created_by="admin", approved_by="Namoyish administratori",
                      approved_at=now - timedelta(days=21), created_at=now - timedelta(days=30)),
        ModelRegistry(model_key=engine.MODEL_KEY, name="RASAD Risk Engine", version="1.1.0",
                      algorithm="Qoidalar + Isolation Forest + LightGBM (rejada)", training_dataset="synthetic-2026.08-v2",
                      features=feature_names, metrics={"note": "Baholash jarayonida"},
                      threshold={"low": 40, "high": 70}, status="TESTING", created_by="admin",
                      created_at=now - timedelta(days=6)),
        ModelRegistry(model_key="rasad-network", name="Aloqadorlik tahlili modeli", version="0.2.0",
                      algorithm="PageRank + jamoalarni aniqlash", training_dataset="synthetic-2026.08-v1",
                      features=["network_risk_score"], metrics={"note": "Ma’lumot mavjud emas"},
                      threshold={}, status="DRAFT", created_by="admin", created_at=now - timedelta(days=2)),
    ])

    print("• Ogohlantirishlar va ekspert qarorlari…")
    golden_id = int(GOLDEN_SUBJECT.split("-")[1])
    alert_ids = scores.index[scores["score"] >= 60].tolist()
    region_of = subj.set_index("id")["region_id"]
    analyst_for = {"NG": users["tahlilchi"], "TK": users["tahlilchi2"]}
    decision_for = {"confirmed": "confirmed", "rejected": "rejected", "in_review": "sent_review"}
    comments = {
        "confirmed": "Ko‘rsatkichlar dinamikasi va manbalar ziddiyati tasdiqlandi. Qo‘shimcha tekshiruv tavsiya etiladi.",
        "rejected": "Og‘ish mavsumiy omil bilan izohlanadi. Qo‘shimcha choralar talab etilmaydi.",
        "sent_review": "Aloqador subyektlar bo‘yicha qo‘shimcha tahlil uchun yuborildi.",
    }
    alerts, decisions = [], []
    for n, sid in enumerate(sorted(alert_ids, key=lambda i: -scores.at[i, "score"]), start=1):
        sc = float(scores.at[sid, "score"])
        region = region_of[sid]
        if sid == golden_id:
            status, hours = "new", 30
        else:
            status = rng.choice(["new", "in_review", "confirmed", "rejected", "closed"],
                                p=[0.52, 0.2, 0.11, 0.1, 0.07])
            hours = float(rng.uniform(1, 24 * 60))
        analyst = analyst_for.get(region) if status != "new" or rng.random() < 0.3 else None
        if status != "new" and analyst is None:
            analyst = users["tahlilchi"] if rng.random() < 0.5 else users["tahlilchi2"]
        detected = now - timedelta(hours=hours)
        alerts.append({"code": f"ALR-{n:06d}", "subject_id": int(sid), "region_id": region,
                       "risk_type": str(scores.at[sid, "primary_risk_type"]),
                       "severity": "high" if sc >= s.high_threshold else "medium", "score": sc,
                       "status": str(status), "analyst_id": analyst.id if analyst else None,
                       "detected_at": detected, "updated_at": detected})
        if status in decision_for:
            decisions.append((int(sid), analyst, decision_for[status], detected + timedelta(hours=float(rng.uniform(2, 72))), sc))
    db.execute(insert(Alert), alerts)
    alert_by_subject = dict(db.execute(select(Alert.subject_id, Alert.id)).all())
    for sid, analyst, decision, at, sc in decisions:
        db.add(ExpertDecision(subject_id=sid, alert_id=alert_by_subject.get(sid), user_id=analyst.id,
                              decision=decision, comment=comments[decision], score_at_decision=sc,
                              model_version=f"{engine.MODEL_KEY}-{engine.MODEL_VERSION}", created_at=at))
        db.query(RiskScore).filter(RiskScore.subject_id == sid).update({"expert_status": decision})

    print("• Sozlamalar va audit…")
    db.add_all([
        AppSetting(key="risk_thresholds", value={"low": s.low_threshold, "high": s.high_threshold},
                   updated_by="system"),
        AppSetting(key="drift_thresholds", value={"psi": 0.2, "rejection_rate": 0.35, "confidence_drop": 0.1},
                   updated_by="system"),
        AppSetting(key="retention_policy", value=[
            {"data_type": "Xom ma’lumotlar (RAW)", "retention": "3 yil", "archive": "5 yil", "deletion": "Avtomatik, tasdiq bilan"},
            {"data_type": "Tahlil natijalari", "retention": "5 yil", "archive": "10 yil", "deletion": "Qo‘lda, rahbar tasdig‘i bilan"},
            {"data_type": "Ekspert qarorlari", "retention": "10 yil", "archive": "Muddatsiz", "deletion": "O‘chirilmaydi"},
            {"data_type": "Audit jurnali", "retention": "10 yil", "archive": "Muddatsiz", "deletion": "O‘chirilmaydi"},
            {"data_type": "Hisobotlar", "retention": "5 yil", "archive": "10 yil", "deletion": "Avtomatik"},
        ], updated_by="system"),
    ])
    db.add(AuditLog(at=now, user_id=None, username="system", action="data.seed", object_type="dataset",
                    object_id=pipeline.data_version(period_end), old_value=None,
                    new_value={"subjects": len(subj), "metrics": n_rows, "relations": len(ds.relations)},
                    ip="127.0.0.1", session_id="seed"))
    db.add(AuditLog(at=now, user_id=None, username="system", action="model.recompute", object_type="model",
                    object_id=f"{engine.MODEL_KEY}-{engine.MODEL_VERSION}", old_value=None,
                    new_value={"subjects": len(scores)}, ip="127.0.0.1", session_id="seed"))
    db.commit()

    g = scores.loc[golden_id]
    dist = pd.cut(scores["score"], [-0.1, s.low_threshold - 0.01, s.high_threshold - 0.01, 100],
                  labels=["past", "o‘rta", "yuqori"]).value_counts(normalize=True).round(4).to_dict()
    print(f"\n✓ Tayyor: {time.perf_counter() - t0:.1f} s")
    print(f"  Xavf taqsimoti: {dist}")
    print(f"  Ogohlantirishlar: {len(alerts)}; qarorlar: {len(decisions)}")
    print(f"  Sintetik AUC={auc:.3f}, precision@5%={precision5:.3f}")
    print(f"  {GOLDEN_SUBJECT}: score={g.score}, ishonch={g.confidence} ({g.confidence_value}), "
          f"DQ={g.dq_score}, tur={g.primary_risk_type} {g.risk_types}")
    db.close()


if __name__ == "__main__":
    main()
