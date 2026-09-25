"""RASAD Risk Engine (TZ §47).

Input → Feature Vector → Rules + Anomaly Model + Time Model + Graph Model
      → Calibration → Risk Score → Confidence → Explanation

Har bir komponent 0–1 oralig'idagi signal beradi. Signallar vaznli yig'iladi,
so'ng monoton kalibrlash funksiyasi bilan 0–100 shkalaga o'tkaziladi. Omillarning
hissasi yakuniy ballga proporsional taqsimlanadi, shuning uchun "NEGA?" oynasidagi
ta'sir ballari yig'indisi xavf bahosiga teng bo'ladi.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.features.build import network_features

MODEL_KEY = "rasad-risk"
MODEL_VERSION = "1.0.0"

# Komponent: (xavf turi, vazn). Vaznlar ekspert tomonidan belgilangan MVP qiymatlari.
COMPONENTS: dict[str, tuple[str, float]] = {
    "dynamics": ("R01", 28.0),
    "sector": ("R02", 16.0),
    "regional": ("R03", 5.0),
    "operational": ("R04", 16.0),
    "network": ("R05", 12.0),
    "conflict": ("R06", 20.0),
    "seasonal": ("R07", 14.0),
    "anomaly": ("R08", 10.0),
}
CALIBRATION_SCALE = 42.0
STRONG_SIGNAL = 0.6

IF_FEATURES = ["turnover_change_3m", "transaction_count_ratio", "avg_check_ratio", "tax_index_6m",
               "source_conflict_ratio", "seasonality_deviation", "volatility"]


def z_signal(z: pd.Series, start: float = 2.0, span: float = 4.0) -> pd.Series:
    """|z| ≤ start → 0; |z| ≥ start+span → 1; oralig'ida chiziqli."""
    return ((z.abs() - start) / span).clip(0, 1).fillna(0)


def calibrate(raw: pd.Series | np.ndarray) -> pd.Series | np.ndarray:
    return 100 * (1 - np.exp(-np.asarray(raw) / CALIBRATION_SCALE))


@dataclass
class EngineResult:
    scores: pd.DataFrame  # subject_id bo'yicha
    signals: pd.DataFrame
    contributions: pd.DataFrame
    network: pd.DataFrame


def _anomaly_model(feats: pd.DataFrame, seed: int) -> pd.Series:
    X = feats[IF_FEATURES].copy()
    X["transaction_count_ratio"] = np.log(X["transaction_count_ratio"])
    X["avg_check_ratio"] = np.log(X["avg_check_ratio"])
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())
    X = (X - X.median()) / (X.quantile(0.75) - X.quantile(0.25)).replace(0, 1)
    model = IsolationForest(n_estimators=200, random_state=seed, contamination="auto")
    model.fit(X)
    raw = -model.score_samples(X)
    pct = pd.Series(raw, index=feats.index).rank(pct=True)
    return pct


def run(feats: pd.DataFrame, relations: pd.DataFrame, dq: pd.DataFrame, subjects: pd.DataFrame,
        seed: int = 2026) -> EngineResult:
    s = pd.DataFrame(index=feats.index)

    # Qoidalar va statistik og'ishlar.
    s["dynamics"] = z_signal(feats["z_change_sector"])
    s["sector"] = z_signal(feats["z_tax_sector"].clip(upper=0))  # faqat past soliq yuklamasi
    s["regional"] = z_signal(feats["z_change_region"], start=2.5, span=4.0)
    s["operational"] = z_signal(feats["z_check_sector"].clip(upper=0), start=2.5, span=6.0)
    s["conflict"] = ((feats["source_conflict_ratio"] - 0.08) / 0.40).clip(0, 1).fillna(0)
    s["seasonal"] = z_signal(feats["z_seasonal_sector"], start=3.0, span=5.0)

    # Anomaliya modeli: faqat eng noodatiy 15% subyektlar signal beradi.
    if_pct = _anomaly_model(feats, seed)
    s["anomaly"] = ((if_pct - 0.85) / 0.15).clip(0, 1)

    # Graf modeli ikki bosqichda: avval aloqadorliksiz baho, keyin qo'shnilar xavfi.
    weights = pd.Series({k: v[1] for k, v in COMPONENTS.items()})
    base_raw = (s.drop(columns=[]).assign(network=0.0)[weights.index] * weights).sum(axis=1)
    base_score = pd.Series(calibrate(base_raw), index=s.index)
    net = network_features(relations, base_score, risky_threshold=40.0)
    s["network"] = (net["network_risk_score"] / 1.5).clip(0, 1)

    s = s[list(COMPONENTS)]
    contrib_raw = s * weights
    raw = contrib_raw.sum(axis=1)
    score = pd.Series(calibrate(raw), index=s.index).round(1)
    share = contrib_raw.div(raw.replace(0, np.nan), axis=0).fillna(0)
    contributions = share.mul(score, axis=0)

    # Xavf turlari: kuchli signallar; ikki va undan ortiq bo'lsa — R08 Kompleks xavf.
    type_signals = s.drop(columns=["anomaly"])
    strong = type_signals >= STRONG_SIGNAL
    type_codes = {k: COMPONENTS[k][0] for k in type_signals.columns}
    risk_types = strong.apply(
        lambda row: [type_codes[c] for c in contributions.loc[row.name, row.index[row]].sort_values(ascending=False).index],
        axis=1,
    )
    top_component = contributions.drop(columns=["anomaly"]).idxmax(axis=1)
    primary = np.where(strong.sum(axis=1) >= 2, "R08", top_component.map(type_codes))

    # Ishonch darajasi: ma'lumot sifati, tarix uzunligi, manbalar soni va modellar kelishuvi.
    subj = subjects.set_index("id")
    dq_score = dq["dq_score"].reindex(s.index)
    history = subj["history_months"].reindex(s.index) / 24
    sources = subj["source_count"].reindex(s.index).clip(upper=4) / 4
    rules_pct = (raw - contrib_raw["anomaly"]).rank(pct=True)
    agreement = 1 - (rules_pct - if_pct).abs()
    conf_value = (0.45 * dq_score / 100 + 0.25 * history + 0.15 * sources + 0.15 * agreement).clip(0, 1)
    conf_level = np.select([conf_value >= 0.75, conf_value >= 0.55], ["high", "medium"], "low")
    conf_level = np.where(dq_score < 60, "low", np.where((dq_score < 75) & (conf_level == "high"), "medium", conf_level))

    scores = pd.DataFrame({
        "score": score,
        "raw": raw.round(3),
        "confidence": conf_level,
        "confidence_value": conf_value.round(3),
        "dq_score": dq_score,
        "primary_risk_type": primary,
        "risk_types": risk_types,
        "anomaly_score": if_pct.round(4),
    })
    return EngineResult(scores=scores, signals=s, contributions=contributions, network=net)
