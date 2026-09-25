from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.db import get_db
from app.core.deps import PERMISSIONS, ROLE_LABELS, CurrentUser, client_ip, get_current_user
from app.core.errors import AppError, ErrorCode
from app.core.responses import ok
from app.core.security import create_token, verify_password
from app.models import Region, User

router = APIRouter(prefix="/auth", tags=["Avtorizatsiya"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def user_payload(db: Session, u: User) -> dict:
    region = db.get(Region, u.region_id) if u.region_id else None
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "role_label": ROLE_LABELS.get(u.role, u.role),
        "region_id": u.region_id,
        "region_name": region.name if region else None,
        "organization": u.organization,
        "permissions": sorted(PERMISSIONS.get(u.role, set())),
    }


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    ip = client_ip(request)
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        record(db, None, "auth.login_failed", "user", body.username, username=body.username[:64], ip=ip)
        db.commit()
        raise AppError(ErrorCode.AUTH_INVALID, "Login yoki parol noto‘g‘ri", 401)
    token, sid, expires = create_token(user.id, user.role)
    user.last_login_at = datetime.now(timezone.utc)
    record(db, None, "auth.login", "user", user.id, username=user.username, ip=ip, session_id=sid)
    db.commit()
    return ok({"token": token, "expires_at": expires.isoformat(), "user": user_payload(db, user)})


@router.get("/me")
def me(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(user_payload(db, cu.user))


@router.post("/logout")
def logout(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    record(db, cu, "auth.logout", "user", cu.id)
    db.commit()
    return ok({"logged_out": True})
