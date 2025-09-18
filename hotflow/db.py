"""Database utilities for HotFlow."""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence
import json

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    and_,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine

from .models import Creative, Item

metadata = MetaData()


taoke_items = Table(
    "taoke_items",
    metadata,
    Column("item_id", BigInteger, primary_key=True),
    Column("category", String(64), nullable=False),
    Column("title", Text, nullable=False),
    Column("image_url", Text),
    Column("coupon_price", Numeric(10, 2)),
    Column("price", Numeric(10, 2)),
    Column("commission_rate", Numeric(10, 4)),
    Column("monthly_sales", Integer),
    Column("shop_score", Numeric(10, 4)),
    Column("shop_title", String(255)),
    Column("item_url", Text),
    Column("coupon_url", Text),
    Column("coupon_info", Text),
    Column("tags", Text),
    Column("raw", Text),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)


creatives = Table(
    "creatives",
    metadata,
    Column("creative_id", String(64), primary_key=True),
    Column("item_id", BigInteger, nullable=False),
    Column("platform", String(32), nullable=False),
    Column("variant", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("prompt", Text, nullable=False),
    Column("model", String(64), nullable=False),
    Column("temperature", Float, nullable=False),
    Column("provider", String(32), nullable=False),
    Column("metadata", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url)


def create_tables(engine: Engine) -> None:
    metadata.create_all(engine)


def store_items(engine: Engine, items: Iterable[Item]) -> int:
    items = list(items)
    if not items:
        return 0

    with engine.begin() as conn:
        ids = [item.item_id for item in items]
        conn.execute(taoke_items.delete().where(taoke_items.c.item_id.in_(ids)))
        rows = []
        for item in items:
            record = item.to_record()
            record["raw"] = json.dumps(record["raw"], ensure_ascii=False)
            rows.append(record)
        conn.execute(taoke_items.insert(), rows)
    return len(items)


def fetch_items(
    engine: Engine,
    *,
    limit: Optional[int] = None,
    categories: Optional[Sequence[str]] = None,
    item_ids: Optional[Sequence[int]] = None,
) -> List[Item]:
    stmt = select(taoke_items).order_by(taoke_items.c.updated_at.desc())
    conditions = []
    if categories:
        conditions.append(taoke_items.c.category.in_(categories))
    if item_ids:
        conditions.append(taoke_items.c.item_id.in_(item_ids))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    if limit:
        stmt = stmt.limit(limit)

    with engine.begin() as conn:
        rows = conn.execute(stmt).fetchall()

    items: List[Item] = []
    for row in rows:
        raw_data = json.loads(row.raw) if row.raw else {}
        tags = row.tags.split(",") if row.tags else []
        items.append(
            Item(
                item_id=row.item_id,
                category=row.category,
                title=row.title,
                image_url=row.image_url,
                price=row.price,
                coupon_price=row.coupon_price,
                commission_rate=row.commission_rate,
                monthly_sales=row.monthly_sales,
                shop_score=row.shop_score,
                shop_title=row.shop_title,
                item_url=row.item_url,
                coupon_url=row.coupon_url,
                coupon_info=row.coupon_info,
                tags=tags,
                raw=raw_data,
            )
        )
    return items


def store_creatives(engine: Engine, creatives_to_store: Iterable[Creative]) -> int:
    creatives_list = list(creatives_to_store)
    if not creatives_list:
        return 0

    with engine.begin() as conn:
        rows = []
        for creative in creatives_list:
            record = creative.to_record()
            record["metadata"] = json.dumps(record.get("metadata") or {}, ensure_ascii=False)
            rows.append(record)
        conn.execute(creatives.insert(), rows)
    return len(creatives_list)


def list_creatives(engine: Engine, *, item_id: Optional[int] = None) -> List[Creative]:
    stmt = select(creatives).order_by(creatives.c.created_at.desc())
    if item_id is not None:
        stmt = stmt.where(creatives.c.item_id == item_id)

    with engine.begin() as conn:
        rows = conn.execute(stmt).fetchall()

    results: List[Creative] = []
    for row in rows:
        metadata_payload = json.loads(row.metadata) if row.metadata else {}
        results.append(
            Creative(
                creative_id=row.creative_id,
                item_id=row.item_id,
                platform=row.platform,
                variant=row.variant,
                content=row.content,
                prompt=row.prompt,
                model=row.model,
                temperature=row.temperature,
                provider=row.provider,
                metadata=metadata_payload,
            )
        )
    return results


__all__ = [
    "get_engine",
    "create_tables",
    "store_items",
    "fetch_items",
    "store_creatives",
    "list_creatives",
    "metadata",
    "taoke_items",
    "creatives",
]
