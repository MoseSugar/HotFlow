"""Command line interface for HotFlow."""
from __future__ import annotations

from typing import List, Optional, Sequence
import logging

import typer

from .config import Settings, load_settings
from .copymaker import CopyWriter
from .db import create_tables, fetch_items, get_engine, list_creatives
from .pipeline import fetch_and_store, generate_and_store_creatives
from .prompts import DEFAULT_PLATFORMS
from .taobao import TaobaoClient

app = typer.Typer(help="HotFlow data ingestion and creative generation toolkit")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging"),
    database_url: Optional[str] = typer.Option(None, help="Override the database URL"),
    keyword: List[str] = typer.Option(
        None, "--keyword", help="Keyword(s) to fetch. Defaults to configuration keywords.", show_default=False
    ),
    openai_model: Optional[str] = typer.Option(None, help="Override the LLM model for copy generation"),
    openai_temperature: Optional[float] = typer.Option(None, help="Override the LLM temperature"),
    copy_provider: Optional[str] = typer.Option(
        None,
        "--copy-provider",
        help="LLM provider for copy generation (e.g. openai, deepseek)",
    ),
    llm_base_url: Optional[str] = typer.Option(
        None,
        "--llm-base-url",
        help="Override the base URL for the copy provider",
    ),
) -> None:
    """Load configuration and prepare context."""

    _setup_logging(verbose)
    overrides = {}
    if database_url:
        overrides["database_url"] = database_url
    if keyword:
        overrides["keywords"] = keyword
    if openai_model:
        overrides["openai_model"] = openai_model
    if openai_temperature is not None:
        overrides["openai_temperature"] = openai_temperature
    if copy_provider:
        overrides["copy_provider"] = copy_provider
    if llm_base_url:
        overrides["openai_base_url"] = llm_base_url

    settings = load_settings(**overrides)
    ctx.obj = {"settings": settings}


def _get_settings(ctx: typer.Context) -> Settings:
    if not ctx.obj or "settings" not in ctx.obj:
        raise typer.BadParameter("Configuration has not been loaded. Ensure the callback ran correctly.")
    return ctx.obj["settings"]


@app.command("init-db")
def init_db(ctx: typer.Context) -> None:
    """Initialize the database schema."""

    settings = _get_settings(ctx)
    engine = get_engine(settings.database_url)
    create_tables(engine)
    typer.echo("Database schema initialized.")


@app.command("fetch")
def fetch_command(
    ctx: typer.Context,
    pages: int = typer.Option(1, help="Number of pages to fetch for each keyword"),
    page_size: int = typer.Option(50, help="Number of items per page"),
    delay: float = typer.Option(1.0, help="Delay between page requests in seconds"),
    include_no_coupon: bool = typer.Option(
        False, "--include-no-coupon", help="Include items without coupons in the search"
    ),
    sort: str = typer.Option("total_sales_des", help="Sort order used by the API"),
) -> None:
    """Fetch items from Taobao Alliance and store them in the database."""

    settings = _get_settings(ctx)
    engine = get_engine(settings.database_url)
    create_tables(engine)

    client = TaobaoClient(
        app_key=settings.taobao.app_key,
        app_secret=settings.taobao.app_secret,
        adzone_id=settings.taobao.adzone_id,
        endpoint=settings.taobao.endpoint,
    )

    keywords = settings.keywords
    total = fetch_and_store(
        client=client,
        engine=engine,
        keywords=keywords,
        pages=pages,
        page_size=page_size,
        delay=delay,
        has_coupon=not include_no_coupon,
        sort=sort,
    )
    typer.echo(f"Stored {total} items for {len(keywords)} keyword(s).")


@app.command("generate-copy")
def generate_copy_command(
    ctx: typer.Context,
    item_id: List[int] = typer.Option(None, "--item-id", help="Generate creatives for specific item IDs"),
    limit: Optional[int] = typer.Option(None, help="Limit the number of items to process"),
    platform: List[str] = typer.Option(None, "--platform", help="Target platforms for copy generation"),
    variants: int = typer.Option(3, help="Number of variants per platform"),
) -> None:
    """Generate creatives for stored items using OpenAI."""

    settings = _get_settings(ctx)
    llm_settings = settings.require_llm()
    engine = get_engine(settings.database_url)
    create_tables(engine)

    platforms = platform or DEFAULT_PLATFORMS
    copywriter = CopyWriter(
        api_key=llm_settings.api_key,
        model=llm_settings.model,
        temperature=llm_settings.temperature,
        provider=llm_settings.provider,
        base_url=llm_settings.base_url,
    )

    creatives = generate_and_store_creatives(
        copywriter=copywriter,
        engine=engine,
        platforms=platforms,
        variants=variants,
        limit=limit,
        item_ids=item_id if item_id else None,
    )
    typer.echo(f"Generated {len(creatives)} creatives across {len(platforms)} platform(s).")


@app.command("list-items")
def list_items_command(
    ctx: typer.Context,
    limit: int = typer.Option(10, help="Number of items to display"),
    category: List[str] = typer.Option(None, "--category", help="Filter by category"),
) -> None:
    """List stored items."""

    settings = _get_settings(ctx)
    engine = get_engine(settings.database_url)
    items = fetch_items(engine, limit=limit, categories=category if category else None)
    if not items:
        typer.echo("No items found.")
        return
    for item in items:
        typer.echo(
            f"[{item.category}] {item.item_id} | {item.title} | 券后价: {item.coupon_price} | 月销量: {item.monthly_sales}"
        )


@app.command("list-creatives")
def list_creatives_command(
    ctx: typer.Context,
    item_id: Optional[int] = typer.Option(None, help="Filter creatives by item id"),
    limit: Optional[int] = typer.Option(10, help="Limit the number of creatives displayed"),
) -> None:
    """List generated creatives."""

    settings = _get_settings(ctx)
    engine = get_engine(settings.database_url)
    creatives = list_creatives(engine, item_id=item_id)
    if limit is not None:
        creatives = creatives[:limit]
    if not creatives:
        typer.echo("No creatives found.")
        return
    for creative in creatives:
        typer.echo(
            f"Item {creative.item_id} | {creative.platform} #{creative.variant}: {creative.content[:80]}..."
        )


if __name__ == "__main__":  # pragma: no cover
    app()
