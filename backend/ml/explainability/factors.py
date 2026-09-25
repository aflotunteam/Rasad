"""Xavf sabablarini standart formatda shakllantirish (TZ §16).

factor · current_value · baseline · deviation · impact · source
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.inference.engine import COMPONENTS

# komponent → (belgi, omil nomi, birlik, manba, qiymatni ko'rsatish funksiyasi)
FACTOR_META = {
    "dynamics": ("turnover_change_3m", "Aylanma o‘zgarishi", "%", "synthetic_demo_transactions_v1"),
    "sector": ("tax_index_6m", "Soliq yuklamasi indeksi (sohaga nisbatan)", "indeks", "synthetic_demo_tax_v1"),
    "regional": ("turnover_change_3m", "Hududiy qonuniyatdan og‘ish", "%", "synthetic_demo_transactions_v1"),
    "operational": ("avg_check_ratio", "O‘rtacha chek o‘zgarishi", "%", "synthetic_demo_transactions_v1"),
    "conflict": ("source_conflict_ratio", "Reyestr va tranzaksiyalar ziddiyati", "%", "synthetic_demo_registry_v1"),
    "seasonal": ("seasonality_deviation", "Mavsumiy qonuniyatdan og‘ish", "indeks", "synthetic_demo_transactions_v1"),
    "network": ("network_risk_score", "Xavfli subyektlar bilan aloqadorlik", "ta", "synthetic_demo_relations_v1"),
    "anomaly": ("anomaly_score", "Ko‘p o‘lchovli noodatiylik (Isolation Forest)", "persentil", "rasad-risk-model"),
}

PERCENT_FEATURES = {"turnover_change_3m", "source_conflict_ratio"}
RATIO_FEATURES = {"avg_check_ratio"}


def _display(feature: str, v: float | None) -> float | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if feature in PERCENT_FEATURES:
        return round(float(v) * 100, 1)
    if feature in RATIO_FEATURES:
        return round((float(v) - 1) * 100, 1)
    if feature == "anomaly_score":
        return round(float(v) * 100, 1)
    return round(float(v), 3)


def peer_ranges(feats: pd.DataFrame, network: pd.DataFrame, anomaly: pd.Series) -> dict:
    """Soha (va hudud) bo'yicha P10–P90 kutilgan oraliqlar."""
    f = feats.copy()
    f["network_risk_score"] = network["risky_neighbors"]
    f["anomaly_score"] = anomaly
    cols = ["turnover_change_3m", "tax_index_6m", "avg_check_ratio", "source_conflict_ratio",
            "seasonality_deviation", "network_risk_score", "anomaly_score"]
    by_sector = f.groupby("sector_id")[cols].quantile([0.1, 0.9]).unstack()
    by_region = f.groupby("region_id")["turnover_change_3m"].quantile([0.1, 0.9]).unstack()
    return {"sector": by_sector, "region": by_region}


def deviation_level(signal: float) -> str:
    if signal >= 0.6:
        return "high"
    if signal >= 0.25:
        return "medium"
    return "low"


def factors_for(subject_id: int, feats: pd.DataFrame, signals: pd.DataFrame, contributions: pd.DataFrame,
                network: pd.DataFrame, anomaly: pd.Series, ranges: dict, min_factors: int = 3) -> list[dict]:
    row = feats.loc[subject_id]
    contrib = contributions.loc[subject_id].sort_values(ascending=False)
    out = []
    for comp, impact in contrib.items():
        if impact <= 0.05 and len(out) >= min_factors:
            continue
        feature, name, unit, source = FACTOR_META[comp]
        if comp == "network":
            current = float(network.at[subject_id, "risky_neighbors"])
        elif comp == "anomaly":
            current = float(anomaly.at[subject_id])
        else:
            current = row[feature]
        if comp == "regional":
            lo, hi = ranges["region"].loc[row["region_id"]]
        else:
            lo = ranges["sector"].loc[row["sector_id"], (feature, 0.1)]
            hi = ranges["sector"].loc[row["sector_id"], (feature, 0.9)]
        out.append({
            "feature": feature,
            "factor": name,
            "risk_type": COMPONENTS[comp][0],
            "current_value": _display(feature, current) if comp != "network" else current,
            "baseline_low": _display(feature, lo) if comp != "network" else round(float(lo), 1),
            "baseline_high": _display(feature, hi) if comp != "network" else round(float(hi), 1),
            "unit": unit,
            "deviation": deviation_level(float(signals.at[subject_id, comp])),
            "impact": round(float(impact), 1),
            "source": source,
        })
    out.sort(key=lambda x: x["impact"], reverse=True)
    for i, f in enumerate(out, start=1):
        f["rank"] = i
    return out
