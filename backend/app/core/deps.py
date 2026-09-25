"""Autentifikatsiya, rol (RBAC) va atribut (ABAC) tekshiruvlari (TZ §21)."""

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models import User

bearer = HTTPBearer(auto_error=False)

ROLE_LABELS = {
    "admin": "Administrator",
    "analyst": "Tahlilchi",
    "manager": "Rahbar",
    "auditor": "Auditor",
}

# Ruxsatlar matritsasi: frontend ham shu ro'yxatdan foydalanadi.
PERMISSIONS: dict[str, set[str]] = {
    "admin": {"dashboard", "subjects", "subjects.stir", "decisions.write", "alerts.write", "reports",
              "data_sources", "imports", "models.read", "models.write", "audit", "users", "settings",
              "settings.write"},
    "analyst": {"dashboard", "subjects", "subjects.stir", "decisions.write", "alerts.write", "reports",
                "data_sources", "imports", "models.read"},
    "manager": {"dashboard", "subjects", "reports", "alerts.read", "models.read"},
    "auditor": {"dashboard", "subjects", "reports", "data_sources", "models.read", "audit", "settings"},
}
for _role in PERMISSIONS:
    PERMISSIONS[_role].add("alerts.read")


@dataclass
class CurrentUser:
    user: User
    session_id: str
    ip: str | None

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def region_scope(self) -> str | None:
        """Tahlilchi faqat o'z hududi ma'lumotlarini ko'radi."""
        return self.user.region_id if self.user.role == "analyst" else None

    def can(self, perm: str) -> bool:
        return perm in PERMISSIONS.get(self.user.role, set())


def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    # Token faqat Authorization sarlavhasidan olinadi: URL dagi token loglarda qolib ketadi.
    if creds is None or not creds.credentials:
        raise Unauthorized()
    payload = decode_token(creds.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise Unauthorized("Foydalanuvchi faol emas")
    return CurrentUser(user=user, session_id=payload.get("sid", ""), ip=client_ip(request))


def require(perm: str):
    def checker(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not cu.can(perm):
            raise Forbidden()
        return cu

    return checker
