import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import ErrorCode, Unauthorized


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    s = get_settings()
    session_id = secrets.token_hex(8)
    expires = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": str(user_id), "role": role, "sid": session_id, "exp": expires},
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    return token, session_id, expires


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        raise Unauthorized("Sessiya muddati tugagan yoki token noto‘g‘ri", ErrorCode.AUTH_TOKEN) from exc
