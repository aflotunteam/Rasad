"""SI javobini tekshirish (prompt §16): model faqat berilgan natijalarni qayta ifodalashi mumkin.

Rad etish sabablari:
- matnda kiruvchi ma'lumotda yo'q son bor (o'ylab topilgan statistika);
- ayb yoki huquqiy xulosa bildiruvchi so'zlar;
- kirill yozuvi (interfeys faqat lotin yozuvida);
- tuzilma talabga javob bermaydi.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

FORBIDDEN = re.compile(
    r"\b(aybdor\w*|jinoyat\w*|firibgar\w*|qonunbuzar\w*|huquqbuzar\w*|noqonuniy\w*|jazola\w*|jinoiy\w*)",
    re.IGNORECASE,
)
CYRILLIC = re.compile(f"[{chr(0x0400)}-{chr(0x04FF)}]")

# Son sifatida hisoblanmaydigan identifikatorlar: xavf turi kodlari, subyekt kodi, versiyalar, manba nomlari.
IDENTIFIERS = re.compile(
    r"\bR0\d\b|SUB-\d+|\bv?\d+\.\d+\.\d+\b|synthetic_demo_\w+|rasad-[\w.-]+|\b\d{4}-\d{2}(-\d{2})?\b",
    re.IGNORECASE,
)
# Minglik bo'shliq bilan yozilgan sonlar ("4 812", "5 000") bitta son sifatida o'qiladi.
# Oddiy bo'shliq, NBSP (U+00A0) va tor NBSP (U+202F): minglik ajratgichlar.
SPACES = " " + chr(0x00A0) + chr(0x202F)
NUMBER = re.compile(rf"(?<![\w])[-{chr(0x2212)}+]?(?:\d{{1,3}}(?:[{SPACES}]\d{{3}})+|\d+)(?:[.,]\d+)?")

# Kichik butun sonlar tartib va sanoq uchun ("uchta omil", "2 ta signal") ruxsat etiladi.
SMALL_INTS = set(range(0, 11)) | {100}
TOLERANCE = 0.051


def _to_float(token: str) -> float:
    t = re.sub(f"[{SPACES}]", "", token).replace(chr(0x2212), "-").replace("+", "")
    return abs(float(t.replace(",", ".")))


def numbers_in(text: str) -> list[float]:
    cleaned = IDENTIFIERS.sub(" ", text)
    return [_to_float(t) for t in NUMBER.findall(cleaned)]


def allowed_numbers(values: Iterable[float | int | None]) -> set[float]:
    out: set[float] = set()
    for v in values:
        if v is None:
            continue
        out.add(abs(float(v)))
    return out


def check(paragraphs: list[str], allowed: set[float]) -> str | None:
    """Muammo topilsa, uning tavsifini qaytaradi; hammasi joyida bo'lsa, None."""
    if not paragraphs or len(paragraphs) > 6:
        return "Izoh tuzilmasi talabga mos emas"
    for p in paragraphs:
        if not p.strip() or len(p) > 1500:
            return "Izoh bo‘limi bo‘sh yoki juda uzun"
        if CYRILLIC.search(p):
            return "Izohda kirill yozuvi bor"
        m = FORBIDDEN.search(p)
        if m:
            return f"Izohda ayb yoki huquqiy xulosa bildiruvchi so‘z bor: «{m.group(0)}»"
        for x in numbers_in(p):
            if x.is_integer() and int(x) in SMALL_INTS:
                continue
            if not any(abs(x - a) < TOLERANCE for a in allowed):
                return f"Izohda hisoblangan natijalarda yo‘q son bor: {x:g}"
    return None
