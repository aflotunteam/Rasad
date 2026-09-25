"""Audit jurnaliga yozish (TZ §23). Jurnal faqat to'ldiriladi."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.models import AuditLog


def record(
    db: Session,
    cu: CurrentUser | None,
    action: str,
    object_type: str,
    object_id: str | int | None = None,
    old: Any = None,
    new: Any = None,
    *,
    username: str | None = None,
    ip: str | None = None,
    session_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=cu.id if cu else None,
        username=cu.user.username if cu else (username or "anonim"),
        action=action,
        object_type=object_type,
        object_id=None if object_id is None else str(object_id),
        old_value=old,
        new_value=new,
        ip=cu.ip if cu else ip,
        session_id=cu.session_id if cu else session_id,
    )
    db.add(entry)
    return entry
