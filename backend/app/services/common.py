"""Umumiy yordamchi funksiyalar: chegaralar, darajalar, maskalash, yorliqlar."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting

LEVEL_LABELS = {"high": "Yuqori", "medium": "O‘rta", "low": "Past"}
CONFIDENCE_LABELS = LEVEL_LABELS
EXPERT_STATUS_LABELS = {
    "pending": "Ko‘rib chiqilmagan",
    "confirmed": "Tasdiqlandi",
    "rejected": "Rad etildi",
    "need_info": "Qo‘shimcha ma’lumot kerak",
    "sent_review": "Tekshiruvga yuborildi",
}
ALERT_STATUS_LABELS = {
    "new": "Yangi",
    "in_review": "Ko‘rib chiqilmoqda",
    "confirmed": "Tasdiqlandi",
    "rejected": "Rad etildi",
    "closed": "Yopildi",
}
SIZE_LABELS = {"small": "Kichik", "medium": "O‘rta", "large": "Yirik"}


def get_thresholds(db: Session) -> tuple[float, float]:
    row = db.get(AppSetting, "risk_thresholds")
    if row and isinstance(row.value, dict):
        return float(row.value.get("low", 40)), float(row.value.get("high", 70))
    s = get_settings()
    return float(s.low_threshold), float(s.high_threshold)


def level_for(score: float, low: float, high: float) -> str:
    if score >= high:
        return "high"
    if score >= low:
        return "medium"
    return "low"


def mask_stir(stir: str, allowed: bool) -> str:
    if allowed:
        return stir
    tail = stir[-3:] if len(stir) >= 3 else stir
    return f"*** *** {tail}"
