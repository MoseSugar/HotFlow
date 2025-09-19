"""High level orchestration helpers for HotFlow."""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence
import logging

from sqlalchemy.engine import Engine

from .copymaker import CopyWriter
from .db import fetch_items, store_creatives, store_items
from .models import Creative, Item
from .taobao import TaobaoClient

logger = logging.getLogger(__name__)


def fetch_and_store(
    *,
    client: TaobaoClient,
    engine: Engine,
    keywords: Iterable[str],
    pages: int = 1,
    page_size: int = 50,
    delay: float = 1.0,
    **options,
) -> int:
    """Fetch items for each keyword and persist them."""

    total_items = 0
    for keyword in keywords:
        logger.info("Fetching keyword '%s'", keyword)
        items = client.fetch_many(keyword, pages=pages, page_size=page_size, delay=delay, **options)
        if not items:
            logger.warning("No items returned for keyword '%s'", keyword)
            continue
        stored = store_items(engine, items)
        logger.info("Stored %s items for keyword '%s'", stored, keyword)
        total_items += stored
    return total_items


def generate_and_store_creatives(
    *,
    copywriter: CopyWriter,
    engine: Engine,
    platforms: Sequence[str],
    variants: int = 3,
    limit: Optional[int] = None,
    categories: Optional[Sequence[str]] = None,
    item_ids: Optional[Sequence[int]] = None,
) -> List[Creative]:
    """Generate creatives for items and persist them."""

    items = fetch_items(engine, limit=limit, categories=categories, item_ids=item_ids)
    if not items:
        logger.warning("No items found for creative generation")
        return []

    all_creatives: List[Creative] = []
    for item in items:
        logger.info("Generating creatives for item %s", item.item_id)
        generated = copywriter.generate(item, platforms=platforms, variants=variants)
        all_creatives.extend(generated)
        store_creatives(engine, generated)
    return all_creatives


__all__ = ["fetch_and_store", "generate_and_store_creatives"]
