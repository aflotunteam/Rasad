"""Deterministik sintetik ma'lumot generatori.

Barcha qiymatlar sun'iy: real korxona nomlari, STIR yoki fuqarolar haqidagi
ma'lumotlar ishlatilmaydi. Bir xil seed har doim bir xil natija beradi.

Generator faqat xom ma'lumot yaratadi. Xavf bahosi keyin Risk Engine tomonidan
hisoblanadi: generator hech qanday ball yoki natijani oldindan yozmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from data_gen.reference import (
    GOLDEN_SUBJECT,
    REGIONS,
    SECTORS,
    SIZE_GROUPS,
    TURNOVER_SIGMA,
    region_level,
    size_mean_factor,
)

# Hududiy daraja rasmiy YaHM asosida; korxonalar ulushi bilan tortilgan o'rtachasi 1 ga keltiriladi,
# shunda tanlanmaning soha bo'yicha o'rtacha aylanmasi rasmiy qiymatga mos keladi.
_LEVEL_NORM = sum(w * region_level(r) for r, _, _, _, w in REGIONS)
REGION_LEVEL = {r: region_level(r) / _LEVEL_NORM for r, _, _, _, _ in REGIONS}

ANOMALY_KINDS = ["drop", "spike", "tax_low", "ops", "conflict", "seasonal"]
ANOMALY_WEIGHTS = [0.30, 0.10, 0.17, 0.16, 0.15, 0.12]


@dataclass
class SyntheticDataset:
    periods: list[date]
    subjects: pd.DataFrame
    metrics: pd.DataFrame
    relations: pd.DataFrame
    # Faqat sinov uchun: qaysi subyektga qanday sun'iy anomaliya joylangani.
    ground_truth: dict[int, list[str]] = field(default_factory=dict)


def month_starts(end: date, n: int) -> list[date]:
    out = []
    y, m = end.year, end.month
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def _fake_stir(rng: np.random.Generator, valid: bool = True) -> str:
    # Sintetik STIR 9 ga boshlanadi (real STIR diapazonlari bilan kesishmaslik uchun).
    digits = "9" + "".join(str(d) for d in rng.integers(0, 10, size=8))
    return digits if valid else digits[:8]


def generate(n_subjects: int = 5000, seed: int = 2026, end: date = date(2026, 8, 1),
             n_months: int = 24) -> SyntheticDataset:
    rng = np.random.default_rng(seed)
    periods = month_starts(end, n_months)
    months = np.array([p.month for p in periods])
    t_idx = np.arange(n_months)

    region_ids = [r[0] for r in REGIONS]
    region_w = np.array([r[4] for r in REGIONS])
    region_w = region_w / region_w.sum()
    sector_by_id = {s[0]: s for s in SECTORS}
    sector_ids = [s[0] for s in SECTORS]
    sector_w = np.array([s[3] for s in SECTORS])
    sector_w = sector_w / sector_w.sum()
    size_names = [s[0] for s in SIZE_GROUPS]
    size_w = np.array([s[1] for s in SIZE_GROUPS])
    size_mult = {s[0]: s[2] for s in SIZE_GROUPS}

    golden_id = int(GOLDEN_SUBJECT.split("-")[1])

    # --- Subyektlar --------------------------------------------------------
    subj_rows = []
    for sid in range(1, n_subjects + 1):
        region = region_ids[rng.choice(len(region_ids), p=region_w)]
        sector = sector_ids[rng.choice(len(sector_ids), p=sector_w)]
        size = size_names[rng.choice(len(size_names), p=size_w)]
        new_firm = rng.random() < 0.07
        if new_firm:
            history = int(rng.integers(6, 21))
            reg_month = periods[n_months - history]
            registered = date(reg_month.year, reg_month.month, int(rng.integers(1, 28)))
        else:
            history = n_months
            registered = date(int(rng.integers(2008, 2024)), int(rng.integers(1, 13)), int(rng.integers(1, 28)))
        subj_rows.append({
            "id": sid,
            "code": f"SUB-{sid:06d}",
            "region_id": region,
            "sector_id": sector,
            "size_group": size,
            "stir": _fake_stir(rng),
            "org_form": rng.choice(["MCHJ", "XK", "YaTT", "AJ"], p=[0.62, 0.12, 0.2, 0.06]),
            "registered_at": registered,
            "history_months": history,
            "source_count": int(rng.choice([2, 3, 4], p=[0.25, 0.5, 0.25])),
            "duplicate_records": 0,
        })
    subjects = pd.DataFrame(subj_rows).set_index("id", drop=False)

    # Oltin yo'l subyekti: Namangan, savdo, o'rta hajm, to'liq tarix.
    subjects.loc[golden_id, ["region_id", "sector_id", "size_group", "history_months", "source_count"]] = [
        "NG", "SAV", "medium", n_months, 3]
    subjects.loc[golden_id, "registered_at"] = date(2019, 4, 12)
    subjects.loc[golden_id, "org_form"] = "MCHJ"

    # --- Anomaliyalar ------------------------------------------------------
    ground_truth: dict[int, list[str]] = {}
    candidates = [i for i in subjects.index if i != golden_id]
    n_anom = int(n_subjects * 0.07)
    anom_ids = rng.choice(candidates, size=n_anom, replace=False)
    for sid in anom_ids:
        kinds = [ANOMALY_KINDS[rng.choice(len(ANOMALY_KINDS), p=ANOMALY_WEIGHTS)]]
        if rng.random() < 0.22:
            second = ANOMALY_KINDS[rng.choice(len(ANOMALY_KINDS), p=ANOMALY_WEIGHTS)]
            if second not in kinds:
                kinds.append(second)
        ground_truth[int(sid)] = kinds
    ground_truth[golden_id] = ["drop", "tax_low", "conflict"]

    # --- Oylik ko'rsatkichlar ---------------------------------------------
    rows = []
    for sid, s in subjects.iterrows():
        sec = sector_by_id[s.sector_id]
        _, _, _, _, base_turnover, amp, peak, check = sec
        # base_turnover — rasmiy o'rtacha; mediana = o'rtacha / hajm aralashmasi koeffitsienti.
        median = base_turnover / size_mean_factor()
        base = median * size_mult[s.size_group] * REGION_LEVEL[s.region_id] * rng.lognormal(0, TURNOVER_SIGMA)
        growth = rng.normal(0.004, 0.004)
        amp_s = max(0.0, amp * rng.normal(1.0, 0.15))
        seasonal = 1 + amp_s * np.cos(2 * np.pi * (months - peak) / 12)
        noise = rng.lognormal(0, 0.07, size=n_months)
        turnover = base * seasonal * (1 + growth) ** t_idx * noise

        avg_check = check * rng.lognormal(0, 0.25) * rng.lognormal(0, 0.04, size=n_months)
        tax = rng.normal(1.0, 0.06) + rng.normal(0, 0.03, size=n_months)
        registry = turnover * (1 + rng.normal(0, 0.02, size=n_months))

        kinds = ground_truth.get(int(sid), [])
        k = int(rng.integers(2, 5))
        if int(sid) == golden_id:
            k = 3
        tail = slice(n_months - k, n_months)

        for kind in kinds:
            if kind == "drop":
                f = 0.33 if int(sid) == golden_id else rng.uniform(0.25, 0.5)
                turnover[tail] *= f
                avg_check[tail] *= f ** 0.15  # chek biroz pasayadi, asosiy qisqarish operatsiyalar sonida
            elif kind == "spike":
                turnover[tail] *= rng.uniform(2.2, 3.5)
            elif kind == "tax_low":
                m = 6 if int(sid) == golden_id else int(rng.integers(6, 13))
                tax[n_months - m:] *= 0.66 if int(sid) == golden_id else rng.uniform(0.45, 0.65)
            elif kind == "ops":
                # Aylanma o'zgarmaydi, lekin operatsiyalar mayda va ko'p bo'lib ketadi.
                avg_check[tail] /= rng.uniform(2.5, 4.0)
            elif kind == "conflict":
                if int(sid) == golden_id:
                    registry[tail] = turnover[tail] * 1.12
                else:
                    ratio = rng.uniform(1.5, 2.2) if rng.random() < 0.6 else rng.uniform(0.35, 0.6)
                    registry[tail] = turnover[tail] * ratio
            elif kind == "seasonal":
                inv = slice(n_months - 8, n_months)
                boosted = max(amp_s, 0.3) * 1.4
                turnover[inv] = turnover[inv] / seasonal[inv] * (1 - boosted * np.cos(2 * np.pi * (months[inv] - peak) / 12))

        # Reyestr ikkinchi manba: ziddiyat joylanmagan bo'lsa, aylanma o'zgarishini kuzatib boradi.
        if ("drop" in kinds or "spike" in kinds or "seasonal" in kinds) and "conflict" not in kinds:
            registry = turnover * (1 + rng.normal(0, 0.02, size=n_months))

        tx_count = np.maximum(1, np.round(turnover * 1000 / avg_check))
        start = n_months - int(s.history_months)
        for i in range(start, n_months):
            rows.append([int(sid), periods[i], float(turnover[i]), int(tx_count[i]), float(avg_check[i]),
                         float(tax[i]), float(registry[i])])

    metrics = pd.DataFrame(rows, columns=["subject_id", "period", "turnover", "tx_count", "avg_check",
                                          "tax_index", "registry_turnover"])
    # Post-stratifikatsiya: har bir soha bo'yicha 2025-yil oylik o'rtacha aylanmasi rasmiy qiymatga
    # (yillik hajm / korxonalar soni / 12) teng bo'lishi uchun soha aylanmasi bitta koeffitsientga ko'paytiriladi.
    # Koeffitsient soha ichida bir xil, shuning uchun nisbiy belgilar va xavf baholari o'zgarmaydi.
    sector_of = subjects.set_index("id")["sector_id"]
    metrics["sector_id"] = metrics["subject_id"].map(sector_of)
    in_2025 = metrics["period"].map(lambda p: p.year == 2025)
    targets = {s[0]: s[4] for s in SECTORS}
    for sid, target in targets.items():
        mask = metrics["sector_id"] == sid
        sample_mean = metrics.loc[mask & in_2025, "turnover"].mean()
        if sample_mean and sample_mean > 0:
            factor = target / sample_mean
            metrics.loc[mask, ["turnover", "registry_turnover"]] *= factor
    metrics = metrics.drop(columns=["sector_id"])
    metrics["avg_check"] = metrics["turnover"] * 1000 / metrics["tx_count"]

    # --- Ma'lumot sifati muammolari ---------------------------------------
    dq_ids = rng.choice([i for i in subjects.index if i != golden_id], size=int(n_subjects * 0.11), replace=False)
    drop_rows: list[int] = []
    for sid in dq_ids:
        n_issues = int(rng.choice([1, 2, 3], p=[0.6, 0.28, 0.12]))
        issues = rng.choice(["missing", "invalid", "stale", "logic", "duplicate", "conformity"],
                            size=n_issues, replace=False, p=[0.32, 0.12, 0.16, 0.12, 0.14, 0.14])
        idx = metrics.index[metrics.subject_id == sid]
        if len(idx) < 8:
            continue
        for issue in issues:
            if issue == "missing":
                miss = rng.choice(idx[:-1], size=min(len(idx) - 1, int(rng.integers(2, 10))), replace=False)
                metrics.loc[miss, ["turnover", "tx_count", "avg_check"]] = np.nan
                if rng.random() < 0.5:
                    heavy = rng.choice(idx, size=min(len(idx) // 2, 10), replace=False)
                    metrics.loc[heavy, "tax_index"] = np.nan
            elif issue == "invalid":
                bad = rng.choice(idx, size=int(rng.integers(1, 3)), replace=False)
                metrics.loc[bad, "turnover"] = -metrics.loc[bad, "turnover"].abs()
            elif issue == "stale":
                drop_rows.extend(idx[-int(rng.integers(2, 5)):].tolist())
            elif issue == "logic":
                bad = rng.choice(idx, size=int(rng.integers(1, 4)), replace=False)
                metrics.loc[bad, "turnover"] = 0.0
            elif issue == "duplicate":
                subjects.loc[sid, "duplicate_records"] = int(rng.integers(1, 4))
            elif issue == "conformity":
                subjects.loc[sid, "stir"] = _fake_stir(rng, valid=False)
    metrics = metrics.drop(index=drop_rows).reset_index(drop=True)

    # Soliq manbasi bir oyga kechikkan: oxirgi davr uchun soliq ko'rsatkichi hali kelmagan.
    metrics.loc[metrics.period == periods[-1], "tax_index"] = np.nan

    # Oltin subyekt: kichik to'liqlik va yagonalik kamchiliklari (ishonch yuqoriligicha qoladi).
    g_idx = metrics.index[metrics.subject_id == golden_id]
    metrics.loc[g_idx[5], "avg_check"] = np.nan
    metrics.loc[g_idx[[9, 10]], "registry_turnover"] = np.nan
    metrics.loc[g_idx[-2], "tax_index"] = np.nan
    subjects.loc[golden_id, "duplicate_records"] = 2

    # --- Aloqadorliklar ---------------------------------------------------
    relations = _generate_relations(rng, subjects, ground_truth, golden_id, periods)

    return SyntheticDataset(periods=periods, subjects=subjects.reset_index(drop=True), metrics=metrics,
                            relations=relations, ground_truth=ground_truth)


def _generate_relations(rng, subjects: pd.DataFrame, ground_truth: dict[int, list[str]], golden_id: int,
                        periods: list[date]) -> pd.DataFrame:
    ids = subjects.index.to_numpy()
    by_region = {r: subjects.index[subjects.region_id == r].to_numpy() for r in subjects.region_id.unique()}
    edges: dict[tuple[int, int], tuple[str, float]] = {}

    def add(a: int, b: int, rel: str, w: float):
        if a == b:
            return
        key = (min(a, b), max(a, b))
        if key not in edges or edges[key][1] < w:
            edges[key] = (rel, round(float(w), 2))

    # Oddiy tijorat aloqalari: siyrak tarmoq, asosan hudud ichida.
    for sid in ids:
        n = rng.poisson(0.9)
        for _ in range(n):
            pool = by_region[subjects.at[sid, "region_id"]] if rng.random() < 0.75 else ids
            other = int(rng.choice(pool))
            rel = rng.choice(["supplier", "buyer", "founder", "director", "address"], p=[0.45, 0.4, 0.06, 0.04, 0.05])
            add(int(sid), other, str(rel), rng.uniform(0.15, 0.7))

    # Xavfli klasterlar: anomaliyali subyektlar zich va tuzilmaviy aloqalar bilan bog'langan.
    anom_by_region: dict[str, list[int]] = {}
    for sid in ground_truth:
        if sid == golden_id:
            continue
        anom_by_region.setdefault(subjects.at[sid, "region_id"], []).append(sid)
    cluster_members: list[list[int]] = []
    for region, members in sorted(anom_by_region.items()):
        members = list(members)
        rng.shuffle(members)
        n_clusters = max(1, len(members) // 12)
        for c in range(n_clusters):
            size = int(rng.integers(3, 7))
            group = members[c * size:(c + 1) * size]
            if len(group) < 3:
                continue
            normals = rng.choice(by_region[region], size=2, replace=False).tolist()
            cluster = group + [int(x) for x in normals]
            cluster_members.append(cluster)
            for i, a in enumerate(cluster):
                for b in cluster[i + 1:]:
                    if rng.random() < 0.6:
                        add(a, b, str(rng.choice(["founder", "director", "address"])), rng.uniform(0.6, 0.95))

    # Oltin subyekt: Namangandagi ikki xavfli subyekt bilan tuzilmaviy aloqa.
    strong = {"drop", "spike", "conflict"}
    ng_anom = sorted(s for s in anom_by_region.get("NG", []) if strong & set(ground_truth[s]))
    risky = ng_anom[:2]
    for s, rel in zip(risky, ["founder", "director"]):
        add(golden_id, s, rel, 0.9)
    if len(risky) == 2:
        add(risky[0], risky[1], "address", 0.8)
    ng_normal = [int(x) for x in by_region["NG"] if int(x) not in ground_truth][:3]
    for s, rel in zip(ng_normal, ["supplier", "buyer", "buyer"]):
        add(golden_id, s, rel, 0.35)

    rows = []
    for (a, b), (rel, w) in edges.items():
        since = periods[int(rng.integers(0, len(periods)))]
        rows.append({"source_id": a, "target_id": b, "rel_type": rel, "weight": w, "since": since})
    return pd.DataFrame(rows)
