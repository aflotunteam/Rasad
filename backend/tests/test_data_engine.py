"""Sintetik ma'lumot, ma'lumot sifati, Entity Resolution va Risk Engine testlari."""

from datetime import date

import pandas as pd
from sqlalchemy import func, select

from app.models import MonthlyMetric, Region, RiskScore, Sector, Subject
from app.services.data_quality import assess_rows
from app.services.entity_resolution import SourceRecord, resolve
from data_gen.generate import generate


def test_generator_is_deterministic():
    a = generate(n_subjects=300, seed=7)
    b = generate(n_subjects=300, seed=7)
    pd.testing.assert_frame_equal(a.metrics, b.metrics)
    pd.testing.assert_frame_equal(a.relations, b.relations)


def test_seed_volume(db):
    assert db.scalar(select(func.count()).select_from(Subject)) == 5000  # AC-02
    assert db.scalar(select(func.count()).select_from(Region)) == 14
    assert db.scalar(select(func.count()).select_from(Sector)) >= 10
    periods = db.scalar(select(func.count(func.distinct(MonthlyMetric.period))))
    assert 12 <= periods <= 24


def test_golden_subject_is_computed(db):
    rs = db.scalar(select(RiskScore).join(Subject).where(Subject.code == "SUB-000125"))
    assert rs.subject.region_id == "NG"
    assert 80 <= rs.score <= 84
    assert rs.confidence == "high"
    assert len(rs.factors) >= 3  # AC-08
    assert rs.factors[0].feature == "turnover_change_3m"
    assert abs(sum(f.impact for f in rs.factors) - rs.score) < 1.0


def test_score_distribution_is_realistic(db):
    scores = [s for (s,) in db.execute(select(RiskScore.score))]
    high = sum(s >= 70 for s in scores) / len(scores)
    low = sum(s < 40 for s in scores) / len(scores)
    assert 0.005 <= high <= 0.06
    assert low >= 0.85


def test_low_data_quality_lowers_confidence(db):
    rows = db.execute(select(RiskScore.dq_score, RiskScore.confidence)).all()
    assert any(dq < 60 for dq, _ in rows)
    assert all(conf == "low" for dq, conf in rows if dq < 60)
    assert all(conf != "high" for dq, conf in rows if dq < 75)


def test_row_quality_rules():
    df = pd.DataFrame([
        {"stir": "912345678", "period": "2026-07-01", "turnover": 10.0},
        {"stir": "12345", "period": "2030-01-01", "turnover": -5.0},
        {"stir": "912345678", "period": "2026-07-01", "turnover": 10.0},
    ])
    res = assess_rows(df, ["stir", "period", "turnover"], today=date(2026, 9, 25))
    assert res["duplicates"] == [2]
    assert any("joriy sanadan keyin" in e for e in res["row_errors"][1])
    assert res["dimensions"]["logic"] < 100
    assert res["score"] < 100


def test_entity_resolution_merges_name_variants():
    recs = [
        SourceRecord("reestr", "1", "ABC MCHJ"),
        SourceRecord("soliq", "2", "ABC МЧЖ"),
        SourceRecord("bank", "3", "ABC LLC"),
        SourceRecord("bank", "4", "«ABC»"),
        SourceRecord("reestr", "5", "Boshqa Savdo MCHJ"),
    ]
    out = resolve(recs)
    assert len(out) == 2
    assert {r.record_id for r in out[0].records} == {"1", "2", "3", "4"}
    assert out[0].internal_subject_id == "SUB-000001"


def test_entity_resolution_respects_stir():
    recs = [
        SourceRecord("a", "1", "ABC MCHJ", stir="912345678"),
        SourceRecord("b", "2", "ABC MCHJ", stir="987654321"),
    ]
    assert len(resolve(recs)) == 2
