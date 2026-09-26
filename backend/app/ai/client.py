"""Anthropic klienti va xizmat holati.

Kalit faqat `.env` dagi ANTHROPIC_API_KEY dan olinadi va hech qachon logga yoki API javobiga chiqmaydi.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic

from app.core.config import get_settings

MODEL_LABELS = {
    "claude-sonnet-5": "Claude Sonnet 5",
    "claude-opus-5": "Claude Opus 5",
    "claude-haiku-4-5": "Claude Haiku 4.5",
}

_client: anthropic.Anthropic | None = None
_client_key: str | None = None
_lock = threading.Lock()


@dataclass
class ServiceState:
    calls: int = 0
    ok: int = 0
    rejected: int = 0
    errors: int = 0
    last_ok_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    recent_latency_ms: list[int] = field(default_factory=list)

    def note_latency(self, ms: int) -> None:
        self.recent_latency_ms = (self.recent_latency_ms + [ms])[-50:]


state = ServiceState()


def model_label(model: str | None = None) -> str:
    m = model or get_settings().ai_model
    return MODEL_LABELS.get(m, m)


def is_configured() -> bool:
    s = get_settings()
    return bool(s.ai_enabled and s.anthropic_api_key)


def get_client() -> anthropic.Anthropic | None:
    """Kalit bo'lsa, bitta umumiy klient qaytaradi; kalit almashsa, klient qayta yaratiladi."""
    global _client, _client_key
    s = get_settings()
    if not is_configured():
        return None
    with _lock:
        if _client is None or _client_key != s.anthropic_api_key:
            _client = anthropic.Anthropic(
                api_key=s.anthropic_api_key,
                timeout=s.ai_timeout_seconds,
                max_retries=1,
            )
            _client_key = s.anthropic_api_key
        return _client


def describe_error(exc: Exception) -> str:
    """SDK xatosini foydalanuvchiga tushunarli o'zbekcha xabarga aylantiradi (kalit ko'rsatilmaydi)."""
    if isinstance(exc, anthropic.AuthenticationError):
        return "API kaliti noto‘g‘ri yoki bekor qilingan"
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "API kalitida bu modelga ruxsat yo‘q"
    if isinstance(exc, anthropic.NotFoundError):
        return f"Model topilmadi: {get_settings().ai_model}"
    if isinstance(exc, anthropic.RateLimitError):
        return "So‘rovlar limiti oshdi, birozdan so‘ng qayta urinib ko‘ring"
    if isinstance(exc, anthropic.BadRequestError):
        return f"So‘rov rad etildi: {exc.message[:200]}"
    if isinstance(exc, anthropic.APITimeoutError):
        return "Model javob berish vaqti tugadi"
    if isinstance(exc, anthropic.APIConnectionError):
        return "Anthropic API bilan aloqa yo‘q (internet yoki proksi)"
    if isinstance(exc, anthropic.APIStatusError):
        return f"Anthropic API xatosi ({exc.status_code})"
    return f"Kutilmagan xato: {type(exc).__name__}"


def record_error(message: str) -> None:
    state.errors += 1
    state.last_error = message
    state.last_error_at = datetime.now(timezone.utc)


def check_connection() -> dict:
    """Kalit va modelga kirishni tekshiradi: Models API chaqiruvi token sarflamaydi."""
    s = get_settings()
    client = get_client()
    if client is None:
        return {"ok": False, "message": "API kaliti o‘rnatilmagan" if s.ai_enabled else "SI xizmati o‘chirilgan"}
    started = datetime.now(timezone.utc)
    try:
        info = client.models.retrieve(s.ai_model)
    except Exception as exc:  # noqa: BLE001 - xato turi xabarga aylantiriladi
        message = describe_error(exc)
        record_error(message)
        return {"ok": False, "message": message}
    ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return {"ok": True, "message": "Ulanish muvaffaqiyatli", "model": info.id,
            "display_name": getattr(info, "display_name", None), "latency_ms": ms}
