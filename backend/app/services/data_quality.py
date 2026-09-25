"""Ma'lumotlar sifati moduli (TZ §5).

Olti o'lchov bo'yicha 0–100 ball:
to'liqlik, to'g'rilik, yagonalik, muvofiqlik, dolzarblik, mantiqiy to'g'rilik.
Ma'lumot sifati past bo'lsa, xavf bahosining ishonch darajasi ham pasayadi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

DIMENSIONS = {
    "completeness": "To‘liqlik",
    "validity": "To‘g‘rilik",
    "uniqueness": "Yagonalik",
    "conformity": "Muvofiqlik",
    "timeliness": "Dolzarblik",
    "logic": "Mantiqiy to‘g‘rilik",
}

WEIGHTS = {
    "completeness": 0.20,
    "validity": 0.15,
    "uniqueness": 0.15,
    "conformity": 0.10,
    "timeliness": 0.25,
    "logic": 0.15,
}

METRIC_FIELDS = ["turnover", "tx_count", "avg_check", "tax_index", "registry_turnover"]
STIR_RE = re.compile(r"^\d{9}$")
ORG_FORMS = {"MCHJ", "XK", "YaTT", "AJ", "DUK", "QK"}
LOW_DQ = 60.0


@dataclass
class QualityResult:
    score: float
    dimensions: dict[str, float]


def _lag_months(latest: date | None, period_end: date) -> int:
    if latest is None or pd.isna(latest):
        return 99
    return (period_end.year - latest.year) * 12 + (period_end.month - latest.month)


def _timeliness_from_lag(lag: int) -> float:
    return {0: 100.0, 1: 75.0, 2: 45.0, 3: 25.0}.get(lag, 10.0)


def combine(dimensions: dict[str, float]) -> float:
    return round(sum(WEIGHTS[k] * dimensions[k] for k in WEIGHTS), 1)


def assess_subjects(subjects: pd.DataFrame, metrics: pd.DataFrame, period_end: date) -> pd.DataFrame:
    """Har bir subyekt uchun sifat o'lchovlari va umumiy ballni qaytaradi."""
    m = metrics
    g = m.groupby("subject_id")

    missing = m[METRIC_FIELDS].isna().sum(axis=1).groupby(m["subject_id"]).sum()
    expected_rows = subjects.set_index("id")["history_months"]
    present_rows = g.size().reindex(expected_rows.index, fill_value=0)
    miss_ratio = (missing.reindex(expected_rows.index, fill_value=0)
                  + (expected_rows - present_rows).clip(lower=0) * len(METRIC_FIELDS)) / (
        expected_rows * len(METRIC_FIELDS))
    completeness = (100 * (1 - 4 * miss_ratio)).clip(0, 100)

    invalid = ((m["turnover"] < 0) | (m["avg_check"] <= 0) | (m["tx_count"] < 0)
               | (m["tax_index"] < 0)).groupby(m["subject_id"]).sum()
    validity = (100 - 30 * invalid.reindex(expected_rows.index, fill_value=0)).clip(0, 100)

    dup = subjects.set_index("id")["duplicate_records"]
    uniqueness = (100 - 12 * dup).clip(0, 100)

    stir_ok = subjects.set_index("id")["stir"].astype(str).map(lambda s: bool(STIR_RE.match(s)))
    form_ok = subjects.set_index("id")["org_form"].isin(ORG_FORMS)
    conformity = 100 - 55 * (~stir_ok).astype(float) - 25 * (~form_ok).astype(float)

    # Dolzarblik: har bir maydonning oxirgi mavjud davri bo'yicha kechikish.
    timeliness_parts = []
    for f in METRIC_FIELDS:
        latest = m.loc[m[f].notna()].groupby("subject_id")["period"].max()
        latest = latest.reindex(expected_rows.index)
        timeliness_parts.append(latest.map(lambda d: _timeliness_from_lag(_lag_months(d, period_end))))
    timeliness = pd.concat(timeliness_parts, axis=1).mean(axis=1)

    logic_bad = (((m["turnover"] == 0) & (m["tx_count"] > 0))
                 | (m["period"] > period_end)).groupby(m["subject_id"]).sum()
    logic = (100 - 25 * logic_bad.reindex(expected_rows.index, fill_value=0)).clip(0, 100)

    out = pd.DataFrame({
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "conformity": conformity,
        "timeliness": timeliness,
        "logic": logic,
    }).fillna(0).round(1)
    out["dq_score"] = sum(WEIGHTS[k] * out[k] for k in WEIGHTS).round(1)
    out.index.name = "subject_id"
    return out


def assess_rows(df: pd.DataFrame, required: list[str], today: date | None = None) -> dict:
    """Import qilinayotgan jadval uchun sifat bahosi va qatorlar bo'yicha xatolar."""
    today = today or date.today()
    n = len(df)
    if n == 0:
        dims = {k: 0.0 for k in DIMENSIONS}
        return {"score": 0.0, "dimensions": dims, "row_errors": {}, "duplicates": []}

    row_errors: dict[int, list[str]] = {}

    def err(i: int, msg: str):
        row_errors.setdefault(int(i), []).append(msg)

    present = [c for c in required if c in df.columns]
    miss_cells = int(df[present].isna().to_numpy().sum()) if present else n
    for c in present:
        for i in df.index[df[c].isna()]:
            err(i, f"«{c}» maydoni bo‘sh")
    completeness = 100 * (1 - miss_cells / max(1, n * max(1, len(present))))

    invalid = 0
    for c in ("turnover", "tx_count", "avg_check"):
        if c in df.columns:
            vals = pd.to_numeric(df[c], errors="coerce")
            bad = df.index[(vals < 0) | (df[c].notna() & vals.isna())]
            invalid += len(bad)
            for i in bad:
                err(i, f"«{c}» qiymati noto‘g‘ri")
    validity = 100 * (1 - invalid / n)

    dup_mask = df.duplicated(keep="first")
    duplicates = df.index[dup_mask].tolist()
    uniqueness = 100 * (1 - len(duplicates) / n)

    conform_bad = 0
    if "stir" in df.columns:
        bad = df.index[~df["stir"].astype(str).str.fullmatch(r"\d{9}")]
        conform_bad = len(bad)
        for i in bad:
            err(i, "STIR formati 9 ta raqamdan iborat bo‘lishi kerak")
    conformity = 100 * (1 - conform_bad / n)

    timeliness = 100.0
    logic_bad = 0
    if "period" in df.columns:
        periods = pd.to_datetime(df["period"], errors="coerce")
        future = df.index[periods.dt.date > today]
        logic_bad += len(future)
        for i in future:
            err(i, "Sana joriy sanadan keyin bo‘lishi mumkin emas")
        latest = periods.max()
        if pd.notna(latest):
            lag = (today.year - latest.year) * 12 + today.month - latest.month
            timeliness = _timeliness_from_lag(max(0, lag - 1))
    logic = 100 * (1 - logic_bad / n)

    dims = {
        "completeness": round(float(np.clip(completeness, 0, 100)), 1),
        "validity": round(float(np.clip(validity, 0, 100)), 1),
        "uniqueness": round(float(np.clip(uniqueness, 0, 100)), 1),
        "conformity": round(float(np.clip(conformity, 0, 100)), 1),
        "timeliness": round(float(timeliness), 1),
        "logic": round(float(np.clip(logic, 0, 100)), 1),
    }
    return {"score": combine(dims), "dimensions": dims, "row_errors": row_errors, "duplicates": duplicates}
