from decimal import Decimal

from hotflow.models import Item
from hotflow.prompts import build_prompt, derive_features


def make_item() -> Item:
    return Item(
        item_id=1,
        category="猫粮",
        title="优质猫粮",
        price=Decimal("79.9"),
        coupon_price=Decimal("69.9"),
        commission_rate=Decimal("0.15"),
        monthly_sales=1234,
        shop_score=Decimal("4.9"),
        shop_title="旗舰店",
        item_url="https://example.com",
        coupon_url="https://example.com/coupon",
        coupon_info="满减优惠",
        raw={"provcity": "上海", "level_one_category_name": "宠物用品"},
    )


def test_build_prompt_contains_core_fields():
    item = make_item()
    prompt = build_prompt(item, ["xiaohongshu", "weibo"], 2)
    assert "优质猫粮" in prompt
    assert "满减优惠" in prompt
    assert "xiaohongshu" in prompt
    assert "¥69.90" in prompt


def test_derive_features_falls_back_to_default():
    item = Item(item_id=2, category="抽纸", title="抽纸", raw={})
    features = derive_features(item)
    assert "性价比" in features
