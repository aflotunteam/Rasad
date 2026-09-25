"""Yagona xato modeli (TZ §19–20)."""

from typing import Any


class ErrorCode:
    AUTH_INVALID = "AUTH_001"
    AUTH_FORBIDDEN = "AUTH_002"
    AUTH_TOKEN = "AUTH_003"
    DATA_NOT_FOUND = "DATA_001"
    DATA_VALIDATION = "DATA_002"
    SUBJECT_NOT_FOUND = "DATA_003"
    MODEL_RULE = "MODEL_001"
    RISK_UNAVAILABLE = "RISK_001"
    IMPORT_FAILED = "IMPORT_001"
    REPORT_FAILED = "REPORT_001"
    SYSTEM = "SYSTEM_001"


class AppError(Exception):
    status_code = 400

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code


class NotFound(AppError):
    status_code = 404

    def __init__(self, message: str = "Ma’lumot topilmadi", code: str = ErrorCode.DATA_NOT_FOUND):
        super().__init__(code, message)


class Forbidden(AppError):
    status_code = 403

    def __init__(self, message: str = "Ruxsat mavjud emas"):
        super().__init__(ErrorCode.AUTH_FORBIDDEN, message)


class Unauthorized(AppError):
    status_code = 401

    def __init__(self, message: str = "Avtorizatsiyadan o‘tilmagan", code: str = ErrorCode.AUTH_TOKEN):
        super().__init__(code, message)
