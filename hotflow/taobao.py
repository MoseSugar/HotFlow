"""Taobao Alliance API client and helpers."""
from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import hashlib
import logging
import time

try:  # pragma: no cover - optional dependency fallback
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from .models import Item

logger = logging.getLogger(__name__)


class TaobaoAPIError(RuntimeError):
    """Raised when the Taobao API returns an error response."""


@dataclass
class SearchResult:
    items: List[Item]
    total_results: Optional[int]
    page_no: int
    page_size: int


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:  # pragma: no cover - defensive
        logger.debug("Failed to convert %s to Decimal", value)
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:  # pragma: no cover - defensive
        logger.debug("Failed to convert %s to int", value)
        return None


class TaobaoClient:
    """A thin wrapper around the Taobao Alliance material optional API."""

    def __init__(
        self,
        *,
        app_key: str,
        app_secret: str,
        adzone_id: str,
        endpoint: str = "https://eco.taobao.com/router/rest",
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        if requests is None:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "The 'requests' package is required to use TaobaoClient. Install requests to enable network calls."
            )
        self.app_key = app_key
        self.app_secret = app_secret
        self.adzone_id = adzone_id
        self.endpoint = endpoint
        self.session = session or requests.Session()
        self.timeout = timeout

    @staticmethod
    def sign(params: Dict[str, Any], secret: str) -> str:
        """Generate a Taobao API signature."""

        ordered = sorted((k, v) for k, v in params.items() if v is not None)
        base = secret + "".join(f"{key}{value}" for key, value in ordered) + secret
        return hashlib.md5(base.encode("utf-8")).hexdigest().upper()

    def _build_params(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "method": "taobao.tbk.dg.material.optional",
            "app_key": self.app_key,
            "sign_method": "md5",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "adzone_id": self.adzone_id,
        }
        params.update({key: value for key, value in extra.items() if value is not None})
        params["sign"] = self.sign(params, self.app_secret)
        return params

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.get(self.endpoint, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if "error_response" in payload:
            error = payload["error_response"]
            code = error.get("code")
            message = error.get("msg") or error.get("sub_msg")
            raise TaobaoAPIError(f"Taobao API error {code}: {message}")
        return payload.get("tbk_dg_material_optional_response", {})

    @staticmethod
    def _parse_item(raw: Dict[str, Any], keyword: str) -> Item:
        price = _safe_decimal(raw.get("zk_final_price"))
        original_price = _safe_decimal(raw.get("reserve_price")) or price
        coupon_amount = _safe_decimal(raw.get("coupon_amount"))
        coupon_price = price
        if price is not None and coupon_amount is not None:
            coupon_price = price - coupon_amount
            if coupon_price < Decimal("0"):
                coupon_price = Decimal("0")

        commission_rate = _safe_decimal(raw.get("commission_rate"))
        if commission_rate is not None:
            commission_rate = commission_rate / Decimal("100")

        monthly_sales = _safe_int(raw.get("volume") or raw.get("month_sales"))
        shop_score = _safe_decimal(raw.get("shop_dsr"))

        coupon_info_parts: List[str] = []
        if raw.get("coupon_start_fee") and raw.get("coupon_amount"):
            coupon_info_parts.append(
                f"满{raw['coupon_start_fee']}减{raw['coupon_amount']}"
            )
        if raw.get("coupon_end_time"):
            coupon_info_parts.append(f"券有效期至{raw['coupon_end_time']}")

        coupon_info = "；".join(coupon_info_parts) or raw.get("coupon_info")

        return Item(
            item_id=int(raw["item_id"]),
            category=keyword,
            title=raw.get("short_title") or raw.get("title") or "",
            image_url=raw.get("pict_url"),
            price=original_price,
            coupon_price=coupon_price,
            commission_rate=commission_rate,
            monthly_sales=monthly_sales,
            shop_score=shop_score,
            shop_title=raw.get("shop_title") or raw.get("shop_dsr"),
            item_url=raw.get("url") or raw.get("item_url"),
            coupon_url=raw.get("coupon_share_url") or raw.get("coupon_click_url"),
            coupon_info=coupon_info,
            tags=[keyword],
            raw=raw,
        )

    def search(
        self,
        keyword: str,
        *,
        page_no: int = 1,
        page_size: int = 50,
        has_coupon: bool = True,
        sort: str = "total_sales_des",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> SearchResult:
        """Search items by keyword."""

        params = {
            "q": keyword,
            "page_no": page_no,
            "page_size": page_size,
            "sort": sort,
        }
        if has_coupon:
            params["has_coupon"] = "true"
        if extra_params:
            params.update(extra_params)

        signed_params = self._build_params(params)
        payload = self._request(signed_params)
        result_list = payload.get("result_list", {}).get("map_data", [])
        items = [self._parse_item(entry, keyword) for entry in result_list if entry]
        total_results = payload.get("total_results")
        return SearchResult(items=items, total_results=total_results, page_no=page_no, page_size=page_size)

    def fetch_many(
        self,
        keyword: str,
        *,
        pages: int = 1,
        page_size: int = 50,
        delay: float = 1.0,
        **options: Any,
    ) -> List[Item]:
        """Fetch multiple pages of results for a keyword."""

        collected: List[Item] = []
        for page in range(1, pages + 1):
            result = self.search(keyword, page_no=page, page_size=page_size, **options)
            if not result.items:
                break
            collected.extend(result.items)
            if len(result.items) < page_size:
                break
            if delay:
                time.sleep(delay)
        return collected


__all__ = ["TaobaoClient", "TaobaoAPIError", "SearchResult"]
