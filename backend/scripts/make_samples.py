"""Import ustasi uchun sintetik namuna fayllar (data/samples/).

Ishga tushirish (backend papkasidan, seed dan keyin):
    python -m scripts.make_samples

Fayllarda qasddan qo'yilgan xatolar bor: noto'g'ri STIR, kelajakdagi sana,
manfiy aylanma va takroriy qator. Bu import sifat tekshiruvini ko'rsatish uchun.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import PROJECT_DIR  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models import Subject  # noqa: E402


def main() -> None:
    out = PROJECT_DIR / "data" / "samples"
    out.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    stirs = [s for (s,) in db.execute(select(Subject.stir).where(Subject.region_id == "NG").order_by(Subject.id).limit(40))]
    db.close()

    rows = []
    for i, stir in enumerate(stirs):
        rows.append({"STIR": stir, "Davr": "2026-08-01", "Aylanma": round(80 + i * 7.3, 1),
                     "Operatsiyalar": 300 + i * 11, "Soliq indeksi": round(0.95 + (i % 5) * 0.02, 3)})
    rows.append(dict(rows[3]))                                                     # takroriy
    rows.append({**rows[5], "STIR": "12345"})                                      # noto'g'ri STIR
    rows.append({**rows[7], "Davr": "2027-01-01"})                                 # kelajakdagi sana
    rows.append({**rows[9], "Aylanma": -42.0})                                     # manfiy aylanma
    rows.append({**rows[11], "Operatsiyalar": None})                               # bo'sh majburiy maydon

    df = pd.DataFrame(rows)
    df.to_csv(out / "namuna_tranzaksiyalar.csv", sep=";", index=False, decimal=",", encoding="utf-8-sig")
    df.to_excel(out / "namuna_tranzaksiyalar.xlsx", index=False)
    (out / "namuna_tranzaksiyalar.json").write_text(
        json.dumps({"rows": json.loads(df.to_json(orient="records", force_ascii=False))}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# Namuna import fayllari\n\nSintetik ma’lumot. Qasddan qo‘yilgan xatolar: 1 ta takroriy qator, noto‘g‘ri STIR, "
        "kelajakdagi sana, manfiy aylanma va bo‘sh majburiy maydon.\n", encoding="utf-8")
    print(f"✓ {len(df)} qator: {out}")


if __name__ == "__main__":
    main()
