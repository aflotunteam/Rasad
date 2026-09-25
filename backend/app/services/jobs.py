"""Fon vazifalar (TZ §17): API → QUEUE → WORKER → DATABASE.

MVP da FastAPI BackgroundTasks ishlatiladi; holat jobs jadvalida saqlanadi
(QUEUED → RUNNING → COMPLETED / FAILED). Production da Celery + Redis ga
almashtiriladi, interfeys o'zgarmaydi.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Job

log = logging.getLogger("rasad.jobs")


def create(db: Session, job_type: str, payload: dict) -> Job:
    job = Job(job_type=job_type, status="QUEUED", payload=payload)
    db.add(job)
    db.flush()
    return job


def run(job_id: int, fn: Callable[[Session, Job], dict]) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status, job.started_at, job.progress = "RUNNING", datetime.now(timezone.utc), 5
        db.commit()
        result = fn(db, job)
        job = db.get(Job, job_id)
        job.status, job.progress, job.result = "COMPLETED", 100, result or {}
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - vazifa xatosi saqlanadi, jarayon to'xtamaydi
        db.rollback()
        log.error("Vazifa %s xato bilan tugadi: %s", job_id, traceback.format_exc())
        job = db.get(Job, job_id)
        if job:
            job.status, job.error = "FAILED", str(exc)[:500]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def payload(job: Job) -> dict:
    return {
        "id": job.id, "type": job.job_type, "status": job.status, "progress": job.progress,
        "result": job.result, "error": job.error, "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
