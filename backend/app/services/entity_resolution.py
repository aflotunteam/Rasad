"""Subyektlarni yagona identifikatsiyalash (TZ §6).

Turli manbalardan kelgan "ABC MCHJ", "ABC МЧЖ", "ABC LLC", "ABC" kabi yozuvlar
STIR, normallashtirilgan nom va manzil bo'yicha bitta ichki subyektga bog'lanadi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}

# Tashkiliy-huquqiy shakllar nomdan olib tashlanadi.
ORG_FORM_TOKENS = {"mchj", "mchzh", "llc", "ltd", "ooo", "xk", "aj", "ao", "oao", "zao", "yatt", "ip",
                   "dk", "duk", "qk", "chp", "xususiy", "korxonasi", "korxona", "firma"}

NAME_THRESHOLD = 92
ADDRESS_THRESHOLD = 80


def transliterate(text: str) -> str:
    return "".join(CYR_TO_LAT.get(ch, ch) for ch in text.lower())


def normalize_name(name: str) -> str:
    t = transliterate(name or "")
    t = re.sub(r"[«»\"'‘’`ʻʼ.,()\-_/]", " ", t)
    tokens = [tok for tok in t.split() if tok and tok not in ORG_FORM_TOKENS]
    return " ".join(tokens)


def normalize_stir(stir: str | None) -> str | None:
    if not stir:
        return None
    digits = re.sub(r"\D", "", str(stir))
    return digits if len(digits) == 9 else None


@dataclass
class SourceRecord:
    source: str
    record_id: str
    name: str
    stir: str | None = None
    address: str | None = None


@dataclass
class ResolvedEntity:
    internal_subject_id: str
    records: list[SourceRecord] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)


def same_entity(a: SourceRecord, b: SourceRecord) -> str | None:
    """Ikki yozuv bitta subyektga tegishli bo'lsa, moslik sababini qaytaradi."""
    sa, sb = normalize_stir(a.stir), normalize_stir(b.stir)
    if sa and sb:
        return "STIR mos keldi" if sa == sb else None
    na, nb = normalize_name(a.name), normalize_name(b.name)
    if not na or not nb:
        return None
    name_score = fuzz.token_sort_ratio(na, nb)
    if name_score < NAME_THRESHOLD:
        return None
    if a.address and b.address:
        addr = fuzz.token_set_ratio(transliterate(a.address), transliterate(b.address))
        if addr < ADDRESS_THRESHOLD:
            return None
        return f"Nom ({name_score:.0f}%) va manzil ({addr:.0f}%) mos keldi"
    return f"Nom mos keldi ({name_score:.0f}%)"


def resolve(records: list[SourceRecord], start_id: int = 1) -> list[ResolvedEntity]:
    """Oddiy union-find: mos kelgan yozuvlar bitta subyektga birlashtiriladi."""
    parent = list(range(len(records)))
    reasons: dict[int, list[str]] = {}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            reason = same_entity(records[i], records[j])
            if reason:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
                reasons.setdefault(find(i), []).append(reason)

    groups: dict[int, list[int]] = {}
    for i in range(len(records)):
        groups.setdefault(find(i), []).append(i)

    out = []
    for n, (root, idx) in enumerate(sorted(groups.items(), key=lambda kv: min(kv[1]))):
        out.append(ResolvedEntity(
            internal_subject_id=f"SUB-{start_id + n:06d}",
            records=[records[i] for i in idx],
            match_reasons=reasons.get(root, []),
        ))
    return out
