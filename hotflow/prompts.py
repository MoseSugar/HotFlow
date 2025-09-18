"""Prompt templates used for creative generation."""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .models import Item

PLATFORM_LABELS = {
    "xiaohongshu": "小红书图文笔记",
    "weibo": "微博短文",
    "zhihu": "知乎回答",
}

DEFAULT_PLATFORMS = ["xiaohongshu", "weibo", "zhihu"]

PROMPT_TEMPLATE = """你是一名擅长电商种草文案的写手, 擅长用真实体验打动消费者。\n\n请根据以下商品信息, 为每个平台生成 {variants} 条不同风格的推广文案。\n\n输出要求:\n1. 每个平台输出一个数组, 其中包含 {variants} 条文案字符串。\n2. 结果必须是 JSON 格式, 字段名使用平台英文标识: {platform_keys}。\n3. 文案需要自然真实, 强调省钱、使用体验和复购感受。\n4. 合理添加 emoji, 但避免过度使用。\n\n商品信息:\n- 品类: {category}\n- 名称: {title}\n- 券后价: {coupon_price}\n- 原价: {price}\n- 月销量: {monthly_sales}\n- 店铺: {shop_title}\n- 核心卖点: {features}\n- 优惠信息: {coupon_info}\n\n如果信息缺失, 请合理发挥但不要捏造夸张数据。"""


def _format_price(value: Decimal | None) -> str:
    if value is None:
        return "未知"
    return f"¥{value:.2f}"


def _format_sales(value: int | None) -> str:
    if value is None:
        return "未知"
    if value >= 10000:
        return f"{value / 10000:.1f}万+"
    return str(value)


def derive_features(item: Item) -> str:
    raw = item.raw or {}
    features: list[str] = []
    highlight = raw.get("item_description") or raw.get("item_short_title")
    if highlight:
        features.append(highlight)
    if raw.get("provcity"):
        features.append(f"发货地 {raw['provcity']}")
    if raw.get("level_one_category_name"):
        features.append(f"类目：{raw['level_one_category_name']}")
    if raw.get("small_images"):
        images = raw["small_images"].get("string") if isinstance(raw["small_images"], dict) else raw["small_images"]
        if isinstance(images, list) and images:
            features.append(f"精选图{len(images)}张")
    if item.tags:
        features.append("#" + " #".join(item.tags))
    if not features:
        features.append("口碑好, 性价比高")
    return "；".join(features)


def build_prompt(item: Item, platforms: Sequence[str], variants: int) -> str:
    keys = ", ".join(platforms)
    features = derive_features(item)
    coupon_info = item.coupon_info or "下单立减, 先到先得"
    prompt = PROMPT_TEMPLATE.format(
        variants=variants,
        platform_keys=keys,
        category=item.category,
        title=item.title,
        coupon_price=_format_price(item.coupon_price or item.price),
        price=_format_price(item.price),
        monthly_sales=_format_sales(item.monthly_sales),
        shop_title=item.shop_title or "优质店铺",
        features=features,
        coupon_info=coupon_info,
    )
    return prompt


__all__ = ["build_prompt", "derive_features", "DEFAULT_PLATFORMS", "PLATFORM_LABELS"]
