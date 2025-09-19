"""Configuration helpers for HotFlow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional
import os

try:  # pragma: no cover - optional dependency fallback
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

try:  # pragma: no cover - optional dependency fallback
    from pydantic import BaseModel, ValidationError
    HAS_PYDANTIC = True
except ModuleNotFoundError:  # pragma: no cover
    BaseModel = None  # type: ignore[assignment]
    HAS_PYDANTIC = False

    class ValidationError(Exception):  # type: ignore[override]
        """Fallback validation error used when pydantic is unavailable."""

        def __init__(self, message: str) -> None:
            super().__init__(message)

        def errors(self):  # pragma: no cover - compatibility helper
            return [{"msg": str(self)}]
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
class LLMSettings:
    """Configuration for the copy generation language model."""

    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    base_url: Optional[str] = None
    provider: str = "openai"


@dataclass
class Settings:
    """Application wide settings."""

    taobao: TaobaoSettings
    database_url: str
    keywords: List[str] = field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    llm: Optional[LLMSettings] = None

    def with_overrides(
        self,
        *,
        keywords: Optional[Iterable[str]] = None,
        database_url: Optional[str] = None,
        openai_model: Optional[str] = None,
        openai_temperature: Optional[float] = None,
        copy_provider: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> "Settings":
        """Return a copy of the settings with runtime overrides applied."""

        llm_settings = None
        if self.llm:
            llm_settings = LLMSettings(
                api_key=self.llm.api_key,
                model=self.llm.model,
                temperature=self.llm.temperature,
                base_url=self.llm.base_url,
                provider=self.llm.provider,
            )

        updated = Settings(
            taobao=self.taobao,
            database_url=database_url or self.database_url,
            keywords=list(keywords) if keywords else self.keywords.copy(),
            llm=llm_settings,
        )
        if updated.llm and copy_provider:
            updated.llm.provider = copy_provider.lower()
        if updated.llm and openai_model:
            updated.llm.model = openai_model
        if updated.llm and openai_temperature is not None:
            updated.llm.temperature = openai_temperature
        if updated.llm and openai_base_url:
            updated.llm.base_url = openai_base_url
        return updated

    def require_llm(self) -> LLMSettings:
        if not self.llm:
            raise RuntimeError(
                "Copy generation credentials are required. Configure OPENAI_API_KEY or DEEPSEEK_API_KEY in the environment."
            )
        return self.llm

    # Backwards compatibility for previous callers.
    def require_openai(self) -> LLMSettings:  # pragma: no cover - thin wrapper
        return self.require_llm()


if HAS_PYDANTIC:

    class _SettingsModel(BaseModel):
        tb_app_key: str
        tb_app_secret: str
        tb_adzone_id: str
        tb_endpoint: Optional[str] = None
        hotflow_database_url: str
        openai_api_key: Optional[str] = None
        openai_model: Optional[str] = None
        openai_temperature: Optional[float] = None
        openai_base_url: Optional[str] = None
        hotflow_copy_provider: Optional[str] = None
        deepseek_api_key: Optional[str] = None
        deepseek_model: Optional[str] = None
        deepseek_temperature: Optional[float] = None
        deepseek_base_url: Optional[str] = None
        hotflow_keywords: Optional[str] = None

else:

    class _SettingsModel:  # pragma: no cover - fallback when pydantic is absent
        def __init__(self, **env: str) -> None:
            def _require(name: str) -> str:
                value = env.get(name)
                if value is None:
                    raise ValidationError(f"Missing required configuration: {name}")
                return value

            def _optional_float(name: str) -> Optional[float]:
                raw = env.get(name)
                if raw in (None, ""):
                    return None
                try:
                    return float(raw)
                except ValueError as exc:  # pragma: no cover - validation helper
                    raise ValidationError(f"Invalid float for {name}: {raw}") from exc

            self.tb_app_key = _require("tb_app_key")
            self.tb_app_secret = _require("tb_app_secret")
            self.tb_adzone_id = _require("tb_adzone_id")
            self.tb_endpoint = env.get("tb_endpoint")
            self.hotflow_database_url = _require("hotflow_database_url")
            self.openai_api_key = env.get("openai_api_key")
            self.openai_model = env.get("openai_model")
            self.openai_temperature = _optional_float("openai_temperature")
            self.openai_base_url = env.get("openai_base_url")
            self.hotflow_copy_provider = env.get("hotflow_copy_provider")
            self.deepseek_api_key = env.get("deepseek_api_key")
            self.deepseek_model = env.get("deepseek_model")
            self.deepseek_temperature = _optional_float("deepseek_temperature")
            self.deepseek_base_url = env.get("deepseek_base_url")
            self.hotflow_keywords = env.get("hotflow_keywords")


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

    provider_override = overrides.get("copy_provider")
    provider = (provider_override or model.hotflow_copy_provider or "openai").lower()

    llm_settings: Optional[LLMSettings] = None
    if provider == "deepseek":
        api_key = overrides.get("deepseek_api_key") or model.deepseek_api_key
        if api_key:
            llm_settings = LLMSettings(
                api_key=api_key,
                model=(
                    overrides.get("openai_model")
                    or overrides.get("deepseek_model")
                    or model.openai_model
                    or model.deepseek_model
                    or "deepseek-chat"
                ),
                temperature=float(
                    overrides.get("openai_temperature")
                    or overrides.get("deepseek_temperature")
                    or model.openai_temperature
                    or model.deepseek_temperature
                    or 0.7
                ),
                base_url=(
                    overrides.get("openai_base_url")
                    or overrides.get("deepseek_base_url")
                    or model.openai_base_url
                    or model.deepseek_base_url
                    or "https://api.deepseek.com"
                ),
                provider="deepseek",
            )
    else:
        api_key = overrides.get("openai_api_key") or model.openai_api_key
        if api_key:
            llm_settings = LLMSettings(
                api_key=api_key,
                model=overrides.get("openai_model") or model.openai_model or "gpt-4o-mini",
                temperature=float(
                    overrides.get("openai_temperature")
                    or model.openai_temperature
                    or 0.7
                ),
                base_url=overrides.get("openai_base_url") or model.openai_base_url,
                provider="openai",
            )

    settings = Settings(
        taobao=taobao,
        database_url=overrides.get("database_url") or model.hotflow_database_url,
        keywords=keyword_list,
        llm=llm_settings,
    )
    return settings


__all__ = [
    "Settings",
    "TaobaoSettings",
    "LLMSettings",
    "load_settings",
]
