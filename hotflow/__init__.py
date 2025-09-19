"""HotFlow package with lightweight imports for optional dependencies."""

from __future__ import annotations

from .config import LLMSettings, Settings, load_settings

try:  # pragma: no cover - optional dependency wrappers
    from .taobao import TaobaoAPIError, TaobaoClient
except ModuleNotFoundError:  # pragma: no cover
    TaobaoClient = None  # type: ignore[assignment]
    TaobaoAPIError = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency wrappers
    from .copymaker import CopyWriter
except ModuleNotFoundError:  # pragma: no cover
    CopyWriter = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency wrappers
    from .pipeline import fetch_and_store
except ModuleNotFoundError:  # pragma: no cover
    fetch_and_store = None  # type: ignore[assignment]

__all__ = [
    "Settings",
    "LLMSettings",
    "load_settings",
    "TaobaoClient",
    "TaobaoAPIError",
    "CopyWriter",
    "fetch_and_store",
]
