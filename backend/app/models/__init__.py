"""RASAD ma'lumotlar modeli.

Sxema SQLite da ishlaydi, lekin turlar PostgreSQL ga ko'chirishga mos tanlangan
(JSON, timezone bilan DateTime, aniq uzunlikdagi String).
"""

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TS = DateTime(timezone=True)


# --- Ma'lumotnomalar -------------------------------------------------------


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    short_name: Mapped[str] = mapped_column(String(32))
    geo_key: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str] = mapped_column(String(32), default="building")


# --- Foydalanuvchilar ------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))  # admin | analyst | manager | auditor
    region_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    organization: Mapped[str] = mapped_column(String(128), default="Namoyish tashkiloti")
    password_hash: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# --- Subyektlar va ko'rsatkichlar -----------------------------------------


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # SUB-000125
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), index=True)
    sector_id: Mapped[str] = mapped_column(ForeignKey("sectors.id"), index=True)
    size_group: Mapped[str] = mapped_column(String(16))  # small | medium | large
    stir: Mapped[str] = mapped_column(String(9))  # sintetik, real STIR emas
    org_form: Mapped[str] = mapped_column(String(16), default="MCHJ")
    registered_at: Mapped[date] = mapped_column(Date)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)  # Entity Resolution birlashtirgan yozuvlar
    history_months: Mapped[int] = mapped_column(Integer, default=24)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    region: Mapped[Region] = relationship()
    sector: Mapped[Sector] = relationship()
    risk: Mapped["RiskScore | None"] = relationship(back_populates="subject", uselist=False)


class MonthlyMetric(Base):
    __tablename__ = "monthly_metrics"
    __table_args__ = (UniqueConstraint("subject_id", "period", name="uq_metric_subject_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    period: Mapped[date] = mapped_column(Date, index=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)  # mln so'm
    tx_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_check: Mapped[float | None] = mapped_column(Float, nullable=True)  # ming so'm
    tax_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    registry_turnover: Mapped[float | None] = mapped_column(Float, nullable=True)  # 2-manba
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    rel_type: Mapped[str] = mapped_column(String(32))
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    since: Mapped[date | None] = mapped_column(Date, nullable=True)


# --- Xavf natijalari -------------------------------------------------------


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), unique=True, index=True
    )
    score: Mapped[float] = mapped_column(Float, index=True)
    confidence: Mapped[str] = mapped_column(String(8))  # high | medium | low
    confidence_value: Mapped[float] = mapped_column(Float)
    dq_score: Mapped[float] = mapped_column(Float, index=True)
    dq_dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    primary_risk_type: Mapped[str] = mapped_column(String(4), index=True)
    risk_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    components: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    expert_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    model_version: Mapped[str] = mapped_column(String(32))
    data_version: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    computed_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    subject: Mapped[Subject] = relationship(back_populates="risk")
    factors: Mapped[list["RiskFactor"]] = relationship(
        back_populates="risk_score", order_by="RiskFactor.rank", cascade="all, delete-orphan"
    )


class RiskFactor(Base):
    """Xavf sababining standart formati (TZ §16)."""

    __tablename__ = "risk_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_score_id: Mapped[int] = mapped_column(ForeignKey("risk_scores.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    feature: Mapped[str] = mapped_column(String(48))
    factor: Mapped[str] = mapped_column(String(96))
    risk_type: Mapped[str] = mapped_column(String(4))
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(16), default="%")
    deviation: Mapped[str] = mapped_column(String(8))  # high | medium | low
    impact: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))

    risk_score: Mapped[RiskScore] = relationship(back_populates="factors")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), index=True)
    risk_type: Mapped[str] = mapped_column(String(4))
    severity: Mapped[str] = mapped_column(String(8))  # high | medium | low
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    analyst_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    subject: Mapped[Subject] = relationship()
    analyst: Mapped[User | None] = relationship()


class ExpertDecision(Base):
    __tablename__ = "expert_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24))  # confirmed | rejected | need_info | sent_review
    comment: Mapped[str] = mapped_column(Text)
    score_at_decision: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    user: Mapped[User] = relationship()


# --- Ma'lumot manbalari va import -----------------------------------------


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(16))  # file | api | db
    status: Mapped[str] = mapped_column(String(16))  # active | delayed | error | disabled
    description: Mapped[str] = mapped_column(Text, default="")
    last_load_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_format: Mapped[str] = mapped_column(String(8))
    stage: Mapped[str] = mapped_column(String(24), default="uploaded")
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[list[str]] = mapped_column(JSON, default=list)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dq: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    storage_path: Mapped[str] = mapped_column(String(512), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class DataLineage(Base):
    """Ma'lumot kelib chiqishi (TZ §7)."""

    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_table: Mapped[str] = mapped_column(String(64))
    target_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transformation: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    pipeline_version: Mapped[str] = mapped_column(String(32))


# --- Belgilar va modellar reestri -----------------------------------------


class FeatureRegistry(Base):
    __tablename__ = "feature_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    formula: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("model_key", "version", name="uq_model_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_key: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(16))
    algorithm: Mapped[str] = mapped_column(String(128))
    training_dataset: Mapped[str] = mapped_column(String(128))
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    threshold: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    drift: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16))  # DRAFT | TESTING | APPROVED | ACTIVE | ARCHIVED
    created_by: Mapped[str] = mapped_column(String(64))
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


# --- Hisobotlar, fon vazifalar, sozlamalar, audit -------------------------


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    report_type: Mapped[str] = mapped_column(String(16))  # subject | region | sector | risk_type | periodic
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    title: Mapped[str] = mapped_column(String(255))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    model_version: Mapped[str] = mapped_column(String(32))
    data_version: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    author: Mapped[User] = relationship()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")  # QUEUED | RUNNING | COMPLETED | FAILED
    progress: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuditLog(Base):
    """Audit jurnali (TZ §23). Faqat qo'shiladi: API orqali o'zgartirilmaydi."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_at", "at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(48), index=True)
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
