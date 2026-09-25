"""Ma'lumot importi (prompt §23): fayl → tuzilma → moslashtirish → sifat → takrorlar → tasdiq → natija."""

from __future__ import annotations

import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.errors import AppError, ErrorCode
from app.models import DataLineage, DataSource, ImportJob, Job, Subject
from app.services.data_quality import assess_rows
from app.services.pipeline import PIPELINE_VERSION

STORAGE = BACKEND_DIR / "storage"
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000

TARGET_FIELDS = {
    "stir": {"label": "STIR", "required": True, "aliases": ["stir", "inn", "tin", "soliq raqami", "стир"]},
    "period": {"label": "Davr (oy)", "required": True, "aliases": ["period", "davr", "oy", "sana", "date", "month"]},
    "turnover": {"label": "Aylanma, mln so‘m", "required": True, "aliases": ["turnover", "aylanma", "oborot", "revenue"]},
    "tx_count": {"label": "Operatsiyalar soni", "required": True, "aliases": ["tx_count", "operatsiyalar", "count", "soni"]},
    "avg_check": {"label": "O‘rtacha chek, ming so‘m", "required": False, "aliases": ["avg_check", "orta chek", "chek"]},
    "tax_index": {"label": "Soliq yuklamasi indeksi", "required": False, "aliases": ["tax_index", "soliq", "tax"]},
}
REQUIRED = [k for k, v in TARGET_FIELDS.items() if v["required"]]


def _path(job: ImportJob) -> Path:
    return Path(job.storage_path)


def read_frame(raw: bytes, fmt: str) -> pd.DataFrame:
    try:
        if fmt == "csv":
            text = raw.decode("utf-8-sig", errors="replace")
            sep = ";" if text.count(";") > text.count(",") else ","
            return pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False, na_values=[""])
        if fmt == "xlsx":
            return pd.read_excel(io.BytesIO(raw), dtype=str)
        if fmt == "json":
            data = json.loads(raw.decode("utf-8-sig"))
            if isinstance(data, dict):
                data = data.get("rows") or data.get("data") or []
            return pd.DataFrame(data).astype(str).replace({"None": None, "nan": None})
    except Exception as exc:
        raise AppError(ErrorCode.IMPORT_FAILED, "Faylni o‘qib bo‘lmadi: tuzilma noto‘g‘ri", 422) from exc
    raise AppError(ErrorCode.IMPORT_FAILED, "Qo‘llab-quvvatlanmaydigan format. CSV, XLSX yoki JSON yuklang", 422)


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    norm = {c: re.sub(r"[^a-z0-9а-я‘' ]", " ", c.lower()).strip() for c in columns}
    for field, spec in TARGET_FIELDS.items():
        best = None
        for alias in spec["aliases"]:
            hit = process.extractOne(alias, norm, scorer=fuzz.WRatio)
            if hit and hit[1] >= 85 and (best is None or hit[1] > best[1]):
                best = hit
        out[field] = best[2] if best else None
    return out


def create(db: Session, filename: str, raw: bytes, user_id: int, data_source_id: int | None) -> ImportJob:
    if len(raw) > MAX_BYTES:
        raise AppError(ErrorCode.IMPORT_FAILED, "Fayl hajmi 10 MB dan oshmasligi kerak", 413)
    fmt = Path(filename).suffix.lower().lstrip(".")
    df = read_frame(raw, fmt)
    if df.empty or len(df.columns) == 0:
        raise AppError(ErrorCode.IMPORT_FAILED, "Faylda ma’lumot topilmadi", 422)
    if len(df) > MAX_ROWS:
        raise AppError(ErrorCode.IMPORT_FAILED, f"Qatorlar soni {MAX_ROWS} dan oshmasligi kerak", 413)
    if data_source_id is not None and db.get(DataSource, data_source_id) is None:
        raise AppError(ErrorCode.DATA_VALIDATION, "Ma’lumot manbasi topilmadi")
    job = ImportJob(filename=Path(filename).name[:255], file_format=fmt, data_source_id=data_source_id,
                    stage="structure", status="QUEUED", total_rows=len(df), columns=[str(c) for c in df.columns],
                    mapping=suggest_mapping([str(c) for c in df.columns]), created_by=user_id)
    db.add(job)
    db.flush()
    folder = STORAGE / "imports"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{job.id:06d}.{fmt}"
    path.write_bytes(raw)
    job.storage_path = str(path)
    return job


def _mapped(job: ImportJob) -> pd.DataFrame:
    df = read_frame(_path(job).read_bytes(), job.file_format)
    cols = {src: tgt for tgt, src in job.mapping.items() if src}
    out = df[list(cols)].rename(columns=cols)
    for c in ("turnover", "tx_count", "avg_check", "tax_index"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c].astype(str).str.replace(",", ".").str.replace(" ", ""), errors="coerce") \
                .where(out[c].notna())
    if "stir" in out.columns:
        out["stir"] = out["stir"].astype(str).str.replace(r"\D", "", regex=True)
    return out


def set_mapping(job: ImportJob, mapping: dict[str, str | None]) -> None:
    unknown = [src for src in mapping.values() if src and src not in job.columns]
    if unknown:
        raise AppError(ErrorCode.IMPORT_FAILED, f"Faylda bunday ustun yo‘q: {', '.join(unknown)}", 422)
    missing = [TARGET_FIELDS[f]["label"] for f in REQUIRED if not mapping.get(f)]
    if missing:
        raise AppError(ErrorCode.IMPORT_FAILED, f"Majburiy maydonlar moslashtirilmagan: {', '.join(missing)}", 422)
    job.mapping = {k: mapping.get(k) for k in TARGET_FIELDS}
    job.stage = "mapped"


def validate(db: Session, job: ImportJob, today: date | None = None) -> dict:
    df = _mapped(job)
    res = assess_rows(df, [f for f in REQUIRED if f in df.columns], today=today)
    known = set(db.scalars(select(Subject.stir)))
    unknown_rows = [int(i) for i in df.index[~df["stir"].isin(known)]] if "stir" in df.columns else []
    errors = []
    for i, msgs in sorted(res["row_errors"].items()):
        errors.append({"row": i + 2, "messages": msgs})  # 1-qator sarlavha
    rejected = set(res["row_errors"])
    duplicates = set(res["duplicates"]) - rejected
    job.dq = {"score": res["score"], "dimensions": res["dimensions"],
              "matched_subjects": int(len(df) - len(unknown_rows)), "unknown_stir": len(unknown_rows)}
    job.errors = errors[:200]
    job.rejected = len(rejected)
    job.duplicates = len(duplicates)
    job.accepted = int(len(df) - len(rejected) - len(duplicates))
    job.stage = "validated"
    return import_payload(job)


def confirm_worker(import_id: int):
    def work(db: Session, job: Job) -> dict:
        imp = db.get(ImportJob, import_id)
        imp.status = "RUNNING"
        db.commit()
        df = _mapped(imp)
        bad = {e["row"] - 2 for e in imp.errors}
        dup = set(df.index[df.duplicated(keep="first")])
        accepted = df.drop(index=[i for i in df.index if i in bad or i in dup])
        raw_dir = STORAGE / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_file = raw_dir / f"import_{imp.id:06d}.json"
        raw_file.write_text(accepted.to_json(orient="records", force_ascii=False, date_format="iso"), encoding="utf-8")
        now = datetime.now(timezone.utc)
        imp.status, imp.stage, imp.finished_at = "COMPLETED", "done", now
        if imp.data_source_id:
            ds = db.get(DataSource, imp.data_source_id)
            ds.rows += len(accepted)
            ds.rejected += imp.rejected
            ds.last_load_at = now
            ds.quality_score = imp.dq.get("score")
            if ds.status in ("delayed", "error"):
                ds.status, ds.last_error = "active", None
        for step in ("ingestion", "schema_validation", "data_quality", "deduplication", "raw_storage"):
            db.add(DataLineage(source_id=imp.data_source_id, source_record_id=f"import/{imp.id}/{imp.filename}",
                               target_table="raw_storage", target_record_id=raw_file.name, transformation=step,
                               pipeline_version=PIPELINE_VERSION))
        db.commit()
        return {"import_id": imp.id, "accepted": len(accepted), "rejected": imp.rejected,
                "duplicates": imp.duplicates, "raw_file": raw_file.name}

    return work


def import_payload(job: ImportJob, preview: bool = False) -> dict:
    out = {
        "id": job.id, "filename": job.filename, "format": job.file_format, "stage": job.stage,
        "status": job.status, "total_rows": job.total_rows, "accepted": job.accepted, "rejected": job.rejected,
        "duplicates": job.duplicates, "columns": job.columns, "mapping": job.mapping, "dq": job.dq,
        "errors": job.errors, "data_source_id": job.data_source_id, "created_at": job.created_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "target_fields": {k: {"label": v["label"], "required": v["required"]} for k, v in TARGET_FIELDS.items()},
    }
    if preview and job.storage_path:
        df = read_frame(_path(job).read_bytes(), job.file_format).head(8)
        out["preview"] = df.astype(object).where(df.notna(), None).to_dict(orient="records")
    return out
