"""Tests for configuration loading and provider selection."""

from __future__ import annotations

import pytest

from hotflow.config import LLMSettings, load_settings


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch):
    """Clear LLM-related environment variables before each test."""

    keys = [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_TEMPERATURE",
        "OPENAI_BASE_URL",
        "HOTFLOW_COPY_PROVIDER",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_TEMPERATURE",
        "DEEPSEEK_BASE_URL",
        "HOTFLOW_KEYWORDS",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    # Required Taobao/database keys for successful configuration load
    monkeypatch.setenv("TB_APP_KEY", "key")
    monkeypatch.setenv("TB_APP_SECRET", "secret")
    monkeypatch.setenv("TB_ADZONE_ID", "zone")
    monkeypatch.setenv("HOTFLOW_DATABASE_URL", "sqlite://")
    yield
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_load_settings_defaults_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = load_settings()
    llm = settings.require_llm()
    assert isinstance(llm, LLMSettings)
    assert llm.provider == "openai"
    assert llm.model == "gpt-4o-mini"
    assert llm.base_url is None


def test_load_settings_supports_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTFLOW_COPY_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    settings = load_settings()
    llm = settings.require_llm()
    assert llm.provider == "deepseek"
    assert llm.api_key == "ds-key"
    assert llm.model == "deepseek-chat"
    assert llm.base_url == "https://api.deepseek.com"

