"""Tahliliy belgilarni hisoblash (feature engineering).

Har bir belgi feature_registry da tavsiflanadi (FEATURE_DEFS). Belgilar oylik
ko'rsatkichlar matritsasidan (subyekt × davr) vektorlashgan holda hisoblanadi.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

FEATURE_VERSION = "1.0.0"

FEATURE_DEFS = [
    ("turnover_change_3m", "Oxirgi 3 oy aylanmasining o‘tgan yilning shu davriga nisbatan o‘zgarishi",
     "synthetic_demo_transactions_v1", "mean(T[-3:]) / mean(T[-15:-12]) - 1"),
    ("transaction_count_ratio", "Oxirgi 3 oy operatsiyalar sonining oldingi 12 oy o‘rtachasiga nisbati",
     "synthetic_demo_transactions_v1", "mean(N[-3:]) / mean(N[-15:-3])"),
    ("avg_check_ratio", "O‘rtacha chekning oldingi 12 oy o‘rtachasiga nisbati",
     "synthetic_demo_transactions_v1", "mean(C[-3:]) / mean(C[-15:-3])"),
    ("tax_index_6m", "Oxirgi 6 oy soliq yuklamasi indeksi (soha bo‘yicha taqqoslanadi)",
     "synthetic_demo_tax_v1", "mean(TAX[-6:])"),
    ("peer_deviation_score", "Soha, hudud va hajm guruhidagi o‘xshash subyektlardan robust z-og‘ish",
     "synthetic_demo_transactions_v1", "(x - median_peer) / (1.4826 * MAD_peer)"),
    ("source_conflict_ratio", "Reyestr va tranzaksiyalar manbasidagi aylanma farqi",
     "synthetic_demo_registry_v1", "mean(|R[-3:] - T[-3:]| / T[-3:])"),
    ("seasonality_deviation", "Yillik o‘zgarishlarning soha mavsumiy qonuniyatidan og‘ishi",
     "synthetic_demo_transactions_v1", "std(log(T[t]/T[t-12]) - median_sector_t), t ∈ [-12, -5]"),
    ("volatility", "Oylik o‘zgarishlar tebranuvchanligi", "synthetic_demo_transactions_v1",
     "std(diff(log T))"),
    ("network_risk_score", "Xavfi yuqori subyektlar bilan tuzilmaviy aloqalarning vaznli yig‘indisi",
     "synthetic_demo_relations_v1", "Σ w_e · 1[risk(neighbor) ≥ 40]"),
]


def _matrix(metrics: pd.DataFrame, field: str, subject_ids: np.ndarray, periods: list) -> np.ndarray:
    piv = metrics.pivot(index="subject_id", columns="period", values=field)
    piv = piv.reindex(index=subject_ids, columns=periods)
    return piv.to_numpy(dtype=float)


def _nanmean(a: np.ndarray, axis=1) -> np.ndarray:
    with np.errstate(all="ignore"):
        cnt = np.sum(~np.isnan(a), axis=axis)
        s = np.nansum(a, axis=axis)
        return np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)


def robust_z(values: pd.Series, groups: pd.Series | list[pd.Series], min_scale: float) -> pd.Series:
    """Guruh ichida robust z: (x - median) / (1.4826 · MAD), pastki chegara bilan."""
    grouped = values.groupby(groups)
    med = grouped.transform("median")
    mad = (values - med).abs().groupby(groups).transform("median") * 1.4826
    return (values - med) / np.maximum(mad.fillna(min_scale), min_scale)


def build_features(subjects: pd.DataFrame, metrics: pd.DataFrame, periods: list) -> pd.DataFrame:
    with warnings.catch_warnings():
        # Yangi subyektlarda tarix qisqa: bo'sh kesimlar NaN bo'lib qoladi, bu kutilgan holat.
        warnings.simplefilter("ignore", RuntimeWarning)
        return _build_features(subjects, metrics, periods)


def _build_features(subjects: pd.DataFrame, metrics: pd.DataFrame, periods: list) -> pd.DataFrame:
    ids = subjects["id"].to_numpy()
    T = _matrix(metrics, "turnover", ids, periods)
    N = _matrix(metrics, "tx_count", ids, periods)
    C = _matrix(metrics, "avg_check", ids, periods)
    TAX = _matrix(metrics, "tax_index", ids, periods)
    R = _matrix(metrics, "registry_turnover", ids, periods)

    # Noto'g'ri qiymatlar (manfiy yoki nol aylanma) belgilar hisobida ishlatilmaydi.
    T = np.where(T > 0, T, np.nan)
    C = np.where(C > 0, C, np.nan)

    last3 = _nanmean(T[:, -3:])
    prev_year = _nanmean(T[:, -15:-12])
    prior6 = _nanmean(T[:, -9:-3])
    base_for_change = np.where(np.isnan(prev_year), prior6, prev_year)
    turnover_change = last3 / base_for_change - 1

    tx_ratio = _nanmean(N[:, -3:]) / _nanmean(N[:, -15:-3])
    ac_ratio = _nanmean(C[:, -3:]) / _nanmean(C[:, -15:-3])
    tax6 = _nanmean(TAX[:, -6:])

    with np.errstate(all="ignore"):
        conflict = _nanmean(np.abs(R[:, -3:] - T[:, -3:]) / T[:, -3:])

        logT = np.log(T)
        yoy = logT[:, 12:] - logT[:, :-12]  # 12 ta yillik o'zgarish (oxirgi 12 oy)
    feats = pd.DataFrame({
        "subject_id": ids,
        "region_id": subjects["region_id"].to_numpy(),
        "sector_id": subjects["sector_id"].to_numpy(),
        "size_group": subjects["size_group"].to_numpy(),
        "turnover_change_3m": turnover_change,
        "transaction_count_ratio": tx_ratio,
        "avg_check_ratio": ac_ratio,
        "tax_index_6m": tax6,
        "source_conflict_ratio": conflict,
        "last3_turnover": last3,
    })

    # Mavsumiy og'ish: soha medianasiga nisbatan yillik o'zgarishlar tarqoqligi.
    window = yoy[:, :8]  # t ∈ [-12, -5]
    sector = feats["sector_id"].to_numpy()
    resid = np.full_like(window, np.nan)
    for sec in np.unique(sector):
        mask = sector == sec
        med = np.nanmedian(window[mask], axis=0)
        resid[mask] = window[mask] - med
    with np.errstate(all="ignore"):
        seas = np.nanstd(resid, axis=1)
        seas = np.where(np.sum(~np.isnan(resid), axis=1) >= 5, seas, np.nan)
        vol = np.nanstd(np.diff(logT, axis=1), axis=1)
    feats["seasonality_deviation"] = seas
    feats["volatility"] = vol

    # Guruhlar bo'yicha robust z-og'ishlar.
    change = feats["turnover_change_3m"]
    feats["z_change_sector"] = robust_z(change, [feats.sector_id, feats.size_group], 0.05)
    feats["z_change_region"] = robust_z(change, [feats.region_id], 0.06)
    feats["z_tax_sector"] = robust_z(feats["tax_index_6m"], [feats.sector_id], 0.03)
    feats["z_check_sector"] = robust_z(np.log(feats["avg_check_ratio"]), [feats.sector_id], 0.04)
    feats["z_seasonal_sector"] = robust_z(feats["seasonality_deviation"], [feats.sector_id], 0.02)
    feats["peer_deviation_score"] = feats[["z_change_sector", "z_tax_sector", "z_check_sector"]].abs().max(axis=1)

    feats = feats.set_index("subject_id", drop=False)
    return feats


def network_features(relations: pd.DataFrame, base_score: pd.Series, risky_threshold: float = 55.0) -> pd.DataFrame:
    """Aloqadorlik belgisi: xavfi yuqori qo'shnilar bilan aloqalarning vaznli yig'indisi."""
    structural = {"founder", "director", "address"}
    risky = base_score >= risky_threshold
    rows = []
    for a, b, rel, w in relations[["source_id", "target_id", "rel_type", "weight"]].itertuples(index=False):
        k = 1.0 if rel in structural else 0.5
        rows.append((a, b, w * k))
        rows.append((b, a, w * k))
    e = pd.DataFrame(rows, columns=["subject_id", "neighbor_id", "w"])
    e["neighbor_risky"] = e["neighbor_id"].map(risky).fillna(False).astype(bool)
    e["risky_w"] = e["w"] * e["neighbor_risky"]
    agg = e.groupby("subject_id").agg(
        degree=("neighbor_id", "size"),
        risky_neighbors=("neighbor_risky", "sum"),
        network_risk_score=("risky_w", "sum"),
    )
    return agg.reindex(base_score.index, fill_value=0)
