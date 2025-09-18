"""Configuration helpers for HotFlow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional
import os

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

DEFAULT_KEYWORDS = ["抽纸", "洗衣液", "猫粮", "狗粮", "猫砂"]


def _split_keywords(raw: Optional[str]) -> List[str]:
    if not raw:
        return DEFAULT_KEYWORDS.copy()
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


@dataclass
class TaobaoSettings:
    """Holds credentials and API configuration for Taobao Alliance."""

    app_key: str
    app_secret: str
    adzone_id: str
    endpoint: str = "https://eco.taobao.com/router/rest"


@dataclass
class OpenAISettings:
    """OpenAI client configuration."""

    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7


@dataclass
class Settings:
    """Application wide settings."""

    taobao: TaobaoSettings
    database_url: str
    keywords: List[str] = field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    openai: Optional[OpenAISettings] = None

    def with_overrides(
        self,
        *,
        keywords: Optional[Iterable[str]] = None,
        database_url: Optional[str] = None,
        openai_model: Optional[str] = None,
        openai_temperature: Optional[float] = None,
    ) -> "Settings":
        """Return a copy of the settings with runtime overrides applied."""

        openai_settings = None
        if self.openai:
            openai_settings = OpenAISettings(
                api_key=self.openai.api_key,
                model=self.openai.model,
                temperature=self.openai.temperature,
            )

        updated = Settings(
            taobao=self.taobao,
            database_url=database_url or self.database_url,
            keywords=list(keywords) if keywords else self.keywords.copy(),
            openai=openai_settings,
        )
        if updated.openai and openai_model:
            updated.openai.model = openai_model
        if updated.openai and openai_temperature is not None:
            updated.openai.temperature = openai_temperature
        return updated

    def require_openai(self) -> OpenAISettings:
        if not self.openai:
            raise RuntimeError(
                "OpenAI credentials are required for this action. Set OPENAI_API_KEY in the environment."
            )
        return self.openai


class _SettingsModel(BaseModel):
    tb_app_key: str
    tb_app_secret: str
    tb_adzone_id: str
    tb_endpoint: Optional[str] = None
    hotflow_database_url: str
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_temperature: Optional[float] = None
    hotflow_keywords: Optional[str] = None


def load_settings(**overrides) -> Settings:
    """Load configuration from environment variables and optional overrides."""

    load_dotenv()
    env = {key.lower(): value for key, value in os.environ.items()}

    try:
        model = _SettingsModel(**env)
    except ValidationError as exc:  # pragma: no cover - reformat error message
        errors = "; ".join(err.get("msg", "") for err in exc.errors())
        raise RuntimeError(f"Invalid configuration: {errors}") from exc

    taobao = TaobaoSettings(
        app_key=model.tb_app_key,
        app_secret=model.tb_app_secret,
        adzone_id=model.tb_adzone_id,
        endpoint=model.tb_endpoint or "https://eco.taobao.com/router/rest",
    )

    keywords = overrides.get("keywords")
    if keywords:
        keyword_list = list(keywords)
    else:
        override_keywords = overrides.get("hotflow_keywords")
        if override_keywords:
            keyword_list = list(override_keywords)
        else:
            keyword_list = _split_keywords(model.hotflow_keywords)

    openai_settings: Optional[OpenAISettings] = None
    api_key = overrides.get("openai_api_key") or model.openai_api_key
    if api_key:
        openai_settings = OpenAISettings(
            api_key=api_key,
            model=overrides.get("openai_model") or model.openai_model or "gpt-4o-mini",
            temperature=float(
                overrides.get("openai_temperature")
                or model.openai_temperature
                or 0.7
            ),
        )

    settings = Settings(
        taobao=taobao,
        database_url=overrides.get("database_url") or model.hotflow_database_url,
        keywords=keyword_list,
        openai=openai_settings,
    )
    return settings


__all__ = [
    "Settings",
    "TaobaoSettings",
    "OpenAISettings",
    "load_settings",
]
