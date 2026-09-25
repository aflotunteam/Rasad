"""Sun'iy intellekt izohi (prompt §16).

Matn faqat allaqachon hisoblangan strukturali natijalardan shablon asosida
yasaladi. Bu yerda yangi raqam, manba yoki fakt yaratilmaydi: har bir son
risk_scores va risk_factors jadvallaridan olinadi. Til modeli ulanmagan.
"""

from __future__ import annotations

from data_gen.reference import RISK_TYPES

LEVEL_TEXT = {"high": "yuqori", "medium": "o‘rta", "low": "past"}
DEVIATION_TEXT = {"high": "kuchli", "medium": "sezilarli", "low": "kichik"}
ORDINALS = ["Eng katta ta’sir ko‘rsatgan omil", "Ikkinchi omil", "Uchinchi omil"]
RISK_TYPE_NAMES = {c: n for c, n, _, _ in RISK_TYPES}

DISCLAIMER = "Mazkur baho avtomatik tahlil natijasi bo‘lib, yakuniy huquqiy xulosa hisoblanmaydi."
BASIS_NOTE = "Sun’iy intellekt izohi hisoblangan tahliliy natijalar asosida shakllantirilgan."


def _lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def fmt(v: float | None, digits: int = 1, signed: bool = False) -> str:
    if v is None:
        return "ma’lumot mavjud emas"
    s = f"{v:+.{digits}f}" if signed else f"{v:.{digits}f}"
    return s.replace(".", ",").replace("-", "−")


def fmt_value(v: float | None, unit: str) -> str:
    if v is None:
        return "ma’lumot mavjud emas"
    if unit == "%":
        return f"{fmt(v, 1)}%"
    if unit == "ta":
        return f"{int(v)} ta"
    if unit == "persentil":
        return f"{fmt(v, 1)}-persentil"
    return fmt(v, 3)


def build(code: str, risk: dict, factors: list[dict], dq_low_threshold: float = 60.0) -> dict:
    level = LEVEL_TEXT.get(risk["level"], risk["level"])
    conf = LEVEL_TEXT.get(risk["confidence"], risk["confidence"])
    paragraphs = [
        f"{code} subyekti uchun hisoblangan analitik xavf bahosi {fmt(risk['score'])}/100 "
        f"({level} daraja). Ishonch darajasi: {conf}. Ma’lumot sifati: {fmt(risk['dq_score'])}/100."
    ]

    top = [f for f in factors if f["impact"] > 0][:3]
    sentences = []
    for i, f in enumerate(top):
        rng = ""
        if f["baseline_low"] is not None and f["baseline_high"] is not None:
            rng = (f", soha bo‘yicha kutilgan oraliq {fmt_value(f['baseline_low'], f['unit'])} … "
                   f"{fmt_value(f['baseline_high'], f['unit'])}")
        sentences.append(
            f"{ORDINALS[i]} — {_lower_first(f['factor'])}: joriy qiymat {fmt_value(f['current_value'], f['unit'])}{rng}. "
            f"Og‘ish {DEVIATION_TEXT.get(f['deviation'], f['deviation'])}, xavf bahosiga ta’siri "
            f"{fmt(f['impact'], 1, signed=True)} ball (manba: {f['source']})."
        )
    if sentences:
        paragraphs.append(" ".join(sentences))

    types = risk.get("risk_types") or []
    primary = risk["primary_risk_type"]
    if primary == "R08" and len(types) >= 2:
        names = ", ".join(f"{RISK_TYPE_NAMES.get(t, t).lower()} ({t})" for t in types[:4])
        paragraphs.append(
            f"Bir vaqtning o‘zida bir nechta xavf signali kuzatilgani sababli holat «Kompleks xavf» (R08) "
            f"turiga kiritilgan. Kuzatilgan signallar: {names}."
        )
    elif primary:
        paragraphs.append(f"Asosiy xavf turi: {RISK_TYPE_NAMES.get(primary, primary)} ({primary}).")

    if risk["dq_score"] < dq_low_threshold:
        paragraphs.append("Ma’lumot sifati past. Natijani ehtiyotkorlik bilan talqin qilish talab etiladi.")
    elif risk["confidence"] == "low":
        paragraphs.append("Ishonch darajasi past: tarix qisqa yoki manbalar yetarli emas. "
                          "Natijani qo‘shimcha ma’lumot bilan tekshirish tavsiya etiladi.")

    paragraphs.append("Yakuniy qaror vakolatli ekspert tomonidan qabul qilinadi.")
    return {
        "paragraphs": paragraphs,
        "basis_note": BASIS_NOTE,
        "disclaimer": DISCLAIMER,
        "generator": "shablon asosidagi izoh (til modeli ishlatilmagan)",
        "inputs": {"score": risk["score"], "confidence": risk["confidence"], "dq_score": risk["dq_score"],
                   "factors": [f["feature"] for f in top], "model_version": risk["model_version"]},
    }
