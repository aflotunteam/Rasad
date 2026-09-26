"""Ma'lumot manbalari, import va fon vazifalar."""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.errors import AppError, ErrorCode, NotFound
from app.core.responses import ok
from app.models import AppSetting, DataLineage, DataSource, ImportJob, Job
from app.services import imports as imp_svc
from app.services import jobs as job_svc
from app.services import pipeline

router = APIRouter(tags=["Ma'lumot manbalari"])


def source_payload(s: DataSource) -> dict:
    return {
        "id": s.id, "code": s.code, "name": s.name, "type": s.source_type, "status": s.status,
        "description": s.description, "last_load_at": s.last_load_at.isoformat() if s.last_load_at else None,
        "rows": s.rows, "rejected": s.rejected, "quality_score": s.quality_score, "last_error": s.last_error,
    }


@router.get("/data-sources")
def list_sources(cu: CurrentUser = Depends(require("data_sources")), db: Session = Depends(get_db)):
    return ok([source_payload(s) for s in db.scalars(select(DataSource).order_by(DataSource.id))])


@router.get("/data-sources/calibration")
def calibration(cu: CurrentUser = Depends(require("dashboard")), db: Session = Depends(get_db)):
    """Sintetik tanlanma qaysi rasmiy agregat statistikaga moslashtirilgani va tekshiruv natijasi."""
    row = db.get(AppSetting, "calibration")
    if row is None:
        raise NotFound("Kalibrlash ma’lumoti topilmadi: bazani qayta seed qiling")
    return ok(row.value)


@router.get("/data-sources/{source_id}/lineage")
def lineage(source_id: int, cu: CurrentUser = Depends(require("data_sources")), db: Session = Depends(get_db)):
    rows = db.scalars(select(DataLineage).where(DataLineage.source_id == source_id)
                      .order_by(desc(DataLineage.processed_at), DataLineage.id).limit(100))
    return ok([{"id": r.id, "source_record_id": r.source_record_id, "target_table": r.target_table,
                "target_record_id": r.target_record_id, "transformation": r.transformation,
                "processed_at": r.processed_at.isoformat(), "pipeline_version": r.pipeline_version} for r in rows])


# --- Import ustasi ----------------------------------------------------------


def _import(db: Session, import_id: int) -> ImportJob:
    job = db.get(ImportJob, import_id)
    if job is None:
        raise NotFound("Import topilmadi")
    return job


@router.get("/imports")
def list_imports(cu: CurrentUser = Depends(require("imports")), db: Session = Depends(get_db)):
    rows = db.scalars(select(ImportJob).order_by(desc(ImportJob.created_at)).limit(30))
    return ok([imp_svc.import_payload(j) for j in rows])


@router.post("/imports")
async def upload(file: UploadFile = File(...), data_source_id: int | None = Form(None),
                 cu: CurrentUser = Depends(require("imports")), db: Session = Depends(get_db)):
    raw = await file.read()
    job = imp_svc.create(db, file.filename or "fayl", raw, cu.id, data_source_id)
    record(db, cu, "import.upload", "import", job.id, new={"file": job.filename, "rows": job.total_rows})
    db.commit()
    return ok(imp_svc.import_payload(job, preview=True))


@router.get("/imports/{import_id}")
def get_import(import_id: int, cu: CurrentUser = Depends(require("imports")), db: Session = Depends(get_db)):
    return ok(imp_svc.import_payload(_import(db, import_id), preview=True))


class MappingIn(BaseModel):
    mapping: dict[str, str | None]


@router.post("/imports/{import_id}/mapping")
def set_mapping(import_id: int, body: MappingIn, cu: CurrentUser = Depends(require("imports")),
                db: Session = Depends(get_db)):
    job = _import(db, import_id)
    imp_svc.set_mapping(job, body.mapping)
    db.commit()
    return ok(imp_svc.import_payload(job))


@router.post("/imports/{import_id}/validate")
def validate(import_id: int, cu: CurrentUser = Depends(require("imports")), db: Session = Depends(get_db)):
    job = _import(db, import_id)
    if job.stage not in ("mapped", "validated"):
        raise AppError(ErrorCode.IMPORT_FAILED, "Avval ustunlarni moslashtiring")
    data = imp_svc.validate(db, job, today=date.today())
    db.commit()
    return ok(data)


@router.post("/imports/{import_id}/confirm")
def confirm(import_id: int, bg: BackgroundTasks, cu: CurrentUser = Depends(require("imports")),
            db: Session = Depends(get_db)):
    job = _import(db, import_id)
    if job.stage != "validated":
        raise AppError(ErrorCode.IMPORT_FAILED, "Import tasdig‘idan oldin sifat tekshiruvi bajarilishi kerak")
    task = job_svc.create(db, "import", {"import_id": job.id})
    job.status = "QUEUED"
    record(db, cu, "import.confirm", "import", job.id,
           new={"accepted": job.accepted, "rejected": job.rejected, "duplicates": job.duplicates})
    db.commit()
    bg.add_task(job_svc.run, task.id, imp_svc.confirm_worker(job.id))
    return ok({"job": job_svc.payload(task), "import": imp_svc.import_payload(job)})


# --- Fon vazifalar ----------------------------------------------------------


@router.get("/jobs")
def list_jobs(cu: CurrentUser = Depends(require("data_sources")), db: Session = Depends(get_db)):
    return ok([job_svc.payload(j) for j in db.scalars(select(Job).order_by(desc(Job.created_at)).limit(30))])


@router.get("/jobs/{job_id}")
def get_job(job_id: int, cu: CurrentUser = Depends(require("dashboard")), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise NotFound("Vazifa topilmadi")
    return ok(job_svc.payload(job))


@router.post("/jobs/recompute")
def recompute(bg: BackgroundTasks, cu: CurrentUser = Depends(require("settings.write")),
              db: Session = Depends(get_db)):
    task = job_svc.create(db, "recompute", {"requested_by": cu.user.username})
    record(db, cu, "model.recompute", "model", "rasad-risk")
    db.commit()
    bg.add_task(job_svc.run, task.id, lambda s, _job: pipeline.recompute(s))
    return ok(job_svc.payload(task))
