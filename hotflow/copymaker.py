"""Utilities to generate creatives using OpenAI models."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import json
import logging

from openai import OpenAI

from .models import Creative, Item
from .prompts import DEFAULT_PLATFORMS, build_prompt

logger = logging.getLogger(__name__)


class CopyWriter:
    """Generate creatives for Taobao items using LLMs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        provider: str = "openai",
        base_url: Optional[str] = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = client or OpenAI(**client_kwargs)
        self.provider = provider
        self.base_url = base_url

    def _parse_response(
        self,
        payload: str,
        platforms: Sequence[str],
        variants: int,
    ) -> Dict[str, List[str]]:
        text = payload.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if "{" in text:
                text = text[text.find("{") : text.rfind("}") + 1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse response as JSON. Falling back to raw text.")
            return {platforms[0]: [payload.strip()]}

        results: Dict[str, List[str]] = {}
        for platform in platforms:
            value = data.get(platform)
            texts: List[str] = []
            if isinstance(value, list):
                texts = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str):
                texts = [value.strip()]
            else:
                logger.debug("Platform %s missing or invalid in response", platform)
            if len(texts) > variants:
                texts = texts[:variants]
            results[platform] = texts
        return results

    def generate(
        self,
        item: Item,
        *,
        platforms: Sequence[str] = DEFAULT_PLATFORMS,
        variants: int = 3,
        extra_system_prompt: Optional[str] = None,
    ) -> List[Creative]:
        prompt = build_prompt(item, platforms, variants)
        messages = []
        if extra_system_prompt:
            messages.append({"role": "system", "content": extra_system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            "Calling %s model %s for item %s",
            self.provider,
            self.model,
            item.item_id,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        message = response.choices[0].message
        content = message.content or ""
        parsed = self._parse_response(content, platforms, variants)

        creatives: List[Creative] = []
        for platform in platforms:
            texts = parsed.get(platform) or []
            if not texts:
                continue
            for idx, text in enumerate(texts, start=1):
                creatives.append(
                    Creative(
                        item_id=item.item_id,
                        platform=platform,
                        variant=idx,
                        content=text,
                        prompt=prompt,
                        model=self.model,
                        temperature=self.temperature,
                        provider=self.provider,
                        metadata={
                            "platforms": list(platforms),
                            "variants_requested": variants,
                        },
                    )
                )
        if not creatives:
            logger.warning("No creatives generated for item %s", item.item_id)
        return creatives


__all__ = ["CopyWriter"]
