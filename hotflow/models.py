"""Domain models used across the HotFlow package."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class Item:
    """A simplified view of a Taobao Alliance item."""

    item_id: int
    category: str
    title: str
    image_url: Optional[str] = None
    price: Optional[Decimal] = None
    coupon_price: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None
    monthly_sales: Optional[int] = None
    shop_score: Optional[Decimal] = None
    shop_title: Optional[str] = None
    item_url: Optional[str] = None
    coupon_url: Optional[str] = None
    coupon_info: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> Dict[str, Any]:
        """Convert the item into a database friendly dictionary."""

        return {
            "item_id": int(self.item_id),
            "category": self.category,
            "title": self.title,
            "image_url": self.image_url,
            "coupon_price": float(self.coupon_price) if self.coupon_price is not None else None,
            "price": float(self.price) if self.price is not None else None,
            "commission_rate": float(self.commission_rate) if self.commission_rate is not None else None,
            "monthly_sales": self.monthly_sales,
            "shop_score": float(self.shop_score) if self.shop_score is not None else None,
            "shop_title": self.shop_title,
            "item_url": self.item_url,
            "coupon_url": self.coupon_url,
            "coupon_info": self.coupon_info,
            "tags": ",".join(self.tags),
            "raw": self.raw,
            "updated_at": datetime.utcnow(),
        }


@dataclass
class Creative:
    """Represents an AI generated creative."""

    item_id: int
    platform: str
    variant: int
    content: str
    prompt: str
    model: str
    temperature: float
    provider: str = "openai"
    creative_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> Dict[str, Any]:
        return {
            "creative_id": self.creative_id,
            "item_id": int(self.item_id),
            "platform": self.platform,
            "variant": self.variant,
            "content": self.content,
            "prompt": self.prompt,
            "model": self.model,
            "temperature": self.temperature,
            "provider": self.provider,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


__all__ = ["Item", "Creative"]
