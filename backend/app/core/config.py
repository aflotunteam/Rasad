from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    app_name: str = "RASAD"
    api_prefix: str = "/api/v1"

    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'rasad.db').as_posix()}"

    # MVP uchun shartli chegaralar. Ishchi qiymatlar settings jadvalida saqlanadi
    # va Sozlamalar → Xavf chegaralari orqali o'zgartiriladi.
    low_threshold: int = 40
    high_threshold: int = 70

    cors_origins: str = "http://localhost:5173"

    # Sintetik ma'lumotlar davri: oxirgi to'liq oy.
    data_period_end: str = "2026-08-01"
    history_months: int = 24
    seed: int = 2026

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
