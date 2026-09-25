from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import CurrentUser, require
from app.core.errors import AppError, ErrorCode, Forbidden, NotFound
from app.core.responses import ok
from app.models import Report, RiskScore
from app.reports import exporters
from app.reports.builder import build_content, metadata, next_number, validate_params

router = APIRouter(prefix="/reports", tags=["Hisobotlar"])

MEDIA = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


class ReportIn(BaseModel):
    report_type: Literal["subject", "region", "sector", "risk_type", "periodic"]
    params: dict = Field(default_factory=dict)


def _load(db: Session, report_id: int, cu: CurrentUser) -> Report:
    rep = db.scalar(select(Report).options(joinedload(Report.author)).where(Report.id == report_id))
    if rep is None:
        raise NotFound("Hisobot topilmadi")
    if cu.role == "analyst" and rep.created_by != cu.id:
        raise Forbidden("Boshqa foydalanuvchi hisobotini ko‘rishga ruxsat yo‘q")
    return rep


@router.post("")
def create_report(body: ReportIn, cu: CurrentUser = Depends(require("reports")), db: Session = Depends(get_db)):
    title, params = validate_params(db, body.report_type, body.params, cu)
    rs = db.scalar(select(RiskScore).limit(1))
    if rs is None:
        raise AppError(ErrorCode.REPORT_FAILED, "Hisobot uchun tahlil natijalari mavjud emas")
    now = datetime.now(timezone.utc)
    rep = Report(number=next_number(db, now.year), report_type=body.report_type, params=params, title=title,
                 period_start=rs.period_start, period_end=rs.period_end, model_version=rs.model_version,
                 data_version=rs.data_version, created_by=cu.id, created_at=now)
    db.add(rep)
    db.flush()
    db.refresh(rep, ["author"])
    content = build_content(db, rep, cu)
    record(db, cu, "report.create", "report", rep.number, new={"type": rep.report_type, "params": params})
    db.commit()
    return ok({"id": rep.id, "meta": metadata(rep), "content": content})


@router.get("")
def list_reports(limit: int = Query(30, ge=1, le=200), cu: CurrentUser = Depends(require("reports")),
                 db: Session = Depends(get_db)):
    q = select(Report).options(joinedload(Report.author)).order_by(desc(Report.created_at)).limit(limit)
    if cu.role == "analyst":
        q = q.where(Report.created_by == cu.id)
    return ok([{"id": r.id, **metadata(r)} for r in db.scalars(q)])


@router.get("/{report_id}")
def get_report(report_id: int, cu: CurrentUser = Depends(require("reports")), db: Session = Depends(get_db)):
    rep = _load(db, report_id, cu)
    return ok({"id": rep.id, "meta": metadata(rep), "content": build_content(db, rep, cu)})


@router.get("/{report_id}/download")
def download_report(report_id: int, format: Literal["pdf", "xlsx", "csv"] = "pdf",
                    cu: CurrentUser = Depends(require("reports")), db: Session = Depends(get_db)):
    rep = _load(db, report_id, cu)
    meta, content = metadata(rep), build_content(db, rep, cu)
    try:
        data = {"pdf": exporters.to_pdf, "xlsx": exporters.to_xlsx, "csv": exporters.to_csv}[format](meta, content)
    except Exception as exc:  # pragma: no cover - eksport kutubxonasi xatolari
        raise AppError(ErrorCode.REPORT_FAILED, "Hisobotni eksport qilib bo‘lmadi", 500) from exc
    record(db, cu, "report.export", "report", rep.number, new={"format": format})
    db.commit()
    filename = f"{rep.number}_{date.today():%Y%m%d}.{format}"
    return Response(content=data, media_type=MEDIA[format],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
