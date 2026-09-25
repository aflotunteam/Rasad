"""Yagona API javob formati: {"success", "data", "error"} (TZ §19)."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class Envelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorBody | None = None


def ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def fail(code: str, message: str, details: Any = None) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details},
    }


def page(items: list, total: int, page_no: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page_no, "page_size": page_size}
